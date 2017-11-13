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

    
Author:     Ronald A.J. van Elburg, RonaldAJ@vanElburg.eu


How to use streamboard_testing_tools:

Streamboard testing tools is written to test the merging of chunks in 
the streamboard context.

To allow for this the Board class has been subclassed yielding the 
TestBoard class. This class can store several ChunkEmitter processor 
instances onBoard, and these processors are therefore not in a separate 
process. The TestBoard is receiving subscriptions on behalf of these 
processors and mimicks the activity  of normal processors by publishing 
ScenarioLines. 

At the same time, because it has been derived from 
Board class, the TestBoard can launch regular processors and the special 
CompositeTester processor. The CompositeTester processor can be 
preloaded with a Scenario, and then when running it can test whether 
the chunks it should receive according to the ScenarioLines in the 
Scenario are actually arriving. If it finds deviation from the scenario 
it will raise an Exception describing the kind of deviation.

Note: The Scenario.play method makes use of the internal structure of a 
processor to make it publish a single chunk from the scenario. To get 
this to work some of the internals of the processor had to be exposed 
to the Scenario class. Important changes in these internals can 
therefore break these tests even when functionality and underlying 
conceptual model remain unchanged. 
    
'''

from nose import with_setup

import numpy as np
import os.path as path
import multiprocessing, logging
import os,sys
import shutil
import h5py 
import time

from libsoundannotator.streamboard                import processor
from libsoundannotator.streamboard.continuity     import Continuity, chunkAlignment, processorAlignment
from libsoundannotator.streamboard.compositor     import DataChunk
from libsoundannotator.streamboard.board          import Board
from libsoundannotator.streamboard.subscription   import SubscriptionOrder
from libsoundannotator.streamboard.messages       import BoardMessage



class ScenarioLine(DataChunk):
    '''
    A Scenarioline instance contains the data for the construction of a 
    single chunk. This includes the content of a DataChunk from which 
    it is therefore derived, furthermore it contains a   
    processorinstance object and the name of the feature in the chunk. 
    '''
     
    def __init__(self,
                processorinstance,featurename, inout, data, startTime, fs, 
                processorName, sources, continuity=Continuity.withprevious, 
                number=0, alignment=None, 
                dataGenerationTime=dict(), 
                identifier=None, 
                chunkcontinuity=None, 
                metadata=dict(),**kwargs):
        
        self.processorinstance=processorinstance
        self.featurename=featurename
        self.inout=inout
              
        
        if inout =='out':
            self.chunkcontinuity=chunkcontinuity
            
        if alignment is None:
            if inout =='in':
                alignment = chunkAlignment(fsampling=fs)
            elif  inout =='out':
                alignment = processorAlignment(fsampling=fs)
            
            
        super(ScenarioLine, self).__init__(data, startTime, fs, 
                            processorName, sources, continuity, 
                            number=number, 
                            alignment=alignment, 
                            dataGenerationTime=dataGenerationTime, 
                            identifier=identifier, 
                            metadata=metadata,
                            **kwargs)
        
      
        

class Scenario(object):
    '''
    A Scenario instance is both a collection of scenario lines and the 
    class providing tools for executing the scenario lines. Using the 
    append method a preconstructed Scenarioline instances are added to a 
    Scenario. Alternatively ScennarioLine can be constucted directly in the Scennario by calling appendScenarioLine
    '''
    
    
    typeerrormessage='TypeError: It is only allowed to append ScenarioLines to a Scenario.' 
     
    def __init__(self, logger):
        self.scenariolist=list()
        self.logger=logger

    def append(self,event):
        '''
        append: append a preconstructed Scenarioline instance to a 
        Scenario.
        '''
           
        if type(event) == ScenarioLine:
            self.scenariolist.append
        else:
            raise TypeError(self.typeerrormessage)


    def appendScenarioLine(self,*args, **kwargs):
        ''' 
        appendScenarioLine: construct a ScenarioLine from the 
        arguments given and append it. 
        ''' 
        
        scenarioline=ScenarioLine(*args, **kwargs) 
        self.scenariolist.append(scenarioline)
    
    def publish(self,scenarioline,testboard, delta_t):
        '''
        
        '''
        stored_subscriptions=scenarioline.processorinstance.subscriptions
        
        # Temporarily replace subscription list with one only including features from the current scenario
        scenarioline.processorinstance.subscriptions=dict()
        for subscriptionorder, subscriber in stored_subscriptions.viewitems():
            if subscriber.senderKey == scenarioline.featurename:
                scenarioline.processorinstance.subscriptions[subscriptionorder]=subscriber
                self.logger.info('subscription copied: {0}'.format(subscriptionorder))
        '''
            Set the properties of the chunk to be published through the processor involved.
        '''
    
        # Chunk variables we need to set explicitly on the processor
        scenarioline.processorinstance.currentTimeStamp=scenarioline.startTime      # returned by getTimeStamp(subscriber.senderKey)
        scenarioline.processorinstance.config['SampleRate']=scenarioline.fs         # returned by getsamplerate(subscriber.senderKey)

        scenarioline.processorinstance.debugcontinuity = scenarioline.continuity  # returned by getcontinuity() from the Processor class (not from the InputProcessor class)
        
        
        scenarioline.processorinstance.oldchunk.number=scenarioline.number-1             # returned by  getchunknumber() with an increment by 1
        
        
        # Chunk variables implicitly defined through the processor
        #   scenarioline.sources         # set via subscriptions when starting the processor
        #   scenarioline.alignment       # getAlignment creates a default chunkAlignment with all alignment parameters set to zero
        
        scenarioline.processorinstance.processorAlignments[scenarioline.featurename]=scenarioline.alignment 
        
        # Chunk variables set by providing them as argument to the publish method
        #   ... required positional argument 
        #       scenarioline.dataGenerationTime                        # argument to the publish method
        data=dict()
        data[scenarioline.featurename]=scenarioline.data
        
        #   ... keyword arguments  (copied by smartChunks from incoming chunks)              
        #   scenarioline.identifier                                 # argument to the publish method, if None publish 
                                                                    # method will set this to the current processor class
        #   scenarioline.metadata                                   # argument to the publish method
        
        if type(scenarioline.dataGenerationTime)==dict:
            _dataGenerationTime=scenarioline.dataGenerationTime
        else:
            _dataGenerationTime={scenarioline.processorinstance.name:scenarioline.dataGenerationTime}
            
        scenarioline.processorinstance.publish( data, scenarioline.continuity,
                                                scenarioline.startTime,
                                                scenarioline.number,
                                                _dataGenerationTime,
                                                metadata=scenarioline.metadata, 
                                                identifier=scenarioline.identifier)
                                                
    
        # Keep an eye on the processors in which we might induce an error.
        testboard.recv_from_processor(delta_t)

        scenarioline.processorinstance.subscriptions=stored_subscriptions
    
    def setExpectedComposite(self, scenarioline, **kwargs):
        pass

    def play(self,  testboard, delta_t=0.02,**kwargs):
        
        
        
        self.logger.info('Entering Scenario Play' )
                
        for scenarioline in  self.scenariolist:
            self.logger.info('Process scenarioline: {0}'.format(scenarioline.featurename))
            if scenarioline.inout == 'out':
                self.publish(scenarioline,testboard, delta_t, **kwargs)
            
        testboard.recv_from_processor(10*delta_t)
            
class ChunkEmitter(processor.Processor):
    
    def __init__(self, boardConn, name, onBoard=False, **kwargs):
        super(ChunkEmitter,self).__init__(boardConn, name, **kwargs)
        
        self.requiredParametersWithDefault(requiredKeys=[], processoralignment=dict())
        self.requiredKeys=self.config['requiredKeys']
        
        self.processorAlignments=self.config['processoralignment']   
        
        if onBoard:
            self.prepare_processor()
            
             
        self.debugcontinuity=Continuity.withPrevious
    
    def prerun(self):
        super(ChunkEmitter, self).prerun()
                
        alignments_out=dict()
            
        for key in self.processorAlignments:
            self.logger.info('processorAlignments type: {0} value: {1}'.format(type(self.processorAlignments[key]),self.processorAlignments[key]))
       
            alignments_out[key]=self.processorAlignments[key].copy()
            
        self.compositeManager.alignments_out=alignments_out
 
        
        
    def prepare_processor(self):
        self.prerun()
             
        
    def getcontinuity(self):
        return self.debugcontinuity
    
    def getTimeStamp(self,key):
        self.currentTimeStamp

class CompositeTester(processor.Processor):
    
    def __init__(self, boardConn, name, onBoard=False, **kwargs):
        super(CompositeTester,self).__init__(boardConn, name, **kwargs)
        
        self.requiredParameters('scenario')
        
        self.requiredParametersWithDefault(requiredKeys=[], processoralignment=dict())
        self.requiredKeys=self.config['requiredKeys']
        self.processorAlignments=self.config['processoralignment']
        
        
       
        
            
        self.scenario=self.config['scenario'] # For a receiving CompositeTester to store the expected compositeChunks 




    def prerun(self):
        super(CompositeTester, self).prerun()
        
        alignments_out=dict()
            
        for key in self.processorAlignments:
            alignments_out[key]=self.processorAlignments[key].copy()
            
        self.compositeManager.alignments_out=alignments_out
 
         
    
    '''
        compositeChunk fields presently used somewhere in libsoundannotator
        XProcessor.processData(self,compositeChunk) 
        compositeChunk:
            ... available in DataChunk
            compositeChunk.continuity
            compositeChunk.received       as DataChunk.data, also in smartChunk this is a dict not a single numpy array
            compositeChunk.alignment
            compositeChunk.startTime
            compositeChunk.chunkMetaData    as DataChunk.metadata
            compositeChunk.identifier
            
            ... compositeChunk extension in scenarioline
            compositeChunk.chunkcontinuity
        '''    
        
        
        
        
        
        
    def processData(self,compositeChunk):
        
        self.logger.info('Processing compositeChunk class of data field: {0} '.format(type(compositeChunk.received)))
        if compositeChunk is None:
            return
        
        scenarioline= self.scenario.scenariolist[0]
        
        
        if not set(compositeChunk.received.keys()) == set(scenarioline.data.keys()):
            raise ValueError('compositeChunk contains different keys than expected,\n \n compositeChunk: {0} \n expected: {1}'.format(compositeChunk.received.keys(),scenarioline.data.keys()))
            
         
        if not compositeChunk.continuity == scenarioline.continuity:
            
            raisestring='compositeChunk has incorrect continuity flag,\n'
            raisestring+=' compositeChunk number: {0} has continuity {1}\n'.format(compositeChunk.number,Continuity.getstring(Continuity,compositeChunk.continuity))
            raisestring+='  expected chunk number {0} with continuity: {1}'.format(scenarioline.number,Continuity.getstring(Continuity,scenarioline.continuity))
            raise ValueError(raisestring)
         
        if not compositeChunk.number == scenarioline.number:
            raise ValueError('compositeChunk has incorrect number,\n compositeChunk: {0} \n expected: {1}'.format(compositeChunk.number, scenarioline.number))
                
               
        if not compositeChunk.alignment == scenarioline.alignment:
            raise ValueError('compositeChunk has incorrect ChunkAlignment,\n compositeChunk: {0} \n expected: {1}'.format(compositeChunk.alignment, scenarioline.alignment))
            
        multiply=None
        for key in compositeChunk.received.keys():
            if type(scenarioline.data[key]) == np.ndarray:
                try:
                    np.testing.assert_equal(compositeChunk.received[key].data,scenarioline.data[key])
                except Exception as e:
                    raise type(e)('{0} for key {1} and number {2}'.format(e.message, key,compositeChunk.number ))
            elif not scenarioline.data[key] == compositeChunk.received[key].data:
                raise ValueError('compositeChunk contains different values for {0} than expected,\n \n compositeChunk: {1} \n expected: {2}'.format(key,compositeChunk.received[key].data,scenarioline.data[key]))
            
            '''
            if not type(scenarioline.dataGenerationTime)== dict:
                raise TypeError('scenarioline.dataGenerationTime is of the wrong type should be a dict. \n key: {0} ,number: {1}'.format(key,scenarioline.number))
                
            if not compositeChunk.received[key].dataGenerationTime == scenarioline.dataGenerationTime:
                raise ValueError('compositeChunk has incorrect  dataGenerationTime,\n compositeChunk: {0} \n expected: {1}'.format(compositeChunk.received[key].dataGenerationTime, scenarioline.dataGenerationTime))
            '''
            
            if type(scenarioline.data[key]) == np.ndarray:
                if multiply is None:
                    multiply=compositeChunk.received[key].data
                else:
                    multiply*=compositeChunk.received[key].data
                    
                    
        if not set(self.compositeManager.sources) == set(scenarioline.sources):
            raise ValueError('compositeManager contains different sources than expected,\n \n compositeChunk: {0} \n expected: {1}'.format(self.compositeManager.sources,scenarioline.sources))
            
        '''
        if not self.compositeManager.compositeChunkList[indexfordebugger].identifier == scenarioline.identifier:
            raise ValueError('compositeChunk has incorrect identifier,\n compositeChunk: |{0}| \n expected: |{1}|'.format(self.compositeManager.compositeChunkList[indexfordebugger].identifier, scenarioline.identifier))
        '''   
      
            
        del self.scenario.scenariolist[0]
        return {'ExT':multiply}
        


from libsoundannotator.streamboard.messages import ProcessorMessage

from _multiprocessing import Connection
'''
    TestBoard is a tool used for reproducing the STS49 error while 
    letting the test suite finish. The implementation is dubious at 
    best so use at your own peril.
'''
class TestBoard(Board):
    
    # Here you can watch a single processor, while the board is otherwise inactive. 
    def recv_from_processor(self,timeout):
        t=time.time()
        
        while time.time()-t < timeout:
            
            for processorName, item in  self.processors.viewitems():
                (instance,fromBoard)=item
                
                if type(fromBoard )==Connection:
                    hasNew = fromBoard.poll(self._BoardConnectionTimeOut)
                    
                    if hasNew:
                        message=fromBoard.recv()

                        if message.getType() == ProcessorMessage.error:
                            
                            contents=message.getContents()
                            
                            (exception_class_name, exception_message, processorname)= contents
                            exceptionstring='Processor {0} raised a {1}: {2}'.format(processorname,exception_class_name, exception_message)
                            self.logger.error(exceptionstring)  
                            
                            raise Exception(exceptionstring)
                   
 
    def createOnBoardTestProcessor(self, processorName, processorClass, *subscriptionorders, **kwargs):
        if processorName in self.processors:
            self.logger.error(
            'Trying to start processor with duplicate name {0}. Processors must have unique names.'
            .format(processorName))
            return

        requiredKeys = [o.receiverKey for o in subscriptionorders]
            
        kwargs['requiredKeys'] = requiredKeys

        self.logger.debug("creating instance of {0}".format(processorName))
        instance = processorClass(None, processorName, logdir=self.logdir, loglevel=self.loglevel, **kwargs)

        self.processors[processorName] = (instance,instance)

        # Let processor check whether provided subscriptions fit the required keys, processor
        # will raise ValueErrors if not correct.
        subscriptionReceiverKeys=[subscriptionorder.receiverKey for subscriptionorder in subscriptionorders]
        instance.processBoardMessage(BoardMessage(BoardMessage.testrequiredkeys,subscriptionReceiverKeys))
       
        # After passing checks normally subscriptions would be created, but OnBoard TestProcessor don't subscribe
        # to other processors, they only receive subscriptions.  
        if len(requiredKeys) > 0:
            self.logger.info('requiredKeys for TestProcessor will not be used for building connections')

