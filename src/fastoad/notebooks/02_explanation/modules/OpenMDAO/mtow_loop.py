from .geometry.geometry import ComputeGeometry
from .aerodynamic.aerodynamic import ComputeAerodynamics
from .mass.mass import ComputeMass
from .performance.performance import ComputePerformance

import openmdao.api as om


class UpdateMTOW(om.Group):
    """
    Gather all the discipline module/groups into the main problem
    """

    def setup(self):

        self.add_subsystem(name="compute_geometry", subsys=ComputeGeometry(), promotes=["*"])
        self.add_subsystem(
            name="compute_aerodynamics", subsys=ComputeAerodynamics(), promotes=["*"]
        )
        self.add_subsystem(name="compute_mass", subsys=ComputeMass(), promotes=["*"])
        self.add_subsystem(name="compute_performance", subsys=ComputePerformance(), promotes=["*"])
