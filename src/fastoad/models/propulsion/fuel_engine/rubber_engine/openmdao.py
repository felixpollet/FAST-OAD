"""
OpenMDAO wrapping of RubberEngine
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

import numpy as np
from fastoad.models.propulsion import OMIEngine
from fastoad.models.propulsion.engine import DirectEngine, IEngine
from fastoad.openmdao.validity_checker import ValidityDomainChecker
from openmdao.core.component import Component

from .rubber_engine import RubberEngine


class DirectRubberEngine(DirectEngine):
    def setup(self, comp: Component):
        comp.add_input("data:propulsion:rubber_engine:bypass_ratio", np.nan)
        comp.add_input("data:propulsion:rubber_engine:overall_pressure_ratio", np.nan)
        comp.add_input("data:propulsion:rubber_engine:turbine_inlet_temperature", np.nan, units="K")
        comp.add_input("data:propulsion:MTO_thrust", np.nan, units="N")
        comp.add_input("data:propulsion:rubber_engine:maximum_mach", np.nan)
        comp.add_input("data:propulsion:rubber_engine:design_altitude", np.nan, units="m")
        comp.add_input(
            "data:propulsion:rubber_engine:delta_t4_climb",
            -50,
            desc="As it is a delta, unit is K or °C, but is not "
            "specified to avoid OpenMDAO making unwanted conversion",
        )
        comp.add_input(
            "data:propulsion:rubber_engine:delta_t4_cruise",
            -100,
            desc="As it is a delta, unit is K or °C, but is not "
            "specified to avoid OpenMDAO making unwanted conversion",
        )

    @staticmethod
    def get_engine(inputs) -> IEngine:
        """

        :param inputs: input parameters that define the engine
        :return: an :class:`RubberEngine` instance
        """
        engine_params = {
            "bypass_ratio": inputs["data:propulsion:rubber_engine:bypass_ratio"],
            "overall_pressure_ratio": inputs[
                "data:propulsion:rubber_engine:overall_pressure_ratio"
            ],
            "turbine_inlet_temperature": inputs[
                "data:propulsion:rubber_engine:turbine_inlet_temperature"
            ],
            "maximum_mach": inputs["data:propulsion:rubber_engine:maximum_mach"],
            "design_altitude": inputs["data:propulsion:rubber_engine:design_altitude"],
            "delta_t4_climb": inputs["data:propulsion:rubber_engine:delta_t4_climb"],
            "delta_t4_cruise": inputs["data:propulsion:rubber_engine:delta_t4_cruise"],
            "mto_thrust": inputs["data:propulsion:MTO_thrust"],
        }

        return RubberEngine(**engine_params)


@ValidityDomainChecker(
    {
        "data:propulsion:altitude": (None, 20000.0),
        "data:propulsion:mach": (0.75, 0.85),  # limitation of SFC ratio model
        "data:propulsion:rubber_engine:overall_pressure_ratio": (20.0, 40.0),
        "data:propulsion:rubber_engine:bypass_ratio": (3.0, 6.0),
        "data:propulsion:thrust_rate": (0.5, 1.0),  # limitation of SFC ratio model
        "data:propulsion:rubber_engine:turbine_inlet_temperature": (
            1400.0,
            1600.0,
        ),  # limitation of max thrust model
        "data:propulsion:rubber_engine:delta_t4_climb": (
            -100.0,
            0.0,
        ),  # limitation of max thrust model
        "data:propulsion:rubber_engine:delta_t4_cruise": (
            -100.0,
            0.0,
        ),  # limitation of max thrust model
    }
)
class OMRubberEngine(OMIEngine):
    """
    Parametric engine model as OpenMDAO component

    See :class:`RubberEngine` for more information.
    """

    def setup(self):
        super().setup()
        self.get_engine().setup(self)

    @staticmethod
    def get_engine() -> DirectEngine:
        return DirectRubberEngine()
