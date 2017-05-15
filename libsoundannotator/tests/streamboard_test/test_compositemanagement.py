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
'''
    
    Author:     Ronald A.J. van Elburg, RonaldAJ@vanElburg.eu
    Copyright:  SoundAppraisal B.V.

    With this test we try to test composite management. Its first development preceded refactoring from smartChunks to the compositeManager/compositeChunks. To allow this test to run in both situations we don't access smartChunk functionality directly but only through interprocessor communication.  At present (August 2016, git-sha: 4df4c81e git-msg begin: STS-49: Design files for refactoring smartChunks.) there are no plans to change this interprocessor communication. 

    The Scenario.play method makes use of the internal structure of a processor to make it publish a single chunk from the scenario. So I had to expose some of the internals of the processor to gets this to work. Important changes in these internals can therefore break these tests even when functionality and underlying conceptual model remain unchanged. A possible solution to this at present hypothetical problem is to keep the CompositeTester based on the old version while constructing new version of the tested processors. This still requires that the new processors would be compatible with the board.
    
'''

from nose import with_setup
from streamboard_testing_tools import TestBoard, Scenario, ChunkEmitter, CompositeTester
from libsoundannotator.streamboard.continuity     import Continuity, chunkAlignment, processorAlignment
import logging, time, sys
import numpy as np

from libsoundannotator.streamboard.subscription       import SubscriptionOrder

# First test the test code
      
def test_scenarioappend():
    
    scenario=Scenario(None)
    try:
        scenario.append(None)
        raise RuntimeError('Appending a non ScenarioLine object to a Scenario should raise a TypeError')
    except TypeError as e:
        if Scenario.typeerrormessage ==str(e):
            pass
        else:
            raise

def test_appendScenarioLine0():
    
    scenario=Scenario(None)
    try:
        scenario.appendScenarioLine('sdfasfd')
        raise RuntimeError('appendScenarioLine with incorrect argument should raise a TypeError')
    except TypeError as e:
        if str(e) =='__init__() takes at least 9 arguments (2 given)':
            pass
        else:
            raise


            
            
            
def my_setup_function():
    global testboard, logger 
    '''
        The TestBoard class is a tool used for reproducing the STS49 error while letting the test suite finish. The implementation is dubious at best so reuse at your own peril.
    '''
    testboard = TestBoard(loglevel=logging.INFO, logdir='.', logfile='TestBoard') # Setting loglevel is needed under windows
    logger=testboard.logger
    
def my_teardown_function():
    global testboard, logger 
    logger = None
    testboard.stopallprocessors()
    time.sleep(.5)
    testboard = None        

@with_setup(my_setup_function,my_teardown_function)  
def test_reproduction_sts49():
    global testboard, logger     
    
    inputscenario=Scenario(logger)
    processor_name='AB_Test'
    requiredKeys=['preA','preB']
    logdir='.'
    subscriptionsorders=[
    SubscriptionOrder('virtualpre','AB_Test', 'A','preA'),
    SubscriptionOrder('virtualpre','AB_Test', 'B','preB'),
    ]
    
    testboard.createOnBoardTestProcessor(processor_name, ChunkEmitter, *subscriptionsorders, onBoard=True)
    scenario_processor=testboard.processors[processor_name][0]
    scenario_processor.sources=set(['microphone',])
    
    tested_processor_name='TestedC'
    subscriptionsorders=[
    SubscriptionOrder(processor_name,tested_processor_name, 'A','A'),
    SubscriptionOrder(processor_name,tested_processor_name, 'B','B'),
    ]
   
    
    time.sleep(0.05)
    
    inputscenario.appendScenarioLine(scenario_processor, 'A','out',
                            np.ones((2000,100)),        #data, 
                            1449478633.333646,          #startTime, 
                            41000,                      #fs, 
                            processor_name,             #processorName, 
                            scenario_processor.sources,       #sources, 
                            Continuity.discontinuous  ,    #continuity, 
                            number=0,  #optional: number=0, 
                            #optional: alignment=processorAlignment(), 
                            #optional: dataGenerationTime={processorname:time}, 
                            identifier='/my/pathname/myfile.wav', #optional: identifier=None
                            )
                            
    inputscenario.appendScenarioLine(scenario_processor, 'B','out',
                            np.ones((2000,100)),        #data, 
                            1449478633.333646,          #startTime, 
                            41000,                      #fs, 
                            processor_name,             #processorName, 
                            scenario_processor.sources,       #sources, 
                            Continuity.discontinuous ,    #continuity, 
                            number=0,  #optional: number=0, 
                            #optional: alignment=processorAlignment(), 
                            #optional: dataGenerationTime={processorname:time}, 
                            identifier='/my/pathname/myfile.wav', #optional: identifier=None
                            )
    
    
    inputscenario.appendScenarioLine(scenario_processor, 'A','out',
                            np.ones((2000,100)),        #data, 
                            1449478633.333646,          #startTime, 
                            41000,                      #fs, 
                            processor_name,             #processorName, 
                            scenario_processor.sources,        #sources, 
                            Continuity.withprevious  ,    #continuity, 
                            number =sys.getrecursionlimit()+1,              #optional: number=0, 
                            #optional: alignment=processorAlignment(), 
                            #optional: dataGenerationTime={processorname:time}, 
                            identifier='/my/pathname/myfile.wav', #optional: identifier=None
                            )
                            
    inputscenario.appendScenarioLine(scenario_processor, 'B','out',
                            np.ones((2000,100)),        #data, 
                            1449478633.333646,          #startTime, 
                            41000,                      #fs, 
                            processor_name,             #processorName, 
                            scenario_processor.sources,        #sources, 
                            Continuity.withprevious  ,    #continuity, 
                            number =sys.getrecursionlimit()+1,              #optional: number=0, 
                            #optional: alignment=processorAlignment(), 
                            #optional: dataGenerationTime={processorname:time}, 
                            identifier='/my/pathname/myfile.wav',#optional: identifier=None
                            )
    
                            
                            
    outputscenario_C = Scenario(logger)
    outputscenario_C.appendScenarioLine(None, 'C','in',
                            {'A':np.ones((2000,100)),'B':np.ones((2000,100))},        #data, 
                            1449478633.333646,          #startTime, 
                            41000,                      #fs, 
                            processor_name,             #processorName, 
                            set([tested_processor_name,'microphone',]),        #sources, 
                            Continuity.discontinuous ,      #continuity, 
                            number=0,                       #optional: number=0, 
                            alignment=chunkAlignment(),#optional: alignment=chunkAlignment(), 
                            #optional: dataGenerationTime=dict(), 
                            identifier='/my/pathname/myfile.wav', #optional: identifier=None
                            )
                            
    outputscenario_C.appendScenarioLine(None, 'C','in',
                            {'A':np.ones((2000,100)),'B':np.ones((2000,100))},        #data, 
                            1449478633.333646,          #startTime, 
                            41000,                      #fs, 
                            processor_name,             #processorName, 
                            set([tested_processor_name,'microphone',]),                    #sources, 
                            Continuity.discontinuous,     #continuity, 
                            number=sys.getrecursionlimit()+1,  #optional: number=0, 
                            #optional: alignment=chunkAlignment(), 
                            #optional: dataGenerationTime={processorname:time}, 
                            identifier='/my/pathname/myfile.wav', #optional: identifier=None
                            )
                            
    testboard.startProcessor(tested_processor_name, CompositeTester,
                            *subscriptionsorders, 
                            scenario=outputscenario_C )
    
    test_processor_C=testboard.processors[tested_processor_name][0]                         
    test_processor_C.sources=set(['microphone',])
    
    
    time.sleep(0.2)
                                                
    inputscenario.play(testboard, 0.2)                     
                

@with_setup(my_setup_function,my_teardown_function)  
def test_calibrationflow():
    global testboard, logger     
    
    inputscenario=Scenario(logger)
    processor_name='AB_Test'
    requiredKeys=['preA','preB']
    logdir='.'
    subscriptionsorders=[
    SubscriptionOrder('virtualpre','AB_Test', 'A','preA'),
    SubscriptionOrder('virtualpre','AB_Test', 'B','preB'),
    ]
    
    testboard.createOnBoardTestProcessor(processor_name, ChunkEmitter, *subscriptionsorders, onBoard=True)
    scenario_processor=testboard.processors[processor_name][0]
    scenario_processor.sources=set(['microphone',])
    
    tested_processor_name='TestedC'
    subscriptionsorders=[
    SubscriptionOrder(processor_name,tested_processor_name, 'A','A'),
    SubscriptionOrder(processor_name,tested_processor_name, 'B','B'),
    ]
   
    
    time.sleep(0.05)
    
    inputscenario.appendScenarioLine(scenario_processor, 'A','out',
                            np.ones((2000,100)),        #data, 
                            1449478633.333646,          #startTime, 
                            41000,                      #fs, 
                            processor_name,             #processorName, 
                            scenario_processor.sources,       #sources, 
                            Continuity.calibrationChunk ,    #continuity, 
                            number=1,  #optional: number=0, 
                            #optional: alignment=processorAlignment(), 
                            #optional: dataGenerationTime={processorname:time}, 
                            identifier='/my/pathname/myfile.wav', #optional: identifier=None
                            )
                            
    inputscenario.appendScenarioLine(scenario_processor, 'B','out',
                            np.ones((2000,100)),        #data, 
                            1449478633.333646,          #startTime, 
                            41000,                      #fs, 
                            processor_name,             #processorName, 
                            scenario_processor.sources,       #sources, 
                            Continuity.calibrationChunk ,    #continuity, 
                            number=1,  #optional: number=0, 
                            #optional: alignment=processorAlignment(), 
                            #optional: dataGenerationTime={processorname:time}, 
                            identifier='/my/pathname/myfile.wav', #optional: identifier=None
                            )
                            
                            
    outputscenario_C = Scenario(logger)
    outputscenario_C.appendScenarioLine(None, 'C','in',
                            {'A':np.ones((2000,100)),'B':np.ones((2000,100))},        #data, 
                            1449478633.333646,          #startTime, 
                            41000,                      #fs, 
                            processor_name,             #processorName, 
                            set([tested_processor_name,'microphone',]),        #sources, 
                            Continuity.calibrationChunk ,      #continuity, 
                            number=1,                       #optional: number=0, 
                            alignment=chunkAlignment(), #optional: alignment=chunkAlignment(), 
                            #optional: dataGenerationTime={processorname:time}, 
                            identifier='/my/pathname/myfile.wav', #optional: identifier=None
  )
                            
    testboard.startProcessor(tested_processor_name, CompositeTester,
                            *subscriptionsorders, 
                            scenario=outputscenario_C )
    
    test_processor_C=testboard.processors[tested_processor_name][0]                         
    test_processor_C.sources=set(['microphone',])
    
    
    time.sleep(0.2)
                                                
    inputscenario.play(testboard, 0.2)                     
                   

@with_setup(my_setup_function,my_teardown_function)  
def test_fileprocessingflow():
    global testboard, logger     
    
    inputscenario=Scenario(logger)
    processor_name='AB_Test'
    requiredKeys=['preA','preB']
    logdir='.'
    subscriptionsorders=[
    SubscriptionOrder('virtualpre','AB_Test', 'A','preA'),
    SubscriptionOrder('virtualpre','AB_Test', 'B','preB'),
    ]
    
    testboard.createOnBoardTestProcessor(processor_name, ChunkEmitter, *subscriptionsorders, onBoard=True)
    scenario_processor=testboard.processors[processor_name][0]
    scenario_processor.sources=set(['microphone',])
    
    tested_processor_name='TestedC'
    subscriptionsorders=[
    SubscriptionOrder(processor_name,tested_processor_name, 'A','A'),
    SubscriptionOrder(processor_name,tested_processor_name, 'B','B'),
    ]
   
    
    time.sleep(0.05)
    
    
    fs=41000
    chunkwidth=2000
    delta_t=float(chunkwidth)/fs
    outputscenario_C = Scenario(logger)
    
    for tsteps, number, continuity in [ (0,0,Continuity.newfile),
                                        (1,1,Continuity.withprevious),
                                        (2,2,Continuity.withprevious),
                                        (3,3,Continuity.withprevious),
                                        (4,4,Continuity.last)]:
                                            
        inputscenario.appendScenarioLine(scenario_processor, 'A','out',
                                np.ones((100,2000)),        #data, 
                                1449478633.333646+tsteps*delta_t,          #startTime, 
                                fs,                      #fs, 
                                processor_name,             #processorName, 
                                scenario_processor.sources,       #sources, 
                                continuity ,    #continuity, 
                                number=number,  #optional: number=0, 
                                #optional: alignment=processorAlignment(), 
                                #optional: dataGenerationTime={processorname:time}, 
                                identifier='/my/pathname/myfile.wav', #optional: identifier=None
                                )
                                
        inputscenario.appendScenarioLine(scenario_processor, 'B','out',
                                np.ones((100,2000)),        #data, 
                                1449478633.333646+tsteps*delta_t,          #startTime, 
                                fs,                      #fs, 
                                processor_name,             #processorName, 
                                scenario_processor.sources,       #sources, 
                                continuity ,    #continuity, 
                                number=number,  #optional: number=0, 
                                #optional: alignment=processorAlignment(), 
                                #optional: dataGenerationTime={processorname:time}, 
                                identifier='/my/pathname/myfile.wav', #optional: identifier=None
                                )
                                
                                

        outputscenario_C.appendScenarioLine(None, 'C','in',
                                {'A':np.ones((100,2000)),'B':np.ones((100,2000))},        #data, 
                                1449478633.333646+tsteps*delta_t,          #startTime, 
                                fs,                      #fs, 
                                processor_name,             #processorName, 
                                set([tested_processor_name,'microphone',]),      #sources, 
                                continuity ,    #continuity, 
                                number=number,  #optional: number=0, 
                                alignment=chunkAlignment(),#optional: alignment=chunkAlignment(), 
                                #optional: dataGenerationTime={processorname:time}, 
                                identifier='/my/pathname/myfile.wav', #optional: identifier=None
                                )
                                
                            
    testboard.startProcessor(tested_processor_name, CompositeTester,
                            *subscriptionsorders, 
                            scenario=outputscenario_C )
    
    test_processor_C=testboard.processors[tested_processor_name][0]                         
    test_processor_C.sources=set(['microphone',])
    
    
    time.sleep(0.2)
                                                
    inputscenario.play(testboard, 0.2)                     




@with_setup(my_setup_function,my_teardown_function)  
def test_online_processingflow():
    global testboard, logger     
    
    inputscenario=Scenario(logger)
    processor_name='AB_Test'
    requiredKeys=['preA','preB']
    logdir='.'
    subscriptionsorders=[
    SubscriptionOrder('virtualpre','AB_Test', 'A','preA'),
    SubscriptionOrder('virtualpre','AB_Test', 'B','preB'),
    ]
    
    testboard.createOnBoardTestProcessor(processor_name, ChunkEmitter, *subscriptionsorders, onBoard=True)
    scenario_processor=testboard.processors[processor_name][0]
    scenario_processor.sources=set(['microphone',])
    
    tested_processor_name='TestedC'
    subscriptionsorders=[
    SubscriptionOrder(processor_name,tested_processor_name, 'A','A'),
    SubscriptionOrder(processor_name,tested_processor_name, 'B','B'),
    ]
   
    
    time.sleep(0.05)
    
    
    fs=41000
    chunkwidth=2000
    delta_t=float(chunkwidth)/fs
    outputscenario_C = Scenario(logger)
    
    for tsteps, number, continuity in [ (0,0,Continuity.discontinuous),
                                        (1,1,Continuity.withprevious),
                                        (2,2,Continuity.withprevious),
                                        (3,3,Continuity.withprevious),
                                        (4,4,Continuity.withprevious),
                                        (5,5,Continuity.discontinuous),
                                        (6,6,Continuity.withprevious),
                                        (7,7,Continuity.withprevious),]:
                                            
        inputscenario.appendScenarioLine(scenario_processor, 'A','out',
                                np.ones((100,2000)),        #data, 
                                1449478633.333646+tsteps*delta_t,          #startTime, 
                                fs,                      #fs, 
                                processor_name,             #processorName, 
                                scenario_processor.sources,       #sources, 
                                continuity ,    #continuity, 
                                number=number,  #optional: number=0, 
                                #optional: alignment=processorAlignment(), 
                                #optional: dataGenerationTime={processorname:time}, 
                                identifier='/my/pathname/myfile.wav', #optional: identifier=None
                                )
                                
        inputscenario.appendScenarioLine(scenario_processor, 'B','out',
                                np.ones((100,2000)),        #data, 
                                1449478633.333646+tsteps*delta_t,          #startTime, 
                                fs,                      #fs, 
                                processor_name,             #processorName, 
                                scenario_processor.sources,       #sources, 
                                continuity ,    #continuity, 
                                number=number,  #optional: number=0, 
                                #optional: alignment=processorAlignment(), 
                                #optional: dataGenerationTime={processorname:time}, 
                                identifier='/my/pathname/myfile.wav', #optional: identifier=None
                                )
                                
        outputscenario_C.appendScenarioLine(None, 'C','in',
                                {'A':np.ones((100,2000)),'B':np.ones((100,2000))},        #data, 
                                1449478633.333646+tsteps*delta_t,          #startTime, 
                                fs,                      #fs, 
                                processor_name,             #processorName, 
                                set([tested_processor_name,'microphone',]),      #sources, 
                                continuity ,    #continuity, 
                                number=number,  #optional: number=0, 
                                alignment=chunkAlignment(),#optional: alignment=chunkAlignment(), 
                                #optional: dataGenerationTime={processorname:time}, 
                                identifier='/my/pathname/myfile.wav', #optional: identifier=None
                                )
                                
                            
    testboard.startProcessor(tested_processor_name, CompositeTester,
                            *subscriptionsorders, 
                            scenario=outputscenario_C )
    
    test_processor_C=testboard.processors[tested_processor_name][0]                         
    test_processor_C.sources=set(['microphone',])
    
    
    time.sleep(0.2)
                                                
    inputscenario.play(testboard, 0.2)                    


@with_setup(my_setup_function,my_teardown_function)  
def test_online_processingflow_withgap():
    global testboard, logger     
    
    inputscenario=Scenario(logger)
    processor_name='AB_Test'
    requiredKeys=['preA','preB']
    logdir='.'
    subscriptionsorders=[
    SubscriptionOrder('virtualpre','AB_Test', 'A','preA'),
    SubscriptionOrder('virtualpre','AB_Test', 'B','preB'),
    ]
    
    testboard.createOnBoardTestProcessor(processor_name, ChunkEmitter, *subscriptionsorders, onBoard=True)
    scenario_processor=testboard.processors[processor_name][0]
    scenario_processor.sources=set(['microphone',])
    
    tested_processor_name='TestedC'
    subscriptionsorders=[
    SubscriptionOrder(processor_name,tested_processor_name, 'A','A'),
    SubscriptionOrder(processor_name,tested_processor_name, 'B','B'),
    ]
   
    
    time.sleep(0.05)
    
    
    fs=41000
    chunkwidth=2000
    delta_t=float(chunkwidth)/fs
    outputscenario_C = Scenario(logger)
    
    for tsteps, number, continuity, continuity_out in [ (0,0,Continuity.discontinuous,Continuity.discontinuous ),
                                        (1,1,Continuity.withprevious,Continuity.withprevious),
                                        (2,2,Continuity.withprevious,Continuity.withprevious),
                                        (4,4,Continuity.withprevious,Continuity.discontinuous),
                                        (5,5,Continuity.withprevious,Continuity.withprevious),
                                        (6,6,Continuity.withprevious,Continuity.withprevious),]:
                                            
        inputscenario.appendScenarioLine(scenario_processor, 'A','out',
                                np.ones((100,2000)),        #data, 
                                1449478633.333646+tsteps*delta_t,          #startTime, 
                                fs,                      #fs, 
                                processor_name,             #processorName, 
                                scenario_processor.sources,       #sources, 
                                continuity ,    #continuity, 
                                number=number,  #optional: number=0, 
                                #optional: alignment=processorAlignment(), 
                                #optional: dataGenerationTime={processorname:time}, 
                                identifier='/my/pathname/myfile.wav', #optional: identifier=None
                                )
                                
        inputscenario.appendScenarioLine(scenario_processor, 'B','out',
                                np.ones((100,2000)),        #data, 
                                1449478633.333646+tsteps*delta_t,          #startTime, 
                                fs,                      #fs, 
                                processor_name,             #processorName, 
                                scenario_processor.sources,       #sources, 
                                continuity ,    #continuity, 
                                number=number,  #optional: number=0, 
                                #optional: alignment=processorAlignment(), 
                                #optional: dataGenerationTime={processorname:time}, 
                                identifier='/my/pathname/myfile.wav', #optional: identifier=None
                                )
                                
                                

        outputscenario_C.appendScenarioLine(None, 'C','in',
                                {'A':np.ones((100,2000)),'B':np.ones((100,2000))},        #data, 
                                1449478633.333646+tsteps*delta_t,          #startTime, 
                                fs,                      #fs, 
                                processor_name,             #processorName, 
                                set([tested_processor_name,'microphone',]),      #sources, 
                                continuity_out ,    #continuity, 
                                number=number,  #optional: number=0, 
                                alignment=chunkAlignment(),#optional: alignment=chunkAlignment(), 
                                #optional: dataGenerationTime={processorname:time}, 
                                identifier='/my/pathname/myfile.wav', #optional: identifier=None
                                )
                                
                        
    testboard.startProcessor(tested_processor_name, CompositeTester,
                            *subscriptionsorders, 
                            scenario=outputscenario_C )
    
    test_processor_C=testboard.processors[tested_processor_name][0]                         
    test_processor_C.sources=set(['microphone',])
    
    
    time.sleep(0.2)
                                                
    inputscenario.play(testboard, 0.2)                    


@with_setup(my_setup_function,my_teardown_function)  
def test_online_processingflow_illegalovertaking():
    global testboard, logger     
    
    inputscenario=Scenario(logger)
    processor_name='AB_Test'
    requiredKeys=['preA','preB']
    logdir='.'
    subscriptionsorders=[
    SubscriptionOrder('virtualpre','AB_Test', 'A','preA'),
    SubscriptionOrder('virtualpre','AB_Test', 'B','preB'),
    ]
    
    testboard.createOnBoardTestProcessor(processor_name, ChunkEmitter, *subscriptionsorders, onBoard=True)
    scenario_processor=testboard.processors[processor_name][0]
    scenario_processor.sources=set(['microphone',])
    
    tested_processor_name='TestedC'
    subscriptionsorders=[
    SubscriptionOrder(processor_name,tested_processor_name, 'A','A'),
    SubscriptionOrder(processor_name,tested_processor_name, 'B','B'),
    ]
   
    
    time.sleep(0.05)
    
    
    fs=41000
    chunkwidth=2000
    delta_t=float(chunkwidth)/fs
    outputscenario_C = Scenario(logger)
    
    for tsteps, number, continuity, continuity_out in [ (0,0,Continuity.discontinuous,Continuity.discontinuous ),
                                        (1,1,Continuity.withprevious,Continuity.withprevious),
                                        (2,2,Continuity.withprevious,Continuity.withprevious),
                                        (3,3,Continuity.withprevious,Continuity.withprevious),
                                        (4,4,Continuity.withprevious,Continuity.withprevious),
                                        (5,5,Continuity.withprevious,Continuity.withprevious),
                                        (6,6,Continuity.withprevious,Continuity.withprevious),]:
                                            
        inputscenario.appendScenarioLine(scenario_processor, 'A','out',
                                np.ones((100,2000)),        #data, 
                                1449478633.333646+tsteps*delta_t,          #startTime, 
                                fs,                      #fs, 
                                processor_name,             #processorName, 
                                scenario_processor.sources,       #sources, 
                                continuity ,    #continuity, 
                                number=number,  #optional: number=0, 
                                #optional: alignment=processorAlignment(), 
                                #optional: dataGenerationTime={processorname:time}, 
                                identifier='/my/pathname/myfile.wav', #optional: identifier=None
                                )
                                
        inputscenario.appendScenarioLine(scenario_processor, 'B','out',
                                np.ones((100,2000)),        #data, 
                                1449478633.333646+tsteps*delta_t,          #startTime, 
                                fs,                      #fs, 
                                processor_name,             #processorName, 
                                scenario_processor.sources,       #sources, 
                                continuity ,    #continuity, 
                                number=number,  #optional: number=0, 
                                #optional: alignment=processorAlignment(), 
                                #optional: dataGenerationTime={processorname:time}, 
                                identifier='/my/pathname/myfile.wav', #optional: identifier=None
                                )
                                
                                

        outputscenario_C.appendScenarioLine(None, 'C','in',
                                {'A':np.ones((100,2000)),'B':np.ones((100,2000))},        #data, 
                                1449478633.333646+tsteps*delta_t,          #startTime, 
                                fs,                      #fs, 
                                processor_name,             #processorName, 
                                set([tested_processor_name,'microphone',]),      #sources, 
                                continuity_out ,    #continuity, 
                                number=number,  #optional: number=0, 
                                alignment=chunkAlignment(),#optional: alignment=chunkAlignment(), 
                                #optional: dataGenerationTime={processorname:time}, 
                                identifier='/my/pathname/myfile.wav', #optional: identifier=None
                                )
                            
    # Introduce the illegal overtake
    
    # Swap 3B and 2B
    inputscenario.scenariolist[5],  inputscenario.scenariolist[7]=   inputscenario.scenariolist[7],  inputscenario.scenariolist[5]
    # As a consequence 3C should have continuity discontinuous and 2C dropped                    
    outputscenario_C.scenariolist[3].continuity=Continuity.discontinuous
    del outputscenario_C.scenariolist[2]
    
    testboard.startProcessor(tested_processor_name, CompositeTester,
                            *subscriptionsorders, 
                            scenario=outputscenario_C )
    
    test_processor_C=testboard.processors[tested_processor_name][0]                         
    test_processor_C.sources=set(['microphone',])
    
    
    time.sleep(0.2)
                                                
    inputscenario.play(testboard, 0.2)            



@with_setup(my_setup_function,my_teardown_function)  
def test_online_processingflow_lostintransmission0A():
    global testboard, logger     
    
    inputscenario=Scenario(logger)
    processor_name='AB_Test'
    requiredKeys=['preA','preB']
    logdir='.'
    subscriptionsorders=[
    SubscriptionOrder('virtualpre','AB_Test', 'A','preA'),
    SubscriptionOrder('virtualpre','AB_Test', 'B','preB'),
    ]
    
    testboard.createOnBoardTestProcessor(processor_name, ChunkEmitter, *subscriptionsorders, onBoard=True)
    scenario_processor=testboard.processors[processor_name][0]
    scenario_processor.sources=set(['microphone',])
    
    tested_processor_name='TestedC'
    subscriptionsorders=[
    SubscriptionOrder(processor_name,tested_processor_name, 'A','A'),
    SubscriptionOrder(processor_name,tested_processor_name, 'B','B'),
    ]
   
    
    time.sleep(0.05)
    
    
    fs=41000
    chunkwidth=2000
    delta_t=float(chunkwidth)/fs
    outputscenario_C = Scenario(logger)
    
    for tsteps, number, continuity, continuity_out in [ (0,0,Continuity.discontinuous,Continuity.discontinuous ),
                                        (1,1,Continuity.withprevious,Continuity.withprevious),
                                        (2,2,Continuity.withprevious,Continuity.withprevious),
                                        (3,3,Continuity.withprevious,Continuity.withprevious),
                                        (4,4,Continuity.withprevious,Continuity.withprevious),
                                        (5,5,Continuity.withprevious,Continuity.withprevious),
                                        (6,6,Continuity.withprevious,Continuity.withprevious),]:
                                            
        inputscenario.appendScenarioLine(scenario_processor, 'A','out',
                                np.ones((100,2000)),        #data, 
                                1449478633.333646+tsteps*delta_t,          #startTime, 
                                fs,                      #fs, 
                                processor_name,             #processorName, 
                                scenario_processor.sources,       #sources, 
                                continuity ,    #continuity, 
                                number=number,  #optional: number=0, 
                                #optional: alignment=processorAlignment(), 
                                #optional: dataGenerationTime={processorname:time}, 
                                identifier='/my/pathname/myfile.wav', #optional: identifier=None
                                )
                                
        inputscenario.appendScenarioLine(scenario_processor, 'B','out',
                                np.ones((100,2000)),        #data, 
                                1449478633.333646+tsteps*delta_t,          #startTime, 
                                fs,                      #fs, 
                                processor_name,             #processorName, 
                                scenario_processor.sources,       #sources, 
                                continuity ,    #continuity, 
                                number=number,  #optional: number=0, 
                                #optional: alignment=processorAlignment(), 
                                #optional: dataGenerationTime={processorname:time}, 
                                identifier='/my/pathname/myfile.wav', #optional: identifier=None
                                )
                                
                                

        outputscenario_C.appendScenarioLine(None, 'C','in',
                                {'A':np.ones((100,2000)),'B':np.ones((100,2000))},        #data, 
                                1449478633.333646+tsteps*delta_t,          #startTime, 
                                fs,                      #fs, 
                                processor_name,             #processorName, 
                                set([tested_processor_name,'microphone',]),      #sources, 
                                continuity_out ,    #continuity, 
                                number=number,  #optional: number=0, 
                                alignment=chunkAlignment(),#optional: alignment=chunkAlignment(), 
                                #optional: dataGenerationTime={processorname:time}, 
                                identifier='/my/pathname/myfile.wav', #optional: identifier=None
                                )
                            
    # Introduce the illegal overtake
    
    # Chunk 0A not transmitted
    del inputscenario.scenariolist[0]
    
    # As a consequence 1C should have continuity discontinuous and 0C should be dropped                   
    outputscenario_C.scenariolist[1].continuity=Continuity.discontinuous
    del outputscenario_C.scenariolist[0]
    
    testboard.startProcessor(tested_processor_name, CompositeTester,
                            *subscriptionsorders, 
                            scenario=outputscenario_C )
    
    test_processor_C=testboard.processors[tested_processor_name][0]                         
    test_processor_C.sources=set(['microphone',])
    
    
    time.sleep(0.2)
                                                
    inputscenario.play(testboard, 0.2)            



@with_setup(my_setup_function,my_teardown_function)  
def test_online_processingflow_lostintransmission2B():
    global testboard, logger     
    
    inputscenario=Scenario(logger)
    processor_name='AB_Test'
    requiredKeys=['preA','preB']
    logdir='.'
    subscriptionsorders=[
    SubscriptionOrder('virtualpre','AB_Test', 'A','preA'),
    SubscriptionOrder('virtualpre','AB_Test', 'B','preB'),
    ]
    
    testboard.createOnBoardTestProcessor(processor_name, ChunkEmitter, *subscriptionsorders, onBoard=True)
    scenario_processor=testboard.processors[processor_name][0]
    scenario_processor.sources=set(['microphone',])
    
    tested_processor_name='TestedC'
    subscriptionsorders=[
    SubscriptionOrder(processor_name,tested_processor_name, 'A','A'),
    SubscriptionOrder(processor_name,tested_processor_name, 'B','B'),
    ]
   
    
    time.sleep(0.05)
    
    
    fs=41000
    chunkwidth=2000
    delta_t=float(chunkwidth)/fs
    outputscenario_C = Scenario(logger)
    
    for tsteps, number, continuity, continuity_out in [ (0,0,Continuity.discontinuous,Continuity.discontinuous ),
                                        (1,1,Continuity.withprevious,Continuity.withprevious),
                                        (2,2,Continuity.withprevious,Continuity.withprevious),
                                        (3,3,Continuity.withprevious,Continuity.withprevious),
                                        (4,4,Continuity.withprevious,Continuity.withprevious),
                                        (5,5,Continuity.withprevious,Continuity.withprevious),
                                        (6,6,Continuity.withprevious,Continuity.withprevious),]:
                                            
        inputscenario.appendScenarioLine(scenario_processor, 'A','out',
                                np.ones((100,2000)),        #data, 
                                1449478633.333646+tsteps*delta_t,          #startTime, 
                                fs,                      #fs, 
                                processor_name,             #processorName, 
                                scenario_processor.sources,       #sources, 
                                continuity ,    #continuity, 
                                number=number,  #optional: number=0, 
                                #optional: alignment=processorAlignment(), 
                                #optional: dataGenerationTime={processorname:time}, 
                                identifier='/my/pathname/myfile.wav', #optional: identifier=None
                                )
                                
        inputscenario.appendScenarioLine(scenario_processor, 'B','out',
                                np.ones((100,2000)),        #data, 
                                1449478633.333646+tsteps*delta_t,          #startTime, 
                                fs,                      #fs, 
                                processor_name,             #processorName, 
                                scenario_processor.sources,       #sources, 
                                continuity ,    #continuity, 
                                number=number,  #optional: number=0, 
                                #optional: alignment=processorAlignment(), 
                                #optional: dataGenerationTime={processorname:time}, 
                                identifier='/my/pathname/myfile.wav', #optional: identifier=None
                                )
                                
                                

        outputscenario_C.appendScenarioLine(None, 'C','in',
                                {'A':np.ones((100,2000)),'B':np.ones((100,2000))},        #data, 
                                1449478633.333646+tsteps*delta_t,          #startTime, 
                                fs,                      #fs, 
                                processor_name,             #processorName, 
                                set([tested_processor_name,'microphone',]),      #sources, 
                                continuity_out ,    #continuity, 
                                number=number,  #optional: number=0, 
                                alignment=chunkAlignment(),#optional: alignment=chunkAlignment(), 
                                #optional: dataGenerationTime={processorname:time}, 
                                identifier='/my/pathname/myfile.wav', #optional: identifier=None
                                )
                            
    # Introduce the illegal overtake
    
    # Chunk 2B not transmitted
    del inputscenario.scenariolist[5]
    
    # As a consequence 1C should have continuity discontinuous and 0C should be dropped                   
    outputscenario_C.scenariolist[3].continuity=Continuity.discontinuous
    del outputscenario_C.scenariolist[2]
    
    testboard.startProcessor(tested_processor_name, CompositeTester,
                            *subscriptionsorders, 
                            scenario=outputscenario_C )
    
    test_processor_C=testboard.processors[tested_processor_name][0]                         
    test_processor_C.sources=set(['microphone',])
    
    
    time.sleep(0.2)
                                                
    inputscenario.play(testboard, 0.01)            
