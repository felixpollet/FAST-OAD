# -*- coding: utf-8 -*-
"""
  disc2.py generated by WhatsOpt. 
"""
from .disc2_base import Disc2Base


class Disc2(Disc2Base):
    """ An OpenMDAO component to encapsulate Disc2 discipline """

    def compute(self, inputs, outputs):
        """
        Evaluates the equation
        y2 = y1**(.5) + z1 + z2
        """

        z1 = inputs['z'][0]
        z2 = inputs['z'][1]
        y1 = inputs['y1']

        # Note: this may cause some issues. However, y1 is constrained to be
        # above 3.16, so lets just let it converge, and the optimizer will
        # throw it out
        if y1.real < 0.0:
            y1 *= -1

        outputs['y2'] = y1 ** .5 + z1 + z2

# Reminder: inputs of compute()
#   
#       inputs['z'] -> shape: 1, type: Float    
#       inputs['y1'] -> shape: 1, type: Float      

# To declare partial derivatives computation ...
# 
#    def setup(self):
#        super(Disc2, self).setup()
#        self.declare_partials('*', '*')  
#			
#    def compute_partials(self, inputs, partials):
#        """ Jacobian for Disc2 """
#   
#       	partials['y2', 'z'] = np.zeros((1, 1))
#       	partials['y2', 'y1'] = np.zeros((1, 1))
