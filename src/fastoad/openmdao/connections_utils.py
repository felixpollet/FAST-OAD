"""
Utility functions for OpenMDAO classes/instances
"""
#  This file is part of FAST : A framework for rapid Overall Aircraft Design
#  Copyright (C) 2019  ONERA/ISAE
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

from logging import Logger
from typing import Tuple, List

import numpy as np
from openmdao.api import IndepVarComp
from openmdao.core.problem import Problem

from fastoad.exceptions import NoSetupError
from fastoad.io.serialize import SystemSubclass

# pylint: disable=protected-access #  needed for OpenMDAO introspection

def get_unconnected_inputs(problem: Problem,
                           logger: Logger = None) -> Tuple[List[str], List[str]]:
    """
    For provided OpenMDAO problem, looks for inputs that are connected to no output.
    Assumes problem.setup() has been run.

    Inputs that have numpy.nan as default value are considered as mandatory. Other ones are
    considered as optional.

    If a logger is provided, it will issue errors for the first category, and warnings for the
    second one.

    :param problem: OpenMDAO Problem or System instance to inspect
    :param logger: optional logger instance
    :return: tuple(list of missing mandatory inputs, list of missing optional inputs)
    """

    model = problem.model

    if not model._var_allprocs_prom2abs_list:
        raise NoSetupError('Analysis of unconnected inputs cannot be done without prior setup.')

    prom2abs: dict = model._var_allprocs_prom2abs_list['input']
    connexions: dict = model._conn_global_abs_in2out

    mandatory_unconnected = []
    optional_unconnected = []

    for abs_names in prom2abs.values():
        # At each iteration, get absolute names that match one promoted name, or one
        # absolute name that has not been promoted.
        unconnected = [a for a in abs_names if a not in connexions or len(connexions[a]) == 0]
        if unconnected:
            for abs_name in abs_names:
                value = model._var_abs2meta[abs_name]['value']
                if np.all(np.isnan(value)):
                    mandatory_unconnected.append(abs_name)
                else:
                    optional_unconnected.append(abs_name)

    if logger:
        if mandatory_unconnected:
            logger.error('Following inputs are required and not connected:')
            for abs_name in sorted(mandatory_unconnected):
                logger.error('    %s', abs_name)

        if optional_unconnected:
            logger.warning(
                'Following inputs are not connected so their default value will be used:')
            for abs_name in sorted(optional_unconnected):
                value = model._var_abs2meta[abs_name]['value']
                logger.warning('    %s : %s', abs_name, value)

    return mandatory_unconnected, optional_unconnected


def build_ivc_of_unconnected_inputs(problem: Problem,
                                    with_optional_inputs: bool = False) -> IndepVarComp:
    """
    This function returns an OpenMDAO IndepVarComp instance containing
    all the unconnected inputs of a Problem.

    If *optional_inputs* is False, only inputs that have numpy.nan as default value (hence
    considered as mandatory) will be in returned instance. Otherwise, all unconnected inputs will
    be in returned instance.

    :param problem: OpenMDAO Problem instance to inspect
    :param with_optional_inputs: If True, returned instance will contain all unconnected inputs.
                            Otherwise, it will contain only mandatory ones.
    :return: IndepVarComp instance
    """
    ivc = IndepVarComp()

    mandatory_unconnected, optional_unconnected = get_unconnected_inputs(problem)
    model = problem.model

    # processed_prom_names will store promoted names that have been already processed, so that
    # it won't be stored twice.
    # By processing mandatory variable first, a promoted variable that would be mandatory somewhere
    # and optional elsewhere will be retained as mandatory (and associated value will be NaN),
    # which is fine.
    # For promoted names that link to several optional variables and no mandatory ones, associated
    # value will be the first encountered one, and this is as good a choice as any other.
    processed_prom_names = []

    def _add_outputs(unconnected_names):
        """ Fills ivc with data associated to each provided var"""
        for abs_name in unconnected_names:
            prom_name = model._var_abs2prom['input'][abs_name]
            if prom_name not in processed_prom_names:
                processed_prom_names.append(prom_name)
                metadata = model._var_abs2meta[abs_name]
                ivc.add_output(prom_name,
                               val=metadata['value'],
                               units=metadata['units'],
                               desc=metadata['desc'])

    _add_outputs(mandatory_unconnected)
    if with_optional_inputs:
        _add_outputs(optional_unconnected)

    return ivc


def build_ivc_of_outputs(system: SystemSubclass) -> IndepVarComp:
    """
    This function returns an OpenMDAO IndepVarComp instance containing
    all the outputs of a SystemSubclass.

    :param system: OpenMDAO SystemSubclass instance to inspect
    :return: IndepVarComp instance
    """
    ivc = IndepVarComp()

    prom2abs: dict = system._var_allprocs_prom2abs_list['output']

    for _, (prom_name, abs_names) in enumerate(prom2abs.items()):
        # Pick the first
        abs_name = abs_names[0]
        metadata = system._var_abs2meta[abs_name]
        ivc.add_output(prom_name,
                       val=metadata['value'],
                       units=metadata['units'],
                       desc=metadata['desc'])

    return ivc
