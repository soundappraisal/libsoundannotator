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
from libsoundannotator.streamboard.continuity import Continuity, processorAlignment
import patchExtractor as patchExtractor 
import uuid, copy


from json import loads, dumps
from hashlib import sha1

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
    
    def __init__(self,level,t_low, t_high, s_low, s_high, size, t_offset=None, typelabel=None, serial_number=0, samplerate=0, chunknumber=None, **kwargs):
        self.identifier=uuid.uuid1()
        self.chunknumber=chunknumber
        self.typelabel=typelabel
        self.level=level
        self.s_shape=(s_high-s_low+1,)
        self.s_range=np.array([s_low,s_high])
        self.t_shape=(t_high-t_low+1,)
        
        if not t_offset == None:
            assert(samplerate > 0)
            self.samplerate=float(samplerate)
            self.t_range_seconds=np.array([t_low/self.samplerate+t_offset,t_high/self.samplerate+t_offset+1.0/self.samplerate])
        else:
            assert(samplerate > 0)
            self.samplerate=float(samplerate)
            self.t_range_seconds=np.array([t_low/self.samplerate,t_high/self.samplerate+1.0/self.samplerate])
        
        self.duration=self.t_range_seconds[1] -self.t_range_seconds[0] 
        self.height=self.s_shape[0]
        self.fillratio=size/(self.duration*self.height)
            
        self.framerange=((chunknumber,t_low),(chunknumber,t_high))
        self.size=size
        self.inFrameDistributions=dict()
        self.inScaleDistributions=dict()
        self.serial_number=serial_number
    
    def copy(self):
        return copy.copy(self)
    
    
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
            
    def merge_descriptors(self, other):
        
        # Code written in such a way that swapping arguments should not 
        # affect resulting descriptors.
        other_=other.copy()
        self_=self.copy()
        
        #  Use the most recent identifier. This way the same identifier 
        #  will not occur twice in the processor output
        if self_.serial_number > other_.serial_number: 
            self.identifier=self_.identifier
        else:
            self.identifier=other_.identifier
         
        assert(self_.typelabel==other_.typelabel)
        assert(other_.level==self_.level)
                
        self.s_range=np.array(  [   np.min([other_.s_range[0],self_.s_range[0]]),
                                    np.max([other_.s_range[1],self_.s_range[1]])]    )
        self.s_shape=(self.s_range[1]-self.s_range[0]+1,)
        assert self.s_range[1]>=self.s_range[0], '{0}'.format(self)
        self.t_range_seconds=np.array(  [   np.min([other_.t_range_seconds[0],self_.t_range_seconds[0]]),
                                    np.max([other_.t_range_seconds[1],self_.t_range_seconds[1]])]    )
        
        self.framerange=(   min(other_.framerange[0],self_.framerange[0]),
                            max(other_.framerange[1],self_.framerange[1])  )
                             
        self.t_shape=(other_.t_shape[0]+self_.t_shape[0],)
        
        #assert self.t_range_seconds[1]>=self.t_range_seconds[0], '{0}'.format(self)
        self.size=other_.size+self_.size
        
        
        self.duration=self.t_range_seconds[1] -self.t_range_seconds[0] 
        self.height=self.s_shape[0]
        self.fillratio=self.size/(self.duration*self.height)
        
        
        self.serial_number=np.min([self_.serial_number,other_.serial_number])
        
        
        #print('level: {0} and framerange: {1} in MERGE'.format(self.level,self.framerange))
        
        
        return self
        
    def merge(self, other ):
        scalemerge=False
        framemerge=False
        for ts_rep in self.inScaleDistributions.keys():
            self.inScaleDistributions[ts_rep],    inScaleCount = joinScaleDistributions(
                self.inScaleDistributions[ts_rep], 
                other.inScaleDistributions[ts_rep], 
                self.s_range, 
                other.s_range, 
                self.inScaleCount,
                other.inScaleCount 
               )
            scalemerge=True
            
        for ts_rep in self.inFrameDistributions.keys():
            self.inFrameDistributions[ts_rep], inFrameCount = joinFrameDistributions(
                self.inFrameDistributions[ts_rep], 
                other.inFrameDistributions[ts_rep], 
                self.framerange, 
                other.framerange, 
                self.inFrameCount,
                other.inFrameCount 
               )
            framemerge=True
               
         
               
        if scalemerge:  
            self.inScaleCount=inScaleCount 
        else: #No representations available so lets calculate the inScale count
            inScaleCount,    self.inScaleCount = joinScaleDistributions(
                self.inScaleCount, 
                other.inScaleCount, 
                self.s_range, 
                other.s_range, 
                self.inScaleCount,
                other.inScaleCount 
               )     
        
        if framemerge:  
            self.inFrameCount=inFrameCount 
        else: #No representations available so lets calculate the inFrame count
            inFrameCount, self.inFrameCount = joinFrameDistributions(
                self.inFrameCount, 
                other.inFrameCount, 
                self.framerange, 
                other.framerange, 
                self.inFrameCount,
                other.inFrameCount 
               )     
          
        
        self.merge_descriptors( other)
        
       
         
    def __str__(self):
        
        
        returnstring='Patch at level={0}, \n size={1} \n  '.format(
            self.level,self.size)   
        
        #returnstring=' inScaleCount={2} \n inFrameCount={3} \n '.format(
        #    self.inScaleCount ,self.inFrameCount)   
        
        returnstring+=("Patch descriptors:\n  uuid={0},"+
        " \n typelabel={1} \n level={2} \n s_shape={3} "+
        " \n s_range={4} \n t_shape={5} \n t_range_seconds={6} "+
        "\n size={7} \n serial_number={8} \n framerange={9} \n").format(
        self.identifier,
        self.typelabel,
        self.level,
        self.s_shape,
        self.s_range,
        self.t_shape,
        self.t_range_seconds,
        self.size,
        self.serial_number,
        self.framerange,)
        
        '''
        for ts_rep in self.inScaleDistributions.keys():
            returnstring+='\n tsrep: {0}, value: {1}'.format(ts_rep,self.inScaleDistributions[ts_rep] )
            
        for ts_rep in self.inFrameDistributions.keys():
            returnstring+='\n tsrep: {0}, value: {1}'.format(ts_rep,self.inFrameDistributions[ts_rep] )'''
        return  returnstring
   
def joinScaleDistributions( dist1, dist2, range1, range2, weights1, weights2 ):
    newrange=np.array([np.min([range1[0],range2[0]]),np.max([range1[1],range2[1]])]);
    newdist=np.zeros([newrange[1]-newrange[0]+1])
    newweights=np.zeros([newrange[1]-newrange[0]+1],'int32')
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
    
    return newdist, newweights

def joinFrameDistributions( dist1, dist2, 
                            framerange1, framerange2, 
                            weights1, weights2, 
                            ):
    
    if framerange1[0] < framerange2[0]:
        firstindex =0
    else:
        firstindex=1

    if framerange1[1] > framerange2[1]:
        lastindex=0
    else:
        lastindex=1
    
    #print('firstindex: {0}, lastindex: {1} '.format( firstindex , lastindex ))
    framerange_list=[framerange1,framerange2]
    dist_list=[dist1,dist2]
    weights_list=[weights1,weights2]
    length_list=[weights1.shape[0],weights2.shape[0]]
    
    if framerange1[0][0] == framerange2[0][0]:                     # both Patches start in the same chunk
        offset=framerange_list[1-firstindex][0][1]-framerange_list[firstindex][0][1]    # Calculate amount the second is shifted compared to first
                
        newlength=offset+length_list[1-firstindex]
        newdist=np.zeros([newlength])
        newweights=np.zeros([newlength],'int32')
        
        newweights[0:length_list[firstindex]]+=weights_list[firstindex]
        newdist[0:length_list[firstindex]]+=dist_list[firstindex]*weights_list[firstindex]
        
        newweights[offset:]+=weights_list[1-firstindex]
        newdist[offset:]+=dist_list[1-firstindex]*weights_list[1-firstindex]
    elif framerange1[1][0] == framerange2[1][0]:         # both Patches end in the same chunk
        offset=framerange_list[lastindex][0][1]-framerange_list[1-lastindex][0][1]    # Calculate amount the second is shifted compared to first
                
        newlength=offset+length_list[1-lastindex]
        newdist=np.zeros([newlength])
        newweights=np.zeros([newlength],'int32')
        
        newweights[0:length_list[1-lastindex]]+=weights_list[1-lastindex]
        newdist[0:length_list[1-lastindex]]+=dist_list[1-lastindex]*weights_list[1-lastindex]
        
        newweights[offset:]+=weights_list[lastindex]
        newdist[offset:]+=dist_list[lastindex]*weights_list[lastindex]
    elif framerange1[1][0]+1 == framerange2[1][0]:       #  Patches end in consecutive chunks
        offset=framerange2[1][1]    # Calculate amount the second is shifted compared to first
        lastindex=1
                
        newlength=offset+length_list[1-lastindex]
        newdist=np.zeros([newlength])
        newweights=np.zeros([newlength],'int32')
        
        newweights[0:length_list[1-lastindex]]+=weights_list[1-lastindex]
        newdist[0:length_list[1-lastindex]]+=dist_list[1-lastindex]*weights_list[1-lastindex]
        
        newweights[offset:]+=weights_list[lastindex]
        newdist[offset:]+=dist_list[lastindex]*weights_list[lastindex]
    elif framerange1[1][0] == framerange2[1][0]+1:       #  Patches end in consecutive chunks
        offset=framerange1[1][1]    # Calculate amount the second is shifted compared to first
        lastindex=0
                
        newlength=offset+length_list[1-lastindex]
        newdist=np.zeros([newlength])
        newweights=np.zeros([newlength],'int32')
        
        newweights[0:length_list[1-lastindex]]+=weights_list[1-lastindex]
        newdist[0:length_list[1-lastindex]]+=dist_list[1-lastindex]*weights_list[1-lastindex]
        
        newweights[offset:]+=weights_list[lastindex]
        newdist[offset:]+=dist_list[lastindex]*weights_list[lastindex]
    else:
        raise Exception('Unanticipated merge scenario!')
    # Joining distributions can involve more than 2 patches
    # in which case the current algorithm cannot assure the 
    # patches are direct neighbours, in which case it is possible 
    # a gap arises and hence zero valued weights.
    newdist[newweights!=0]=newdist[newweights!=0]/newweights[newweights!=0]
    
    return newdist, newweights

class patchProcessorCore(object):
    
    def __init__(self,*args, **kwargs):
        self.quantizer=kwargs['quantizer']
        self.noofscales=kwargs['noofscales']
        self.logger=kwargs['logger']
        self.samplerate=kwargs['SampleRate']
        self.typelabel=kwargs['PatchType']
        
        self.tex_after=np.zeros([self.noofscales],'int32')
        self.patch_after=np.zeros([self.noofscales],'int32') 
        self.tex_before=np.zeros([self.noofscales],'int32')
        self.patch_before=np.zeros([self.noofscales],'int32')
        self.joinMatrix=np.zeros([2*self.noofscales,2],'int32')
        self.cumulativePatchCount=1 #reserve zero for non-patches
        self.inFrameDistributions=dict()
        self.inScaleDistributions=dict()
        self.newpatchlist=list()
        self.oldpatchlist=list()
        self.mergeprepared=False
        
        self.logger.info('patchProcessorCore initialized')
        
    def prerun(self):
        self.logger.info('patchProcessorCore prerun')
        self.extractor=patchExtractor.patchExtractor()

    def processData(self, chunk):
        result=None         # This is important to do, prevents publication of output if input is absent.
        
        if chunk is None:
            return result
               
        if not chunk.data.shape[1]==0:
            result=dict()
            self.logger.info('patchProcessorCore processData of chunk {0} with shape {1}'.format(chunk.number,chunk.data.shape))
            self.newpatches(chunk.data, chunk.initialSampleTime, chunk.number)
            if(chunk.continuity>=Continuity.withprevious) and self.mergeprepared == chunk.number:
                self.joinpatches()
                
            result['matrix']=self.patchMatrix
            result['patches']=self.newpatchlist
            result['levels']=self.levels
            
            
            # Store information on current patches to make them available
            # in case of a merge with next chunk
            self.tex_before[:]= np.array(self.levels[:,-1]) 
            self.patch_before[:]=np.array(self.patchMatrix[:,-1]) 
            self.oldpatchlist=self.newpatchlist            
            self.cumulativePatchCount+=self.N
            self.mergeprepared = chunk.number+1
            self.logger.info('Processed chunk {}'.format(chunk.number))
            
            finalized_patch_list=list()
            unfinalized_patch_list=list()
            for patch in self.newpatchlist:
                if patch.serial_number in self.patchMatrix[:,-1]:
                    unfinalized_patch_list.append(patch)
                else:
                    finalized_patch_list.append(patch)
                    
            result['markedpatches']={   'finalized_patches':finalized_patch_list,
                                        'unfinalized_patches':unfinalized_patch_list,
                                        'join_matrix':np.array([[a,b] for a,b in self.joinMatrix if a>0])}
            
            
        else:
            if(chunk.continuity>=Continuity.withprevious):
                result=dict()
                result['matrix']=np.zeros(chunk.data.shape)
                result['patches']=list()
                result['levels']=np.zeros(chunk.data.shape)
                result['markedpatches']={'finalized_patches':list(),
                                'unfinalized_patches':list(),
                                'join_matrix':np.zeros((0,2))}
                self.logger.info('set merge prepaered flag to : {}'.format(chunk.number+1)) 
                self.mergeprepared = chunk.number+1
            else:
                self.mergeprepared = False
        
        return result

    def newpatches(self,data,initialSampleTime,chunknumber):
            '''
            newpatches(self,data):
                Create new patches from data making use of the levels generated by the quantizer.
            '''
            self.levels=self.quantizer.levels(data)
            self.patchMatrix=np.zeros(np.shape(self.levels),'int32')
            self.N=self.extractor.cpp_calcPatches(self.levels,self.patchMatrix)
            
            # Correct the patch count from the raw value coming from  
            # the C++ code. In this patch count merging is ignored for simplicity.
            #   ... but first prevent garbage collection of memory in use by c++ code,
            #   all patch related info needs to be copied to python datastructures in 
            #   the scope containing the call to cpp_calcPatches before it can be safely
            #   collected.
            keepMemoryAllocatedForCPPCode=self.patchMatrix     
            self.patchMatrix=self.patchMatrix+self.cumulativePatchCount
            
            self.descriptors=np.zeros([6,self.N],'int32') 
            self.extractor.cpp_getDescriptors(self.descriptors)
            
            self.newpatchlist=list()
            for patchNo in np.arange(self.N):
                # Set simplest patch descriptors
                newPatch=Patch(*self.descriptors[:,patchNo],
                                t_offset=initialSampleTime,
                                serial_number=patchNo+self.cumulativePatchCount,
                                samplerate=self.samplerate,
                                typelabel=self.typelabel,
                                chunknumber=chunknumber)
                                
                # Get and set in row count of timescale pixels
                inScaleCount=np.zeros(newPatch.s_shape,'int32')
                self.extractor.cpp_getInRowCount(int(patchNo),inScaleCount)
                newPatch.set_inScaleCount(inScaleCount)
                
                # Get and set in column count of timescale pixels
                inFrameCount=np.zeros(newPatch.t_shape,'int32')
                self.extractor.cpp_getInColCount(int(patchNo),inFrameCount)
                newPatch.set_inFrameCount(inFrameCount)
                
                
                 # Get and set in row count of timescale pixels
                inScaleLowerFrame=np.zeros(newPatch.s_shape,'int32')
                inScaleUpperFrame=np.zeros(newPatch.s_shape,'int32')
                self.extractor.cpp_getInRowExtrema(int(patchNo),inScaleLowerFrame,inScaleUpperFrame)
                
                # Get and set in column count of timescale pixels
                inFrameLowerScale=np.zeros(newPatch.t_shape,'int32')
                inFrameUpperScale=np.zeros(newPatch.t_shape,'int32')
                self.extractor.cpp_getInColExtrema(int(patchNo),inFrameLowerScale,inFrameUpperScale)
                
                
                self.newpatchlist.append(newPatch)
            
    def joinpatches(self):
            
            ''' 
            joinpatches: join incomplete patches over the 
            chunkboundary if they belong together. They belong together 
            if their frequencies are aligned and they have the same 
            texture label. 
            
            The resulting patches have a uuid generated with the new patch 
            and a serial number corresponding the earliest patch to which 
            it is continuously connected.
            '''
            
           
            # Copy patch information from the C++ code provided patch 
            # information.
            self.tex_after[:]= np.array(self.levels[:,0])
            self.patch_after[:]=np.array(self.patchMatrix[:,0])
            
            # Allocate memory for the result provided by C++ code
            self.joinMatrix=np.zeros([2*self.noofscales,2],'int32')
            
            # Calculate the number of valid patches and the matrix 
            # describing which patches need to be joined. This joinMatrix 
            # is passed as an argument but its elements are changed in place! 
            validpatches=self.extractor.cpp_calcJoinMatrix(self.tex_before, 
                self.tex_after,
                self.patch_before, 
                self.patch_after, 
                self.joinMatrix      # this matrix holds part of the result.
            )
            
            # Replace current patch numbers with those indicated in the joinMatrix
            for patchNo in  np.arange(validpatches):
                if not(self.joinMatrix[patchNo,1] ==   self.joinMatrix[patchNo,0]):
                    # Update the patchMatrix to reflect correct joining of patches
                    self.patchMatrix[self.joinMatrix[patchNo,0]==self.patchMatrix]=self.joinMatrix[patchNo,1] 
                    
            # Update the new patches to reflect correct joining of patches
            updatedPatchList=list()
            oldpatches=dict()
            newpatches=dict()
            
            continuedpatches=set()
            patchestokeep=set()
            
            for patch in self.oldpatchlist:
                oldpatches[patch.serial_number]=patch
            
            for patch in self.newpatchlist:
                newpatches[patch.serial_number]=patch
                patchestokeep=patchestokeep.union({patch.serial_number,})
            
            for patchNo in np.arange(validpatches):
                patch_key_for_new_chunk=self.joinMatrix[patchNo,0]
                
                if patch_key_for_new_chunk in newpatches.keys():
                    patch_for_new_chunk=newpatches[patch_key_for_new_chunk]
                    if not self.joinMatrix[patchNo,1] ==  patch_key_for_new_chunk: 
                        # The patch is involved in merge over the chunk boundary, 
                        # remove from the list of unaffected patches. 
                        patchestokeep=patchestokeep.difference({patch_key_for_new_chunk,})  
                        
                        # Get the old patch involved in the merge and merge
                        patch_key_for_old_chunk=self.joinMatrix[patchNo,1]
                        if patch_key_for_old_chunk in oldpatches.keys():
                            continued_patch=oldpatches[patch_key_for_old_chunk]   
                            continuedpatches=continuedpatches.union({continued_patch.serial_number, })
                            # Merge in place from the perspective of the dictionary.
                            # The same old patch can appear more than once in the joinMatrix, we can therefore
                            # not append the resulting patch to the updatedPatchList here. 
                            oldpatches[continued_patch.serial_number]=patch_for_new_chunk.merge_descriptors(continued_patch)
                            
            for serial_number in continuedpatches:
                updatedPatchList.append(oldpatches[serial_number])
     
            for serial_number in patchestokeep:
                updatedPatchList.append(newpatches[serial_number])
                
            self.newpatchlist=updatedPatchList
            
           

class patchProcessor(Processor):
    requiredKeys=['TSRep']
    
    featurenames=['matrix','patches','levels','markedpatches']
    eventLikeFeature=dict(zip(featurenames,[False,True,False,True]))
    
    def __init__(self,boardConn, name,*args, **kwargs):
        super(patchProcessor, self).__init__(boardConn, name,*args, **kwargs)
        self.args=args
        self.kwargs=kwargs
        self.requiredParameters('SampleRate','TS_Rep')
        self.samplerate=self.config['SampleRate']
        self.setProcessorAlignments()
        
    def prerun(self):
        super(patchProcessor, self).prerun()
        self.kwargs['logger']=self.logger
        self.kwargs['SampleRate']=self.samplerate
        
        self.kwargs['SampleRate']=self.samplerate
        self.kwargs['PatchType']={'ts_rep':self.config['TS_Rep'],'quantizer':type(self.config['quantizer']).__name__ }
        self.patchProcessorCore=patchProcessorCore(*self.args,**self.kwargs)
        self.patchProcessorCore.prerun()

    def processData(self,data ):
        
        chunk=data.received['TSRep']
        
        dataout=self.patchProcessorCore.processData(chunk)
            
        return dataout

    def getsamplerate(self,key):
         return self.samplerate
        
    def setProcessorAlignments(self):        
        ''' 
        setProcessorAlignments: set the dictionary self.processorAlignments. 
        
        '''
        self.processorAlignments=dict()
        
        for featureName in self.featurenames: 
            self.processorAlignments[featureName]=processorAlignment(fsampling=self.getsamplerate(featureName),eventlike=self.eventLikeFeature[featureName])


    def getMetaData(self):
        self.config_serializable=self.config.copy()
        self.config_serializable['quantizer']=type(self.config_serializable['quantizer']).__name__
        
        
        config_json=dumps(self.config_serializable, sort_keys=True)
        config_hash=sha1(config_json).hexdigest()
        return  config_hash, config_json
