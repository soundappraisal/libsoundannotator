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
import numpy as np
import logger
import time

from continuity import Continuity, chunkAlignment


class DataChunk(object):
    """ A chunk of data, starting at a specific time and at a specific
        framerate
    """

    def __init__(self,  data, 
                        startTime, 
                        fs, 
                        processorname, 
                        sources, 
                        continuity=Continuity.withprevious, 
                        number=0, 
                        alignment=chunkAlignment(), 
                        dataGenerationTime=dict(), 
                        identifier=None,
                        metadata = dict(), 
                        initialSampleTime=None):

        assert(type(sources) is set)
        self.sources = sources
        
        self.data = data
        self.startTime = startTime
        self.fs = fs
        self.processorname = processorname
        self.continuity=continuity
        self.number=number
        self.alignment=alignment
        
        self.setDataGenerationTime(dataGenerationTime)
        self.identifier = identifier
        self.setMetaData(metadata)
        self.initialSampleTime=initialSampleTime

    def getLength(self):
        return np.shape(self.data)[0]

    def setMetaData(self, metadata):
        if type(metadata) == dict:
            self.metadata = metadata
        else:
            raise ValueError('DataChunk Metadata should be of type dict, processorname= {0}, metadata= {1}'.format(self.processorname,metadata))
    
    def setDataGenerationTime(self,dataGenerationTime):
        if type(dataGenerationTime) == dict:
            self.dataGenerationTime = dataGenerationTime
        else:
            raise ValueError('DataChunk dataGenerationTime should be of type dict, processorname= {0}, type discovered is {1}'.format(self.processorname,type(dataGenerationTime)))
    
    
    def getMetaData(self):
        return self.metadata

class compositeChunk(object):
    """ A composite of chunk of data, deriving from the same preceding source chunk.
    """
    
    incomplete=0
    complete=1
    processed=2
    
    def __init__(self, number, requiredKeys, 
                    startTime=None,
                    dataGenerationTime=None,
                    metadata=None,
                    identifier=None,
                    initialSampleTime=None):
                        
        self.status=compositeChunk.incomplete
        
        self.openKeys=set(requiredKeys)
        self.received=dict()
        self.number=number
        
        # used in processData by certain procesors
        self.startTime=startTime
        self.initialSampleTime=initialSampleTime
        self.dataGenerationTime=dataGenerationTime
        self.metadata=metadata
        self.identifier=identifier
        
        # used in publish
        self.alignment=chunkAlignment()
        self.continuity=Continuity.withPrevious
        
        self.chunkcontinuity=Continuity.withPrevious
        
    def update(self, receiverKey, chunk):
        
        assert(self.number==chunk.number)
        
        if receiverKey in self.openKeys:
            self.received[receiverKey]=chunk
            self.openKeys.remove(receiverKey)
        else:
            raise ValueError('Incorrect key ({0}) passed to compositeChunk.update'.format(receiverKey))
           

        if len(self.openKeys)==0:
            self.status = compositeChunk.complete

        return self.status
    
            
   
class compositeManager(object):

    def __init__(self, requiredKeys,processor):
        self.requiredKeys=frozenset(requiredKeys)
        self.processor=processor
        
        '''
            compositeChunkList: central data structure of the manager contains references to all composite chunk that still need to be processed.
            
            position 0 contains the first unprocessed composite, will be processed when complete, will be discarded if a later composite completes before that time.              
        '''
        self.initialize()

     
    def initialize(self):
        self.compositeChunkList=list()
        self.lastcompleted=None 
        self.index0number=None       
        self.streamInitialized=False
        self.alignments_out=dict()
        
        #self.chunkbuffer=dict(zip(self.requiredKeys,[None].len(self.requiredKeys)))
            
    def inject(self, receiverKey, chunk):
        
        ''' If the list is empty we make the incoming chunk the 
        first compositeChunk in the list. If the chunk.number is 
        beyond the end of a non-empty list we create the intermediate 
        compositeChunk and the composite chunk needed. '''
        
        noofcomposites=len(self.compositeChunkList)
        if  noofcomposites == 0:
            newComposite=compositeChunk(chunk.number,self.requiredKeys)
            self.compositeChunkList.append(newComposite)
            self.index0number=chunk.number
        else: 
            while not chunk.number-self.index0number < noofcomposites:
                newComposite=compositeChunk(self.index0number+noofcomposites,self.requiredKeys)
                self.compositeChunkList.append(newComposite)
                noofcomposites+=1
                
        
        
        status=None
        
        index=chunk.number-self.index0number
        self.processor.logger.info('Received a chunk for key {} number {}'.format(receiverKey,chunk.number))
        if  index >= 0:
            status=self.compositeChunkList[index].update(receiverKey, chunk)
        else:
            self.processor.logger.warning('Received a chunk with an outdated chunknumber: {0} while index is at: {1}'.format(chunk.number, self.index0number))
        
        if status==compositeChunk.complete:
            self.processCompositeChunk(index)
            self.lastcompleted=self.compositeChunkList[index]
            del self.compositeChunkList[:index+1]    
            self.index0number+=index+1
     
    def processCompositeChunk(self,index):
        
        # Preprocess chunks
        continuity, chunkcontinuity   = self.calculateContinuity(index)
        starttime                     = self.calculateStartTime(index)
        
        # Some info is dynamic but stable over runtime
        if not self.streamInitialized:
            self.alignment_in, self.alignments_out  = self.calculateAlignment(index)   
            self.sources                            = self.mergeSources(index)              
            self.streamInitialized                  = True
        
        dataGenerationTime,metadata,identifier      = self.fuseMetadata(index)
        
        initialSampleTime = self.calculateInitialSampleTime(index,continuity, chunkcontinuity,starttime)
        
        
        compositechunk=self.alignIncomingChunks(index, continuity, chunkcontinuity, starttime, dataGenerationTime,metadata, identifier, initialSampleTime)
        
        data=self.processor.processData(compositechunk)   # This is where the processor is called to do the real work.
        
        
        self.processor.logger.debug("Got data in smartCompositeChunk")
        self.processor.publish(
            data, 
            continuity, 
            starttime,
            compositechunk.number,
            dataGenerationTime, 
            metadata=metadata,
            identifier=identifier,
        )
        self.processor.logger.debug("Called publish on processor")

                
        
        
    def calculateContinuity(self,index):
        '''
            calculateContinuity(self,index):
            
            Calculate continuity of the incoming and outgoing chunks.
            
            There is a dangerous aspect to this calculation, in principle  continuity is propagated,
            if however different representations disagree on the continuity the resulting continuity is not well defined.
            Because in general all inherit continuity from the injected sound they all carry the same continuity.
            Only in case of discontinuity arising from failures will this be different, however consistent continuity then arises
            from the absence of a preceding completed chunk set.
        '''
        continuity=Continuity.withprevious         # this flag includes transmission error corrections
        chunkcontinuity=Continuity.withprevious    # this one is purely derived from incoming chunks
        
        compositechunk=self.compositeChunkList[index]
        for key in self.requiredKeys:
            chunk=compositechunk.received[key]
            if chunk.continuity != Continuity.withprevious:
                    continuity=chunk.continuity
                    chunkcontinuity=chunk.continuity
        
        # Check whether there were chunks lost in transmission, if so flag the composite as discontinuous 
        # if it was of a withPrevious subtype
        
        if (continuity >= Continuity.withprevious):
            if (self.lastcompleted is None) :
                continuity=Continuity.discontinuous
            elif (compositechunk.number != self.lastcompleted.number+1 ):
                continuity=Continuity.discontinuous
            
        ''' In the old code we did this and hopefully for some silly reason
         # Set continuity for all incoming chunks
            if chunk.continuity >= Continuity.withprevious:
                chunk.continuity = self.continuity

        '''
        return continuity, chunkcontinuity
    
    def calculateAlignment(self,index):
        alignment_in=None
        alignments_out=dict()
        
        compositechunk=self.compositeChunkList[index]
        for key in self.requiredKeys:
            chunk=compositechunk.received[key]
            if alignment_in  is None:
                alignment_in=chunk.alignment.copy()
            else:
                alignment_in=alignment_in.merge(chunk.alignment)
        
        for key in self.processor.processorAlignments:
            
            if self.processor.processorAlignments[key].fsampling is None:
                raise ValueError('fsampling should be set on processor {0} for key {1}'.format(self.processor.name,key))
          
            alignment=alignment_in.impose_processor_alignment(self.processor.processorAlignments[key])
            alignments_out[key]=alignment
        
        return alignment_in, alignments_out
    
    def getAlignment(self,key):
        alignment=chunkAlignment()
        
        # If we have it we return it, otherwise we return the default
        if key in self.alignments_out:
            alignment=self.alignments_out[key]
        
        return alignment
        
        
    def mergeSources(self, index):
        sources=set()
        compositechunk=self.compositeChunkList[index]
        for key in self.requiredKeys:
            chunk=compositechunk.received[key]
            sources=sources.union(chunk.sources)
        
        return sources
    
    def calculateStartTime(self,index):
        startTime='Initial'
        
        compositechunk=self.compositeChunkList[index]
        for key in self.requiredKeys:
            chunk=compositechunk.received[key]
            
            if startTime != chunk.startTime and startTime =='Initial':
                startTime = chunk.startTime
            elif startTime != chunk.startTime:
                raise ValueError('Inconsistent start time on incoming chunks for chunk number: {0}'.format(chunk.number))
            if startTime =='Initial':
                startTime=np.array([-1])
        
        return startTime
    
    def fuseMetadata(self,index):
        compositechunk=self.compositeChunkList[index]
        dataGenerationTime=dict({self.processor.name:time.time()})
        identifier = None
        metadata=dict()
        metadata[self.processor.name]   = self.processor.getMetaData()
        
        for key in self.requiredKeys:
            chunk=compositechunk.received[key]
            
            # These are timestamps generated by the framework, they give an impression of the time spent in different subprocesses.
            dataGenerationTime=dict(compositechunk.received[key].dataGenerationTime.items()+
            dataGenerationTime.items())
            
            '''for key2,value2 in compositechunk.received[key].dataGenerationTime.viewitems():
                if not key2 in dataGenerationTime:
                    dataGenerationTime[key2]=value2
            '''
            
            metadata=dict(compositechunk.received[key].metadata.items()+
            metadata.items())
            
            
            
            # identifier is used to identify an original source, should be the same for all incoming chunks. It can change over time, when switching wav-files for example in the wav-reader.  
            if identifier is None:
                identifier=chunk.identifier
            else:
                if not identifier==chunk.identifier:
                    raise ValueError('Received incompatible chunk identifiers: {0} {1}'.format(identifier,chunk.identifier))
            
        return dataGenerationTime,metadata,identifier
        
    def alignIncomingChunks(self,index, 
                                continuity, 
                                chunkcontinuity, 
                                starttime, 
                                dataGenerationTime,
                                metadata, 
                                identifier,
                                initialSampleTime):
                                    
        current_composite       = self.compositeChunkList[index]
        previous_composite      = self.lastcompleted
        to_processor_composite  = compositeChunk(current_composite.number, 
                                                        self.requiredKeys, 
                                                        starttime, 
                                                        dataGenerationTime, 
                                                        metadata, 
                                                        identifier,
                                                        initialSampleTime)
        
        
        
        
        '''
        self.processor.logger.error("previous_composite {0}, continuity {1}".format(previous_composite , Continuity.getstring(Continuity,continuity))) 
        self.processor.logger.error("Required keys {0}".format(self.requiredKeys))
        for key, current_chunk in current_composite.received.viewitems():
            self.processor.logger.error("Keys in arriving chunk {0}".format(key))
            self.processor.logger.error("Shapes in arriving chunk {0}".format(np.shape(current_chunk.data)))
            self.processor.logger.error("                Alignable {0}".format(current_chunk.alignment.isAlignable()))
        '''
        
        for key, current_chunk in current_composite.received.viewitems():
            
            if current_chunk.alignment.isAlignable():
                if current_chunk.alignment.isEventLike():
                    #self.processor.logger.info("Eventlike chunk with key: {}".format(key))
                    to_processor_composite.update(key,current_chunk)
                else:
                    current_data=current_chunk.data
                    current_data_shape=np.shape(current_data)
                    dimension=len(current_data_shape)
                    current_data_length=current_data_shape[-1]

                    lowindices_drop = self.alignment_in.droppedAfterDiscontinuity-current_chunk.alignment.droppedAfterDiscontinuity 
                    highindices_drop= self.alignment_in.includedPast-current_chunk.alignment.includedPast
                    chunkdiscontinuity_lowindicesdrop=self.alignment_in.droppedAfterDiscontinuity+current_chunk.alignment.includedPast
                    
                    
                    self.processor.logger.info("Keys in arriving chunk {0}".format(key))
                    self.processor.logger.info("          lowindices_drop {0}".format(lowindices_drop))
                    self.processor.logger.info("          highindices_drop {0}".format(highindices_drop))
                    self.processor.logger.info("          chunkdiscontinuity_lowindicesdrop {0}".format(chunkdiscontinuity_lowindicesdrop))
                    self.processor.logger.info("          dimension {0}".format(dimension))
                    
                    
                    if dimension == 1:
                        if continuity >= Continuity.withprevious:                   # Regular Continuous Case
                            previous_data=previous_composite.received[key].data
                            previous_data_shape=np.shape(previous_data)
                            previous_data_length=previous_data_shape[-1]
                            
                            newdata=np.concatenate((previous_data[previous_data_length-highindices_drop:],current_data[:current_data_length-highindices_drop]))
                        elif current_chunk.continuity >= Continuity.withprevious:   # Irregular Discontinuous Case
                            newdata=current_data[chunkdiscontinuity_lowindicesdrop:current_data_length-highindices_drop]  # shave off the part  not present had this chunk been discontinuous and the part shaved of if it had been discontinuous.
                        else:                                                       # Regular Discontinuous Case
                            newdata=current_data[lowindices_drop:current_data_length-highindices_drop]
                    elif dimension == 2:
                        if continuity >= Continuity.withprevious:                   # Regular Continuous Case
                            previous_data=previous_composite.received[key].data
                            previous_data_shape=np.shape(previous_data)
                            previous_data_length=previous_data_shape[-1]
                            newdata=np.concatenate((previous_data[:,previous_data_length-highindices_drop:],current_data[:,:current_data_length-highindices_drop]), axis=1)
                        elif current_chunk.continuity >= Continuity.withprevious:   # Irregular Discontinuous Case
                            newdata=current_data[:,chunkdiscontinuity_lowindicesdrop:current_data_length-highindices_drop]  # shave off the part  not present had this stream been discontinuous and the part shaved of it it had been discontinuous.
                        else:                                                       # Regular Discontinuous Case
                            newdata=current_data[:,lowindices_drop:current_data_length-highindices_drop]
                    else:
                        raise ValueError('compositeManager does not support numpy arrays of dimensions higher than 2')
                    
                    newChunk=DataChunk( newdata, 
                                        starttime, 
                                        current_chunk.fs, 
                                        current_chunk.processorname, 
                                        self.sources, 
                                        continuity, 
                                        current_chunk.number, 
                                        alignment=self.alignment_in,
                                        #dataGenerationTime=current_chunk.dataGenerationTime,
                                        #metadata=current_chunk.metadata, 
                                        #identifier=current_chunk.identifier,                                     
                                        dataGenerationTime=dataGenerationTime,
                                        metadata=metadata, 
                                        identifier=identifier,
                                        initialSampleTime=initialSampleTime,
                                       )
                    
                    to_processor_composite.update(key,newChunk)
                
                
        # Needed for passing testing, but largely obsolete for our current purposes.
        to_processor_composite.continuity=continuity
        to_processor_composite.alignment=self.alignment_in
        to_processor_composite.chunkcontinuity=chunkcontinuity
            
        if to_processor_composite.status == compositeChunk.incomplete:
            raise RuntimeError('compositeChunk misses required keys')
            pass
       
        if not current_chunk.alignment.isEventLike():
            timeintervallengths=[np.shape(to_processor_composite.received[key].data)[-1]  for key in to_processor_composite.received]
            
            if not len(set(timeintervallengths)) == 1:
                #raise RuntimeError('Chunks passed to processor should be of the same length')
                pass


        return to_processor_composite
        
        

    def calculateInitialSampleTime(self,index,continuity, chunkcontinuity,starttime):
        '''
        calculateInitialSampleTime(self,index,continuity, chunkcontinuity,starttime):
        
        Return the time of the first sample in the aligned data of the incoming chunks
        '''
        
        InitialSampleTime=starttime
        
        #self.processor.logger.error('========== type of fsampling: {0} and value {1}'.format(type(self.alignment_in.fsampling),self.alignment_in.fsampling))
        #self.processor.logger.error('========== type of self.alignment_in: {0} and value {1}'.format(type(self.alignment_in ),self.alignment_in ))
        #self.processor.logger.error('========== type of self.processor.processorAlignments: {0} and value {1}'.format(type(self.processor.processorAlignments),self.processor.processorAlignments ))
        
        fsampling=float(self.alignment_in.fsampling) # cast to float to force non integer division in the following
        
        if continuity >= Continuity.withprevious:                           # Regular Continuous Case
            InitialSampleTime-=self.alignment_in.includedPast/fsampling
        elif chunkcontinuity >= Continuity.withprevious:           # Irregular Discontinuous Case
            InitialSampleTime+=self.alignment_in.droppedAfterDiscontinuity/fsampling
        else:                                                               # Regular Discontinuous Case
            InitialSampleTime+=self.alignment_in.droppedAfterDiscontinuity/fsampling
            
        return InitialSampleTime
        
        
        
        
    


