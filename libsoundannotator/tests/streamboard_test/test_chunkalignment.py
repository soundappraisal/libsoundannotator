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

'''

from nose import with_setup
from streamboard_testing_tools import TestBoard, Scenario, ChunkEmitter, CompositeTester
from libsoundannotator.streamboard.continuity     import Continuity, chunkAlignment,processorAlignment
import logging, time, sys
import numpy as np

from libsoundannotator.streamboard.subscription       import SubscriptionOrder


            
            
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
def test_online_processingflow1():
    global testboard, logger     
    
    inputscenario=Scenario(logger)
    processor_name='AB_Test'
    requiredKeys=['preA','preB']
    logdir='.'
    subscriptionsorders=[
    SubscriptionOrder('virtualpre','AB_Test', 'A','preA'),
    SubscriptionOrder('virtualpre','AB_Test', 'B','preB'),
    ]
    
    # order arguments in constructor processorAlignment:
    #  includedPast=0 , droppedAfterDiscontinuity=0 , invalidLargeScales=0 , invalidSmallScales=0, alignable=True   
    ip1=15;   ip2=13; ip3=0
    d1 =37;   d2=27;  d3=0
    il1=0 ;   il2=5;  il3=0
    is1=0 ;   is2=7;  is3=0
    
     
    fs=41000.
    
    processoralignment_AB_Test={'A':processorAlignment(ip1,d1,il1,is1,fsampling=fs),'B':processorAlignment(ip2,d2,il2,is2,fsampling=fs)}
    
    testboard.createOnBoardTestProcessor(processor_name, ChunkEmitter, *subscriptionsorders, processoralignment=processoralignment_AB_Test,onBoard=True)
    scenario_processor=testboard.processors[processor_name][0]
    scenario_processor.sources=set(['microphone',])
    
    tested_processor_name='TestedC'
    subscriptionsorders=[
    SubscriptionOrder(processor_name,tested_processor_name, 'A','A'),
    SubscriptionOrder(processor_name,tested_processor_name, 'B','B'),
    ]
   
    
    time.sleep(0.05)
    
   
    chunkwidth=2000
    delta_t=float(chunkwidth)/fs
    outputscenario_C = Scenario(logger)
    
   
    scenarioStartTime=1449478633.333646
  

  
   
    
    
    # tsteps, number, 
    #   continuity, continuity_out, 
    #       alignmentA, alignmentB, alignmnetC ,alignmentD, 
    #           in_shapeA, inshapeB, out_shapes
    #               initial_frame_offset
    #
    # line 0: regular discontinuous
    # line 1: regular continuous
    # line 2: regular continuous
    # line 3: irregular discontinuous
    # line 4: regular continuous
    # line 5: regular continuous
    
    summaryScenario=[ 
            (0,0,
                Continuity.discontinuous,Continuity.discontinuous ,
                    (ip1,d1,il1,is1),(ip2,d2,il2,is2),(max(ip1,ip2),max(d1,d2),max(il1,il2),max(is1,is2)),(max(ip1,ip2)+ip3,max(d1,d2)+d3,max(il1,il2)+il3,max(is1,is2)+is3),
                            (100,2000-ip1-d1),(100,2000-ip2-d2), (100,2000-max(ip1,ip2)-max(d1,d2)),
                                max(d1,d2)/fs),
            (1,1,
                Continuity.withprevious ,Continuity.withprevious  ,
                    (ip1,d1,il1,is1),(ip2,d2,il2,is2),(max(ip1,ip2),max(d1,d2),max(il1,il2),max(is1,is2)),(max(ip1,ip2)+ip3,max(d1,d2)+d3,max(il1,il2)+il3,max(is1,is2)+is3), 
                            (100,2000),(100,2000),(100,2000),
                                -max(ip1,ip2)/fs),
            (2,2,
                Continuity.withprevious ,Continuity.withprevious  ,
                    (ip1,d1,il1,is1),(ip2,d2,il2,is2),(max(ip1,ip2),max(d1,d2),max(il1,il2),max(is1,is2)),(max(ip1,ip2)+ip3,max(d1,d2)+d3,max(il1,il2)+il3,max(is1,is2)+is3), 
                            (100,2000),(100,2000),(100,2000),
                                -max(ip1,ip2)/fs),
            (4,4,
                Continuity.withprevious ,Continuity.discontinuous ,
                    (ip1,d1,il1,is1),(ip2,d2,il2,is2),(max(ip1,ip2),max(d1,d2),max(il1,il2),max(is1,is2)), (max(ip1,ip2)+ip3,max(d1,d2)+d3,max(il1,il2)+il3,max(is1,is2)+is3), 
                            (100,2000),(100,2000),(100,2000-max(ip1+d1,ip2+d2)),
                                max(d1,d2)/fs),
            (5,5,
                Continuity.withprevious ,Continuity.withprevious  ,
                    (ip1,d1,il1,is1),(ip2,d2,il2,is2),(max(ip1,ip2),max(d1,d2),max(il1,il2),max(is1,is2)),(max(ip1,ip2)+ip3,max(d1,d2)+d3,max(il1,il2)+il3,max(is1,is2)+is3), 
                            (100,2000),(100,2000),(100,2000),
                                -max(ip1,ip2)/fs),
            (6,6,
                Continuity.withprevious ,Continuity.withprevious  ,
                    (ip1,d1,il1,is1),(ip2,d2,il2,is2),(max(ip1,ip2),max(d1,d2),max(il1,il2),max(is1,is2)),(max(ip1,ip2)+ip3,max(d1,d2)+d3,max(il1,il2)+il3,max(is1,is2)+is3),
                            (100,2000),(100,2000),(100,2000) ,
                                -max(ip1,ip2)/fs),
    ]
    
    for tsteps, number,  continuity, continuity_out, alignmentA, alignmentB, alignmentC,alignmentD,in_shapeA, in_shapeB, out_shapes, initial_frame_offset  in summaryScenario:
                                            
        inputscenario.appendScenarioLine(scenario_processor, 'A','out',
                                np.ones(in_shapeA),        #data, 
                                scenarioStartTime+tsteps*delta_t,          #startTime, 
                                fs,                      #fs, 
                                processor_name,             #processorName, 
                                scenario_processor.sources,       #sources, 
                                continuity ,    #continuity, 
                                number=number,  #optional: number=0, 
                                alignment=processorAlignment(*alignmentA,fsampling=fs) ,#optional: alignment=processorAlignment(), 
                                #optional: dataGenerationTime={processorname:time}, 
                                identifier='/my/pathname/myfile.wav', #optional: identifier=None
                                )
                                
        inputscenario.appendScenarioLine(scenario_processor, 'B','out',
                                np.ones(in_shapeB),        #data, 
                                scenarioStartTime+tsteps*delta_t,          #startTime, 
                                fs,                      #fs, 
                                processor_name,             #processorName, 
                                scenario_processor.sources,       #sources, 
                                continuity ,    #continuity, 
                                number=number,  #optional: number=0, 
                                alignment=processorAlignment(*alignmentB,fsampling=fs) ,#optional: alignment=processorAlignment(), 
                                #optional: dataGenerationTime={processorname:time}, 
                                identifier='/my/pathname/myfile.wav', #optional: identifier=None
                                )
                                
        outputscenario_C.appendScenarioLine(None, 'C','in',
                                {'A':np.ones(out_shapes),'B':np.ones(out_shapes)},        #data, 
                                scenarioStartTime+tsteps*delta_t,          #startTime, 
                                fs,                      #fs, 
                                processor_name,             #processorName, 
                                set(['microphone',]),      #sources, 
                                continuity_out ,    #continuity, 
                                number=number,  #optional: number=0, 
                                alignment=chunkAlignment(*alignmentC,fsampling=fs) ,#optional: alignment=chunkAlignment(), 
                                #optional: dataGenerationTime={processorname:time}, 
                                identifier='/my/pathname/myfile.wav', #optional: identifier=None
                                initialSampleTime=scenarioStartTime+tsteps*delta_t+initial_frame_offset,
                                
                                )
      
                                
                            
    testboard.startProcessor(tested_processor_name, CompositeTester,
                            *subscriptionsorders, 
                            scenario=outputscenario_C,
                            processoralignment={'ExT':processorAlignment(ip3,d3,il3,is3,fsampling=fs)},
                            requiredKeys=['A','B'] )
    
   
    time.sleep(0.05)
                                                
    inputscenario.play(testboard, 0.01)      



@with_setup(my_setup_function,my_teardown_function)  
def test_online_processingflow2():
    global testboard, logger     
    
    inputscenario=Scenario(logger)
    processor_name='AB_Test'
    requiredKeys=['preA','preB']
    logdir='.'
    subscriptionsorders=[
    SubscriptionOrder('virtualpre','AB_Test', 'A','preA'),
    SubscriptionOrder('virtualpre','AB_Test', 'B','preB'),
    ]
    
    # order arguments in constructor processorAlignment:
    #  includedPast=0 , droppedAfterDiscontinuity=0 , invalidLargeScales=0 , invalidSmallScales=0, alignable=True   
    ip2=15;   ip1=13; ip3=0
    d2 =37;   d1=27;  d3=0
    il2=0 ;   il1=5;  il3=0
    is2=0 ;   is1=7;  is3=0
    
     
    fs=41000.
    
    processoralignment_AB_Test={'A':processorAlignment(ip1,d1,il1,is1,fsampling=fs),'B':processorAlignment(ip2,d2,il2,is2,fsampling=fs)}
    
    testboard.createOnBoardTestProcessor(processor_name, ChunkEmitter, *subscriptionsorders, processoralignment=processoralignment_AB_Test,onBoard=True)
    scenario_processor=testboard.processors[processor_name][0]
    scenario_processor.sources=set(['microphone',])
    
    tested_processor_name='TestedC'
    subscriptionsorders=[
    SubscriptionOrder(processor_name,tested_processor_name, 'A','A'),
    SubscriptionOrder(processor_name,tested_processor_name, 'B','B'),
    ]
   
    
    time.sleep(0.05)
    
   
    chunkwidth=2000
    delta_t=float(chunkwidth)/fs
    outputscenario_C = Scenario(logger)
    
   
    scenarioStartTime=1449478633.333646
  

  
   
    
    
    # tsteps, number, 
    #   continuity, continuity_out, 
    #       alignmentA, alignmentB, alignmnetC ,alignmentD, 
    #           in_shapeA, inshapeB, out_shapes
    #               initial_frame_offset
    #
    # line 0: regular discontinuous
    # line 1: regular continuous
    # line 2: regular continuous
    # line 3: irregular discontinuous
    # line 4: regular continuous
    # line 5: regular continuous
    
    summaryScenario=[ 
            (0,0,
                Continuity.discontinuous,Continuity.discontinuous ,
                    (ip1,d1,il1,is1),(ip2,d2,il2,is2),(max(ip1,ip2),max(d1,d2),max(il1,il2),max(is1,is2)),(max(ip1,ip2)+ip3,max(d1,d2)+d3,max(il1,il2)+il3,max(is1,is2)+is3),
                            (100,2000-ip1-d1),(100,2000-ip2-d2), (100,2000-max(ip1,ip2)-max(d1,d2)),
                                max(d1,d2)/fs),
            (1,1,
                Continuity.withprevious ,Continuity.withprevious  ,
                    (ip1,d1,il1,is1),(ip2,d2,il2,is2),(max(ip1,ip2),max(d1,d2),max(il1,il2),max(is1,is2)),(max(ip1,ip2)+ip3,max(d1,d2)+d3,max(il1,il2)+il3,max(is1,is2)+is3), 
                            (100,2000),(100,2000),(100,2000),
                                -max(ip1,ip2)/fs),
            (2,2,
                Continuity.withprevious ,Continuity.withprevious  ,
                    (ip1,d1,il1,is1),(ip2,d2,il2,is2),(max(ip1,ip2),max(d1,d2),max(il1,il2),max(is1,is2)),(max(ip1,ip2)+ip3,max(d1,d2)+d3,max(il1,il2)+il3,max(is1,is2)+is3), 
                            (100,2000),(100,2000),(100,2000),
                                -max(ip1,ip2)/fs),
            (4,4,
                Continuity.withprevious ,Continuity.discontinuous ,
                    (ip1,d1,il1,is1),(ip2,d2,il2,is2),(max(ip1,ip2),max(d1,d2),max(il1,il2),max(is1,is2)), (max(ip1,ip2)+ip3,max(d1,d2)+d3,max(il1,il2)+il3,max(is1,is2)+is3), 
                            (100,2000),(100,2000),(100,2000-max(ip1+d1,ip2+d2)),
                                max(d1,d2)/fs),
            (5,5,
                Continuity.withprevious ,Continuity.withprevious  ,
                    (ip1,d1,il1,is1),(ip2,d2,il2,is2),(max(ip1,ip2),max(d1,d2),max(il1,il2),max(is1,is2)),(max(ip1,ip2)+ip3,max(d1,d2)+d3,max(il1,il2)+il3,max(is1,is2)+is3), 
                            (100,2000),(100,2000),(100,2000),
                                -max(ip1,ip2)/fs),
            (6,6,
                Continuity.withprevious ,Continuity.withprevious  ,
                    (ip1,d1,il1,is1),(ip2,d2,il2,is2),(max(ip1,ip2),max(d1,d2),max(il1,il2),max(is1,is2)),(max(ip1,ip2)+ip3,max(d1,d2)+d3,max(il1,il2)+il3,max(is1,is2)+is3),
                            (100,2000),(100,2000),(100,2000) ,
                                -max(ip1,ip2)/fs),
    ]
    
    for tsteps, number,  continuity, continuity_out, alignmentA, alignmentB, alignmentC,alignmentD,in_shapeA, in_shapeB, out_shapes, initial_frame_offset  in summaryScenario:
                                            
        inputscenario.appendScenarioLine(scenario_processor, 'A','out',
                                np.ones(in_shapeA),        #data, 
                                scenarioStartTime+tsteps*delta_t,          #startTime, 
                                fs,                      #fs, 
                                processor_name,             #processorName, 
                                scenario_processor.sources,       #sources, 
                                continuity ,    #continuity, 
                                number=number,  #optional: number=0, 
                                alignment=processorAlignment(*alignmentA,fsampling=fs) ,#optional: alignment=processorAlignment(), 
                                #optional: dataGenerationTime={processorname:time}, 
                                identifier='/my/pathname/myfile.wav', #optional: identifier=None
                                )
                                
        inputscenario.appendScenarioLine(scenario_processor, 'B','out',
                                np.ones(in_shapeB),        #data, 
                                scenarioStartTime+tsteps*delta_t,          #startTime, 
                                fs,                      #fs, 
                                processor_name,             #processorName, 
                                scenario_processor.sources,       #sources, 
                                continuity ,    #continuity, 
                                number=number,  #optional: number=0, 
                                alignment=processorAlignment(*alignmentB,fsampling=fs) ,#optional: alignment=processorAlignment(), 
                                #optional: dataGenerationTime={processorname:time}, 
                                identifier='/my/pathname/myfile.wav', #optional: identifier=None
                                )
                                
        outputscenario_C.appendScenarioLine(None, 'C','in',
                                {'A':np.ones(out_shapes),'B':np.ones(out_shapes)},        #data, 
                                scenarioStartTime+tsteps*delta_t,          #startTime, 
                                fs,                      #fs, 
                                processor_name,             #processorName, 
                                set(['microphone',]),      #sources, 
                                continuity_out ,    #continuity, 
                                number=number,  #optional: number=0, 
                                alignment=chunkAlignment(*alignmentC,fsampling=fs) ,#optional: alignment=chunkAlignment(), 
                                #optional: dataGenerationTime={processorname:time}, 
                                identifier='/my/pathname/myfile.wav', #optional: identifier=None
                                initialSampleTime=scenarioStartTime+tsteps*delta_t+initial_frame_offset,
                                
                                )
      
                                
                            
    testboard.startProcessor(tested_processor_name, CompositeTester,
                            *subscriptionsorders, 
                            scenario=outputscenario_C,
                            processoralignment={'ExT':processorAlignment(ip3,d3,il3,is3,fsampling=fs)},
                            requiredKeys=['A','B'] )
    
   
    time.sleep(0.05)
                                                
    inputscenario.play(testboard, 0.01)      

