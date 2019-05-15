# -*- coding: utf-8 -*-
"""
  functions.py generated by WhatsOpt. 
"""
from math import exp

from .functions_base import FunctionsBase


class Functions(FunctionsBase):
    """ An OpenMDAO component to encapsulate Functions discipline """

    def compute(self, inputs, outputs):
        """ Functions computation """

        z1 = inputs['z'][0]
        z2 = inputs['z'][1]
        x1 = inputs['x']
        y1 = inputs['y1']
        y2 = inputs['y2']

        outputs['f'] = x1 ** 2 + z2 + y1 + exp(-y2)
        outputs['g1'] = 3.16 - y1
        outputs['g2'] = y2 - 24.0
# Reminder: inputs of compute()
#   
#       inputs['x'] -> shape: 1, type: Float    
#       inputs['z'] -> shape: 1, type: Float    
#       inputs['y1'] -> shape: 1, type: Float    
#       inputs['y2'] -> shape: 1, type: Float      

# To declare partial derivatives computation ...
# 
#    def setup(self):
#        super(Functions, self).setup()
#        self.declare_partials('*', '*')  
#			
#    def compute_partials(self, inputs, partials):
#        """ Jacobian for Functions """
#   
#       	partials['f', 'x'] = np.zeros((1, 1))
#       	partials['f', 'z'] = np.zeros((1, 1))
#       	partials['f', 'y1'] = np.zeros((1, 1))
#       	partials['f', 'y2'] = np.zeros((1, 1))
#       	partials['g1', 'x'] = np.zeros((1, 1))
#       	partials['g1', 'z'] = np.zeros((1, 1))
#       	partials['g1', 'y1'] = np.zeros((1, 1))
#       	partials['g1', 'y2'] = np.zeros((1, 1))
#       	partials['g2', 'x'] = np.zeros((1, 1))
#       	partials['g2', 'z'] = np.zeros((1, 1))
#       	partials['g2', 'y1'] = np.zeros((1, 1))
#       	partials['g2', 'y2'] = np.zeros((1, 1))
