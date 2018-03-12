# -*- coding: utf-8 -*-

"""
This python class implements a Ensemble of particles, each consisting of a single drifter in its own ocean state. The perturbation parameter is the wind direction.


Copyright (C) 2018  SINTEF ICT

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""


from matplotlib import pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
import time
import abc

import CDKLM16
import GPUDrifterCollection
import Common
import DataAssimilationUtils as dautils


class DrifterEnsemble:
        
    def __init__(self, cl_ctx, numParticles, observation_variance=0.0):
        
        self.cl_ctx = cl_ctx
        
        self.numParticles = numParticles
        self.particles = [None]*(self.numParticles + 1)
        
        self.obs_index = self.numParticles
        
        self.simType = 'CDKLM16'
        
        self.observation_variance = observation_variance
        
    # UNCHANGED
    def cleanUp(self):
        for oceanState in self.particles:
            if oceanState is not None:
                oceanState.cleanUp()
    
    # ADDED
    def setGridInfoFromSim(self, sim):
        eta, hu, hv = sim.download()
        Hi = sim.downloadBathymetry()[0]
        self.setGridInfo(sim.nx, sim.ny, sim.dx, sim.dy, sim.dt,
                         sim.boundary_conditions,
                         eta=eta, hu=hu, hv=hv, H=Hi)
        self.setParameters(f=sim.f, g=sim.g, beta=sim.coriolis_beta, r=sim.r, wind=sim.wind_stress)
        
    # IMPROVED
    def setGridInfo(self, nx, ny, dx, dy, dt, boundaryConditions, eta=None, hu=None, hv=None, H=None):
        self.nx = nx
        self.ny = ny
        self.dx = dx
        self.dy = dy
        self.dt = dt
        
        # Default values for now:
        self.initialization_variance = 10*dx
        self.midPoint = 0.5*np.array([self.nx*self.dx, self.ny*self.dy])
        self.initialization_cov = np.eye(2)*self.initialization_variance
        
        self.boundaryConditions = boundaryConditions
        
        assert(self.simType == 'CDKLM16'), 'CDKLM16 is currently the only supported scheme'
        #if self.simType == 'CDKLM16':
        self.ghostCells = np.array([2,2,2,2])
        if self.boundaryConditions.isSponge():
            sponge = self.boundaryConditions.getSponge()
            for i in range(4):
                if sponge[i] > 0: 
                    self.ghostCells[i] = sponge[i]
        dataShape =  ( ny + self.ghostCells[0] + self.ghostCells[2], 
                       nx + self.ghostCells[1] + self.ghostCells[3]  )
            
        self.base_eta = eta
        self.base_hu = hu
        self.base_hv = hv
        self.base_H = H
            
        # Create base initial data: 
        if self.base_eta is None:
            self.base_eta = np.zeros(dataShape, dtype=np.float32, order='C')
        if self.base_hu is None:
            self.base_hu  = np.zeros(dataShape, dtype=np.float32, order='C');
        if self.base_hv is None:
            self.base_hv  = np.zeros(dataShape, dtype=np.float32, order='C');
        
        # Bathymetry:
        if self.base_H is None:
            waterDepth = 10
            self.base_H = np.ones((dataShape[0]+1, dataShape[1]+1), dtype=np.float32, order='C')*waterDepth
 

        self.setParameters()
    
    
    # IMPROVED
    def setParameters(self, f=0, g=9.81, beta=0, r=0, wind=Common.WindStressParams(type=99)):
        self.g = g
        self.f = f
        self.beta = beta
        self.r = r
        self.wind = wind
    
    
    # ---------------------------------------
    # Needs to be abstract!
    # ---------------------------------------
    def init(self):

        self.sim = CDKLM16.CDKLM16(self.cl_ctx, \
                                   self.base_eta, self.base_hu, self.base_hv, \
                                   self.base_H, \
                                   self.nx, self.ny, self.dx, self.dy, self.dt, \
                                   self.g, self.f, self.r, \
                                   wind_stress=self.wind, \
                                   boundary_conditions=self.boundaryConditions, \
                                   write_netcdf=False)

        # TO CHECK! Is it okay to have drifters as self.drifters - in order to easier reach its member functions?
        drifters = GPUDrifterCollection.GPUDrifterCollection(self.cl_ctx, self.numParticles,
                      observation_variance=self.observation_variance,
                      boundaryConditions=self.boundaryConditions,
                      domain_size_x=self.nx*self.dx, domain_size_y=self.ny*self.dy)
        
        drifters.initializeUniform()
        self.sim.attachDrifters(drifters)
    
    
    def observeParticles(self):
        return self.sim.drifters.getDrifterPositions()
    
    def observeTrueState(self):
        return self.sim.drifters.getObservationPosition()
    
    def step(self, t):
        return self.sim.step(t)
    
    def getDistances(self, obs=None):
        return self.sim.drifters.getDistances()
       
    def resample(self, newSampleIndices, reinitialization_variance):
        self.sim.drifters.resample(newSampleIndices, reinitialization_variance)
                    
    def getEnsembleMean(self):
        return self.sim.drifters.getEnsembleMean()
    
    def plotDistanceInfo(self, title=None):
        self.sim.drifters.plotDistanceInfo()
            
    def enforceBoundaryConditions(self):
        self.sim.drifters.enforceBoundaryConditions()
    
    ### Duplication of code
    def getDomainSizeX(self):
        return self.nx*self.dx
    def getDomainSizeY(self):
        return self.ny*self.dy
    def getObservationVariance(self):
        return self.observation_variance
    def getNumParticles(self):
        return self.numParticles
    
