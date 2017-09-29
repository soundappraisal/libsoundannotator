'''
This file is part of libsoundannotator. The library libsoundannotator is 
designed for processing sound using time-frequency representations.

Copyright 2011-2014 Sensory Cognition Group, University of Groningen
Copyright 2014-2017 SoundAppraisal BV

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
'''
# -*- coding: u8 -*-
import numpy as np

from libsoundannotator.streamboard.processor  import Processor, Continuity
from libsoundannotator.streamboard.continuity import Continuity
import patchExtractor as patchExtractor 
import uuid

class Quantizer(object):
    def levels(self, data):
         self.overrideError('processData')

class LogFloorQuantizer(Quantizer):
    def levels(self, data):
         return (np.floor(np.log(data))).astype(int)
    
class FloorQuantizer(Quantizer):
    def levels(self, data):
         return (20*np.floor(data/20)-30).astype(int)
        
class textureQuantizer(Quantizer):
    def levels(self, data):
         results= -np.ones(np.shape(data),dtype='int32')
         results[data > 0 ]=0
         results[data > 20]=1
         results[data > 60]=2
         return results

class Patch(object):
    
    def __init__(self,level,t_low, t_high, s_low, s_high, size, **kwargs):
        self.identifier=uuid.uuid1()
        self.typelabel=None
        self.level=level
        self.s_shape=(s_high-s_low+1,)
        self.s_range=np.array([s_low,s_high])
        self.t_shape=(t_high-t_low+1,)
        self.t_range=np.array([t_low,t_high])
        self.size=size
        self.inFrameDistributions=dict()
        self.inScaleDistributions=dict()
    
    def set_inFrameCount(self,inFrameCount):
        self.inFrameCount=inFrameCount
    
    def set_inFrameDistribution(self,ts_rep_name,distribution):
        # ts_rep_name: timescale representation name
        assert (distribution.shape == self.t_shape)
        self.inFrameDistributions[ts_rep_name] = distribution
        
    def set_inScaleCount(self,inScaleCount):
        self.inScaleCount=inScaleCount

    def set_inScaleDistribution(self,ts_rep_name,distribution):
        # ts_rep_name: timescale representation name
        assert (distribution.shape == self.s_shape)
        self.inScaleDistributions[ts_rep_name] = distribution
            
    def merge(self, other ):
        scalemerge=False
        framemerge=False
        for ts_rep in self.inScaleDistributions.keys():
            self.inScaleDistributions[ts_rep],  s_range,  inScaleCount = joinDistributions(
                self.inScaleDistributions[ts_rep], 
                other.inScaleDistributions[ts_rep], 
                self.s_range, 
                other.s_range, 
                self.inScaleCount,
                other.inScaleCount 
               )
            scalemerge=True
            
        for ts_rep in self.inFrameDistributions.keys():
            self.inFrameDistributions[ts_rep],  t_range,  inFrameCount = joinDistributions(
                self.inFrameDistributions[ts_rep], 
                other.inFrameDistributions[ts_rep], 
                self.t_range, 
                other.t_range, 
                self.inFrameCount,
                other.inFrameCount 
               )
            framemerge=True
               
         
               
        if scalemerge:      
            self.s_range=s_range  
            self.inScaleCount=inScaleCount 
            self.s_shape=(self.s_range[1]-self.s_range[0]+1,)
        else:
            inScaleCount,  self.s_range,  self.inScaleCount = joinDistributions(
                self.inScaleCount, 
                other.inScaleCount, 
                self.s_range, 
                other.s_range, 
                self.inScaleCount,
                other.inScaleCount 
               )     
        
        if framemerge:    
            self.t_range=t_range  
            self.inFrameCount=inFrameCount 
            self.t_shape=(self.t_range[1]-self.t_range[0]+1,)
        else:
            inFrameCount,  self.t_range,  self.inFrameCount = joinDistributions(
                self.inFrameCount, 
                other.inFrameCount, 
                self.t_range, 
                other.t_range, 
                self.inFrameCount,
                other.inFrameCount 
               )     
          
        
        self.size+=other.size
        
       
         
    def __str__(self):
        returnstring='Patch at level={0}, \n size={1} \n inScaleCount={2} \n inFrameCount={3} '.format(
            self.level,self.size,self.inScaleCount ,self.inFrameCount)   
        
        for ts_rep in self.inScaleDistributions.keys():
            returnstring+='\n tsrep: {0}, value: {1}'.format(ts_rep,self.inScaleDistributions[ts_rep] )
            
        for ts_rep in self.inFrameDistributions.keys():
            returnstring+='\n tsrep: {0}, value: {1}'.format(ts_rep,self.inFrameDistributions[ts_rep] )
        return  returnstring
   
def joinDistributions( dist1, dist2, range1, range2, weights1, weights2 ):
    newrange=np.array([np.min([range1[0],range2[0]]),np.max([range1[1],range2[1]])]);
    newdist=np.zeros([newrange[1]-newrange[0]+1]);
    newweights=np.zeros([newrange[1]-newrange[0]+1],'int32');
    len1=weights1.shape[0]
    pos1=range1[0]-newrange[0]
    newweights[pos1:pos1+len1]+=weights1
    newdist[pos1:pos1+len1]+=dist1*weights1
    
    len2=weights2.shape[0]
    pos2=range2[0]-newrange[0]
    newweights[pos2:pos2+len2]+=weights2
    newdist[pos2:pos2+len2]+=dist2*weights2
    
    # Joining distributions can involve more than 2 patches
    # in which case the current algorithm cannot assure the 
    # patches are direct neighbours, in which case it is possible 
    # a gap arises and hence zero valued weights.
    newdist[newweights!=0]=newdist[newweights!=0]/newweights[newweights!=0]
    
    return newdist, newrange, newweights

         
class patchProcessorCore(object):
    
    def __init__(self,*args, **kwargs):
        self.quantizer=kwargs['quantizer']
        self.noofscales=kwargs['noofscales']
        self.logger=kwargs['logger']
        self.logger.info('patchProcessorCore initialized')
        self.tex_after=np.zeros([self.noofscales],'int32')
        self.patch_after=np.zeros([self.noofscales],'int32') 
        self.tex_before=np.zeros([self.noofscales],'int32')
        self.patch_before=np.zeros([self.noofscales],'int32')
        self.joinMatrix=np.zeros([2*self.noofscales,2],'int32')
        self.cumulativePatchCount=0
        self.inFrameDistributions=dict()
        self.inScaleDistributions=dict()
        
    def prerun(self):
        self.logger.info('patchProcessorCore prerun')
        self.extractor=patchExtractor.patchExtractor()

    def processData(self, chunk):
        
        # Assuming the first data source is E
        if (chunk is None):
            pass
        else:
            self.logger.info('patchProcessorCore processData with shape {0}'.format(chunk.data.shape))
            self.newpatches(chunk.data)
            if(chunk.continuity>=Continuity.withprevious):
                self.joinpatches()
            return self.patchMatrix
        # This is important to do, prevents trying to output.
        return None

    def newpatches(self,data):
            self.levels=self.quantizer.levels(data)
            self.patchMatrix=np.zeros(np.shape(self.levels),'int32')
            self.N=self.extractor.cpp_calcPatches(self.levels,self.patchMatrix)
            descriptors=np.zeros([6,self.N],'int32')
            self.extractor.cpp_getDescriptors(descriptors)
            self.newpatchlist=list()
            for patchNo in np.arange(self.N):
                # Set simplest patch descriptors
                newPatch=Patch(*descriptors[:,patchNo])
                
                # Get and set in row count of timescale pixels
                inScaleCount=np.zeros(newPatch.s_shape,'int32')
                self.extractor.cpp_getInRowCount(int(patchNo),inScaleCount)
                newPatch.set_inScaleCount(inScaleCount)
                
                # Get and set in column count of timescale pixels
                inFrameCount=np.zeros(newPatch.t_shape,'int32')
                self.extractor.cpp_getInColCount(int(patchNo),inFrameCount)
                newPatch.set_inFrameCount(inFrameCount)
                
                self.newpatchlist.append(newPatch)

            
    def joinpatches(self):
            self.patchMatrix[:,:]+=self.cumulativePatchCount
            self.cumulativePatchCount+=self.N
           
            self.tex_after[:]= np.array(self.levels[:,0])
            self.patch_after[:]=np.array(self.patchMatrix[:,0])
          
            validpatches=self.extractor.cpp_calcJoinMatrix(self.tex_before, 
                self.tex_after,
                self.patch_before, 
                self.patch_after, 
                self.joinMatrix 
            )
            
            for patchNo in  np.arange(validpatches):
                if not(self.joinMatrix[patchNo,1] ==   self.joinMatrix[patchNo,0]):
                    self.patchMatrix[self.joinMatrix[patchNo,0]==self.patchMatrix]=self.joinMatrix[patchNo,1] 
            
            self.tex_before[:]= np.array(self.levels[:,-1])     
            self.patch_before[:]=np.array(self.patchMatrix[:,-1])

class patchProcessor(Processor):
    requiredKeys=['TSRep']
    
    def __init__(self,boardConn, name,*args, **kwargs):
        super(patchProcessor, self).__init__(boardConn, name,*args, **kwargs)
        self.args=args
        self.kwargs=kwargs
        
        
    def prerun(self):
        super(patchProcessor, self).prerun()
        self.kwargs['logger']=self.logger
        self.patchProcessorCore=patchProcessorCore(*self.args,**self.kwargs)
        self.patchProcessorCore.prerun()

    def processData(self,data ):
        
        chunk=data.received['TSRep']
        if chunk is None or  chunk.data.shape[1]==0:
            dataout=None
        else:
            dataout=dict()
            dataout['patches']=self.patchProcessorCore.processData(chunk)
            dataout['levels']=self.patchProcessorCore.levels
        return dataout