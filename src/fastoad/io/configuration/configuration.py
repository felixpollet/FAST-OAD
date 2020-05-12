"""
Module for building OpenMDAO problem from configuration file
"""

#  This file is part of FAST : A framework for rapid Overall Aircraft Design
#  Copyright (C) 2020  ONERA & ISAE-SUPAERO
#  FAST is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.

import logging
import os
import os.path as pth
from typing import Dict

import openmdao.api as om
import tomlkit
from fastoad.io import IVariableIOFormatter
from fastoad.module_management import OpenMDAOSystemRegistry
from fastoad.openmdao.problem import FASTOADProblem

from .exceptions import (
    FASTConfigurationBaseKeyBuildingError,
    FASTConfigurationBadOpenMDAOInstructionError,
    FASTConfigurationError,
)

# Logger for this module
_LOGGER = logging.getLogger(__name__)

KEY_FOLDERS = "module_folders"
KEY_INPUT_FILE = "input_file"
KEY_OUTPUT_FILE = "output_file"
KEY_COMPONENT_ID = "id"
TABLE_MODEL = "model"
KEY_DRIVER = "driver"
TABLE_OPTIMIZATION = "optimization"
TABLES_DESIGN_VAR = "design_var"
TABLES_CONSTRAINT = "constraint"
TABLES_OBJECTIVE = "objective"


class FASTOADProblemConfigurator:
    def __init__(self, conf_file_path=None, auto_scaling: bool = False):
        self._conf_file = None
        self._conf_dict = {}
        self._auto_scaling = False

        if conf_file_path:
            self.load(conf_file_path, auto_scaling)

    @property
    def input_file_path(self):
        path = self._conf_dict[KEY_INPUT_FILE]
        if not pth.isabs(path):
            path = pth.normpath(pth.join(pth.dirname(self._conf_file), path))
        return path

    @input_file_path.setter
    def input_file_path(self, file_path: str):
        self._conf_dict[KEY_INPUT_FILE] = file_path

    @property
    def output_file_path(self):
        path = self._conf_dict[KEY_OUTPUT_FILE]
        if not pth.isabs(path):
            path = pth.normpath(pth.join(pth.dirname(self._conf_file), path))
        return path

    @output_file_path.setter
    def output_file_path(self, file_path: str):
        self._conf_dict[KEY_OUTPUT_FILE] = file_path

    def load(self, conf_file, auto_scaling: bool = False):
        """
        Reads definition of the current problem in given file.

        :param conf_file: Path to the file to open or a file descriptor
        :param auto_scaling: if True, automatic scaling is performed for design
                             variables and constraints
        """

        self._conf_file = conf_file
        self._auto_scaling = auto_scaling

        conf_dirname = pth.dirname(pth.abspath(conf_file))  # for resolving relative paths
        with open(conf_file, "r") as file:
            d = file.read()
            self._conf_dict = tomlkit.loads(d)

        # FIXME: Could structure of configuration file be checked more thoroughly ?
        for key in [KEY_INPUT_FILE, KEY_OUTPUT_FILE]:
            if key not in self._conf_dict:
                raise FASTConfigurationError(missing_key=key)

        if not isinstance(self._conf_dict.get(TABLE_MODEL), dict):
            raise FASTConfigurationError(missing_section=TABLE_MODEL)

        # Looking for modules to register
        module_folder_paths = self._conf_dict.get(KEY_FOLDERS, [])
        for folder_path in module_folder_paths:
            folder_path = pth.join(conf_dirname, folder_path)
            if not pth.exists(folder_path):
                _LOGGER.warning("SKIPPED %s: it does not exist.")
            else:
                OpenMDAOSystemRegistry.explore_folder(folder_path)

    def save(self, filename: str = None):
        """
        Writes to the .toml config file the current configuration.
        If no filename is provided, the initially read file is used.

        :param filename: file where to save configuration
        """
        if not filename:
            filename = self._conf_file

        dirname = pth.abspath(pth.dirname(filename))
        if not pth.exists(dirname):
            os.makedirs(dirname)

        with open(filename, "w") as file:
            d = tomlkit.dumps(self._conf_dict)
            file.write(d)

    def write_needed_inputs(
        self, source_file_path: str = None, source_formatter: IVariableIOFormatter = None,
    ):
        """
        Writes the input file of the problem with unconnected inputs of the configured problem.

        Written value of each variable will be taken:
        1. from input_data if it contains the variable
        2. from defined default values in component definitions

        :param source_file_path: if provided, variable values will be read from it
        :param source_formatter: the class that defines format of input file. if not provided,
                                expected format will be the default one.
        """
        problem = self.get_problem(read_inputs=False)
        problem.write_needed_inputs(source_file_path, source_formatter)

    def get_problem(self, read_inputs: bool = False) -> FASTOADProblem:
        if not self._conf_dict:
            raise RuntimeError("read configuration file first")

        problem = FASTOADProblem(self._build_model())

        problem.input_file_path = self.input_file_path
        problem.output_file_path = self.output_file_path

        driver = self._conf_dict.get(KEY_DRIVER, "")
        if driver:
            problem.driver = _om_eval(driver)

        if self.get_optimization_definition():
            self._add_constraints(problem.model)
            self._add_objectives(problem.model)

        if read_inputs:
            problem.read_inputs()
            self._add_design_vars(problem.model)

        return problem

    def get_optimization_definition(self) -> Dict:
        """
        Reads the config file and returns information related to the optimization problem:
            - Design Variables
            - Constraints
            - Objectives

        :return: dict containing optimization settings for current problem
        """

        optimization_definition = {}
        conf_dict = self._conf_dict.get(TABLE_OPTIMIZATION)
        if conf_dict:
            for sec, elements in conf_dict.items():
                optimization_definition[sec] = {elem["name"]: elem for elem in elements}
        return optimization_definition

    def set_optimization_definition(self, optimization_definition: Dict):
        """
        Updates configuration with the list of design variables, constraints, objectives
        contained in the optimization_definition dictionary.
        Keys of the dictionary are: "design_var", "constraint", "objective".

        :param optimization_definition: dict containing the optimization problem definition
        """
        subpart = {}
        for key, value in optimization_definition.items():
            subpart[key] = [value for _, value in optimization_definition[key].items()]
        subpart = {"optimization": subpart}
        self._conf_dict.update(subpart)

    def _build_model(self) -> om.Group:
        """
        Builds (or rebuilds) the problem as defined in the configuration file.

        self.model is initialized as a new group and populated subsystems indicated in
        configuration file.
        """

        model = om.Group()
        model_definition = self._conf_dict.get(TABLE_MODEL)

        try:
            if KEY_COMPONENT_ID in model_definition:
                # The defined model is only one system
                system_id = model_definition[KEY_COMPONENT_ID]
                sub_component = OpenMDAOSystemRegistry.get_system(system_id)
                model.add_subsystem("system", sub_component, promotes=["*"])
            else:
                # The defined model is a group
                self._parse_problem_table(model, model_definition)

        except FASTConfigurationBaseKeyBuildingError as err:
            log_err = err.__class__(err, TABLE_MODEL)
            _LOGGER.error(log_err)
            raise log_err

        return model

    def _parse_problem_table(self, group: om.Group, table: dict):
        """
        Feeds provided *group*, using definition in provided TOML *table*.

        :param group:
        :param table:
        """
        assert isinstance(table, dict), "table should be a dictionary"

        for key, value in table.items():
            if isinstance(value, dict):  # value defines a sub-component
                if KEY_COMPONENT_ID in value:
                    # It is a non-group component, that should be registered with its ID
                    options = value.copy()
                    identifier = options.pop(KEY_COMPONENT_ID)
                    sub_component = OpenMDAOSystemRegistry.get_system(identifier, options=options)
                    group.add_subsystem(key, sub_component, promotes=["*"])
                else:
                    # It is a Group
                    sub_component = group.add_subsystem(key, om.Group(), promotes=["*"])
                    try:
                        self._parse_problem_table(sub_component, value)
                    except FASTConfigurationBadOpenMDAOInstructionError as err:
                        # There has been an error while parsing an attribute.
                        # Error is relayed with key added for context
                        raise FASTConfigurationBadOpenMDAOInstructionError(err, key)
            else:
                # value is an attribute of current component and will be literally interpreted
                try:
                    setattr(group, key, _om_eval(value))  # pylint:disable=eval-used
                except Exception as err:
                    raise FASTConfigurationBadOpenMDAOInstructionError(err, key, value)

    def _add_constraints(self, model):
        """  Adds constraints as instructed in configuration file """
        optimization_definition = self.get_optimization_definition()
        # Constraints
        constraint_tables = optimization_definition.get(TABLES_CONSTRAINT, {})
        for _, constraint_table in constraint_tables.items():
            if self._auto_scaling:
                if "lower" in constraint_table:
                    constraint_table["ref0"] = constraint_table["lower"]
                if "upper" in constraint_table:
                    constraint_table["ref"] = constraint_table["upper"]
            model.add_constraint(**constraint_table)

    def _add_objectives(self, model):
        """  Adds objectives as instructed in configuration file """
        optimization_definition = self.get_optimization_definition()
        objective_tables = optimization_definition.get(TABLES_OBJECTIVE, {})
        for _, objective_table in objective_tables.items():
            model.add_objective(**objective_table)

    def _add_design_vars(self, model):
        """ Adds design variables as instructed in configuration file """
        optimization_definition = self.get_optimization_definition()
        design_var_tables = optimization_definition.get(TABLES_DESIGN_VAR, {})
        for _, design_var_table in design_var_tables.items():
            if self._auto_scaling:
                if "lower" in design_var_table:
                    design_var_table["ref0"] = design_var_table["lower"]
                if "upper" in design_var_table:
                    design_var_table["ref"] = design_var_table["upper"]
            model.add_design_var(**design_var_table)


def _om_eval(string_to_eval: str):
    """
    Evaluates strings that assume `import openmdao.api as om` is done.

    eval() is used for that, as safely as possible.

    :param string_to_eval:
    :return: result of eval()
    """
    if "__" in string_to_eval:
        raise ValueError("No double underscore allowed in evaluated string for security reasons")
    return eval(string_to_eval, {"__builtins__": {}}, {"om": om})
