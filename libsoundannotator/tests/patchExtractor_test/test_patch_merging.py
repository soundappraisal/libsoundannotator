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
from nose import with_setup

from libsoundannotator.cpsp import patchExtractor, patchProcessor
import numpy as np
import multiprocessing


from libsoundannotator.streamboard.continuity     import Continuity
from libsoundannotator.streamboard.compositor     import DataChunk, compositeChunk

import psutil , os

'''
Auxilary code for mapping connected components to a unique representation
'''     
def normalize_labels(Labels):
    '''
        Make labels unique by remapping the labels to integers in the range 
        0 .. noofComponents-1, in  ROW MAJOR order of label appearance. 
        
        This is needed to test labelling in the presence of mechanism that 
        break this convention, e.g. the patch join operation will break 
        this convention.
    '''
    _labels,locations=np.unique(Labels,return_index=True)
    _labels,inverse=np.unique(Labels,return_inverse=True)
    sorted_location_indices=np.argsort(locations)
    sorted_labels=np.zeros(np.shape(sorted_location_indices))
    sorted_labels[sorted_location_indices]=np.arange(np.shape(sorted_location_indices)[0])
    uniquelabels=sorted_labels[inverse]
    return uniquelabels.reshape(np.shape(Labels))
    
def test_normalize_labels():
    expected=np.array([[0,1,2,2,],[0,1,2,2,],[3,3,3,3,]])
    Labels=np.array([[10,21,13,13,],[10,21,13,13,],[-10,-10,-10,-10]])
    uniquelabels=normalize_labels(Labels)
    np.testing.assert_equal(uniquelabels,expected)

def test_normalize_labels2():
    expected=np.array([[0,0,1,],[2,2,1,],[3,3,1,],[3,3,1,]])
    Labels=np.array([[10,21,13,13,],[10,21,13,13,],[-10,-10,-10,-10]])
    uniquelabels=normalize_labels(Labels.T)
    np.testing.assert_equal(uniquelabels,expected)    
 
'''
Testing connected component labelling
''' 


def test_join_bulk_connection1():
    p=patchExtractor.patchExtractor()
    joinMatrixExpected= np.array(
        [[0,0],[1,1],[2,2],[3,3],[4,4]
        ,[5,5],[6,0],[7,3],[8,0],[9,4]
        ,[10,5],[0,0],[0,0],[0,0],[0,0]
        ,[0,0],[0,0],[0,0],[0,0],[0,0],])
        
    tex_before  =np.array([0,0,1,2,3,0,0,2,2 ,1],'int32')
    patch_before=np.array([0,0,1,2,3,0,0,4,4 ,5],'int32')
    
    tex_after   =np.array([0,0,3,3,3,0,0,2,2 ,1],'int32')
    patch_after =np.array([6,6,7,7,7,8,8,9,9,10],'int32')
    
    joinMatrix=np.zeros([20,2],'int32')
    
    print('{0}, {1}'.format(patch_before,patch_after))
    validpatches=p.cpp_calcJoinMatrix(tex_before, tex_after, patch_before, patch_after, joinMatrix )
    print('joinMatrix:{0}, validpatches:{1}'.format(joinMatrix[0:validpatches,:],validpatches))
    np.testing.assert_equal(joinMatrixExpected,joinMatrix)



def test_join_bulk_connection2():
    p=patchExtractor.patchExtractor()
    joinMatrixExpected= np.array(
        [[0,0],[1,1],[2,2],[3,3],[4,0]
        ,[5,5],[6,6],[10,0],[11,3],[13,5]
        ,[14,14],[0,0],[0,0],[0,0],[0,0]
        ,[0,0],[0,0],[0,0],[0,0],[0,0],])
        
    tex_before  =np.array([ 0, 0, 1, 2, 3, 0, 0, 2, 2, 0],'int32')
    patch_before=np.array([ 0, 0, 1, 2, 3, 4, 4, 5, 5, 6],'int32')
    
    tex_after   =np.array([ 0, 0, 3, 3, 3, 0, 0, 2, 2, 1],'int32')
    patch_after =np.array([10,10,11,11,11,10,10,13,13,14],'int32')
    
    joinMatrix=np.zeros([20,2],'int32')
    
    print('{0}, {1}'.format(patch_before,patch_after))
    validpatches=p.cpp_calcJoinMatrix(tex_before, tex_after, patch_before, patch_after, joinMatrix )
    print('joinMatrix:{0}, validpatches:{1}'.format(joinMatrix[0:validpatches,:],validpatches))
    np.testing.assert_equal(joinMatrixExpected,joinMatrix)

def test_join_double_bulk_connection():
    p=patchExtractor.patchExtractor()
    joinMatrixExpected= np.array(
        [[0,0],[1,1],[2,2],[3,3],[5,5]
        ,[6,6],[10,0],[11,3],[13,5],[14,14]
        ,[0,0],[0,0],[0,0],[0,0],[0,0]
        ,[0,0],[0,0],[0,0],[0,0],[0,0],])
        
    tex_before  =np.array([ 0, 0, 1, 2, 3, 0, 0, 2, 2, 0],'int32')
    patch_before=np.array([ 0, 0, 1, 2, 3, 0, 0, 5, 5, 6],'int32')
    
    tex_after   =np.array([ 0, 0, 3, 3, 3, 0, 0, 2, 2, 1],'int32')
    patch_after =np.array([10,10,11,11,11,10,10,13,13,14],'int32')
    
    joinMatrix=np.zeros([20,2],'int32')
    
    print('{0}, {1}'.format(patch_before,patch_after))
    validpatches=p.cpp_calcJoinMatrix(tex_before, tex_after, patch_before, patch_after, joinMatrix )
    print('joinMatrix:{0}, validpatches:{1}'.format(joinMatrix[0:validpatches,:],validpatches))
    np.testing.assert_equal(joinMatrixExpected,joinMatrix)
    #assert(False)

def test_memory_allocation1():
    '''
        Mainly testing whether memory is handled correctly, when calling 
        the c++ code. Python code is partly responsible for allocating memory
        when the cpp code is in use this memory cannot be garbage collected
        without consequence. Reallocating in c++ would lead to unneeded 
        memory usage.
        
        No stress here on correctness of result, therefore no check on 
        generated output.
    '''
    
    
    fs=100
    noofscales=49
    startTime1=12.
    logger = multiprocessing.log_to_stderr()
    quantizer=patchProcessor.textureQuantizer()
   
    datapattern=np.ones((noofscales,2),dtype=np.float)
    datapattern[:,1]=30
    datapattern[np.ceil(noofscales/2).astype(int),:]=90
   
   
    requiredKeys=frozenset(['TSRep',])
    processorname='testing'
    sources={'mock_tf'}
    startTime=12.
    
    p=patchProcessor.patchProcessorCore(quantizer=quantizer,noofscales=noofscales, logger=logger,SampleRate=fs)
    p.prerun()
    
    
   
    mem = psutil.virtual_memory()
    testrange=[np.min([13, np.floor(np.log2(mem.available/20000.)).astype(np.int32)]),7,-2]
    
    for power in np.arange(*testrange): 
        
        data1=np.tile(datapattern,2**power)
        
        mem = psutil.virtual_memory()
        process = psutil.Process(os.getpid())
        mem2 = process.memory_full_info()
        
        logger.info('Power: {0} , free memory: {1} memory used: {2}'.format(power, mem.available, mem2.uss))
       
        
        not_a_composite_chunk1=compositeChunk(12, requiredKeys)
        not_a_composite_chunk1.received['TSRep'] = DataChunk(data1, startTime1, fs, processorname, sources,number=12)
        not_a_composite_chunk1.received['TSRep'].continuity     = Continuity.discontinuous
        not_a_composite_chunk1.received['TSRep'].chunkcontinuity= Continuity.discontinuous
        not_a_composite_chunk1.received['TSRep'].initialSampleTime=startTime
        
        r1=p.processData(not_a_composite_chunk1.received['TSRep'])
        startTime=startTime+data1.shape[1]/fs
        
 
        not_a_composite_chunk2=compositeChunk(13, requiredKeys)
        not_a_composite_chunk2.received['TSRep'] = DataChunk(data1, startTime1, fs, processorname, sources,number=12)
        not_a_composite_chunk2.received['TSRep'].continuity     = Continuity.continuous
        not_a_composite_chunk2.received['TSRep'].chunkcontinuity= Continuity.continuous
        not_a_composite_chunk2.received['TSRep'].initialSampleTime=startTime
        
        r2=p.processData(not_a_composite_chunk2.received['TSRep'])
        startTime=startTime+data1.shape[1]/fs
        
    del p


def test_memory_allocation2():
    '''
        Mainly testing whether memory is handled correctly, when calling 
        the c++ code. Python code is partly responsible for allocating memory
        when the cpp code is in use this memory cannot be garbage collected
        without consequence. Reallocating in c++ would lead to unneeded 
        memory usage.
        
        No stress here on correctness of result, therefore no check on 
        generated output.
    '''
    
    
    
    fs=100
    noofscales=49
    startTime1=12.
    logger = multiprocessing.log_to_stderr()
    quantizer=patchProcessor.textureQuantizer()
   
    datapattern=np.ones((noofscales,2),dtype=np.float)
    datapattern[:,1]=30
    datapattern[np.ceil(noofscales/2).astype(int),:]=90
   
   
    requiredKeys=frozenset(['TSRep',])
    processorname='testing'
    sources={'mock_tf'}
    startTime=12.
    
    p=patchProcessor.patchProcessorCore(quantizer=quantizer,noofscales=noofscales, logger=logger,SampleRate=fs)
    p.prerun()
  
    mem = psutil.virtual_memory()
    testrange=[7,np.min([14, np.floor(np.log2(mem.available/20000.)).astype(np.int32)]),2]
    
    for power in np.arange(*testrange): 
        
        data1=np.tile(datapattern,2**power)
        mem = psutil.virtual_memory()
        process = psutil.Process(os.getpid())
        mem2 = process.memory_full_info()
        
        logger.info('Power: {0} , free memory: {1} memory used: {2}'.format(power, mem.available, mem2.uss))
        
        print(data1.shape)
        
        not_a_composite_chunk1=compositeChunk(12, requiredKeys)
        not_a_composite_chunk1.received['TSRep'] = DataChunk(data1, startTime1, fs, processorname, sources,number=12)
        not_a_composite_chunk1.received['TSRep'].continuity     = Continuity.discontinuous
        not_a_composite_chunk1.received['TSRep'].chunkcontinuity= Continuity.discontinuous
        not_a_composite_chunk1.received['TSRep'].initialSampleTime=startTime
        
        r1=p.processData(not_a_composite_chunk1.received['TSRep'])
        startTime=startTime+data1.shape[1]/fs
        
 
        not_a_composite_chunk2=compositeChunk(13, requiredKeys)
        not_a_composite_chunk2.received['TSRep'] = DataChunk(data1, startTime1, fs, processorname, sources,number=12)
        not_a_composite_chunk2.received['TSRep'].continuity     = Continuity.continuous
        not_a_composite_chunk2.received['TSRep'].chunkcontinuity= Continuity.continuous
        not_a_composite_chunk2.received['TSRep'].initialSampleTime=startTime
        
        r2=p.processData(not_a_composite_chunk2.received['TSRep'])
        startTime=startTime+data1.shape[1]/fs
        
    del p




 
 





def test_process_continuous_chunks():
    
    fs=100
    
    logger = multiprocessing.log_to_stderr()
    quantizer=patchProcessor.textureQuantizer()
    p=patchProcessor.patchProcessorCore(quantizer=quantizer,noofscales=10, logger=logger,SampleRate=fs)
    p.prerun()
    
    requiredKeys=frozenset(['TSRep',])
    
    processorname='testing'
    sources={'mock_tf'}
    
    data1=np.ones((10,20),dtype=np.float)
    data1[5:,:10]=30*np.ones((5,10),dtype=np.float)
    data1[5:,10:]=1*np.ones((5,10),dtype=np.float)
    
    data1[5:,18:]=70*np.ones((5,2),dtype=np.float)
    data2=70*np.ones((10,20),dtype=np.float)
    data2[5:,18:]=30*np.ones((5,2),dtype=np.float)
    data2[:4,:]=1*np.ones((4,20),dtype=np.float)
    
    startTime1=12.
    startTime2=12.+20./fs
    
    not_a_composite_chunk1=compositeChunk(12, requiredKeys)
    not_a_composite_chunk1.received['TSRep'] = DataChunk(data1, startTime1, fs, processorname, sources,number=12)
    not_a_composite_chunk1.received['TSRep'].continuity     = Continuity.discontinuous
    not_a_composite_chunk1.received['TSRep'].chunkcontinuity= Continuity.discontinuous
    not_a_composite_chunk1.received['TSRep'].initialSampleTime=startTime1
    
    # Chunks can contain empty matrices, should basically be ignored if continuity is withprevious or compatible
    not_a_composite_chunk3=compositeChunk(13, requiredKeys)
    not_a_composite_chunk3.received['TSRep']= DataChunk(np.zeros((10,0)), startTime2, fs, processorname, sources,number=13)
    not_a_composite_chunk3.received['TSRep'].initialSampleTime=startTime2
    
    
    not_a_composite_chunk2=compositeChunk(14, requiredKeys)
    not_a_composite_chunk2.received['TSRep']= DataChunk(data2, startTime2, fs, processorname, sources,number=14)
    not_a_composite_chunk2.received['TSRep'].initialSampleTime=startTime2
    
    r1=p.processData(not_a_composite_chunk1.received['TSRep'])
    r3=p.processData(not_a_composite_chunk3.received['TSRep'])
    r2=p.processData(not_a_composite_chunk2.received['TSRep'])
   
    np.testing.assert_equal(r1['matrix'],np.array(
                                                [   [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,],
                                                    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,],
                                                    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,],
                                                    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,],
                                                    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,],
                                                    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 2, 2,],
                                                    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 2, 2,],
                                                    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 2, 2,],
                                                    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 2, 2,],
                                                    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 2, 2,],]))
    
    
    np.testing.assert_equal(r1['levels'],np.array( 
                                                [[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
                                                , [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
                                                , [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
                                                , [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
                                                , [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
                                                , [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 2, 2]
                                                , [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 2, 2]
                                                , [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 2, 2]
                                                , [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 2, 2]
                                                , [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 2, 2]]))
                                                    
    np.testing.assert_equal(r2['matrix'],np.array(
                                                    [ [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
                                                    , [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
                                                    , [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
                                                    , [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
                                                    , [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2]
                                                    , [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 5, 5]
                                                    , [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 5, 5]
                                                    , [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 5, 5]
                                                    , [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 5, 5]
                                                    , [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 5, 5]]))
                                                
    np.testing.assert_equal(r2['levels'],np.array( 
                                                [ [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
                                                , [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
                                                , [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
                                                , [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
                                                , [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2]
                                                , [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 1, 1]
                                                , [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 1, 1]
                                                , [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 1, 1]
                                                , [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 1, 1]
                                                , [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 1, 1]]))
    
    
    
    expectedPatchesChunk1=dict()
    dummy=dict()
    dummy['typelabel']=None 
    dummy['level']=0 
    dummy['s_shape']=(10,)  
    dummy['s_range']=[0, 9] 
    dummy['t_shape']=(20,) 
    dummy['t_range']=[ 12. ,   12.19] 
    dummy['size']=140 
    dummy['serial_number']=0 
    expectedPatchesChunk1[dummy['serial_number']]=dummy
    dummy=dict()
    dummy['typelabel']=None 
    dummy['level']=1 
    dummy['s_shape']=(5,)  
    dummy['s_range']=[5, 9] 
    dummy['t_shape']=(10,) 
    dummy['t_range']=[ 12. ,   12.09] 
    dummy['size']=50 
    dummy['serial_number']=1
    expectedPatchesChunk1[dummy['serial_number']]=dummy
    dummy=dict()
    dummy['typelabel']=None 
    dummy['level']=2 
    dummy['s_shape']=(5,)  
    dummy['s_range']=[5, 9] 
    dummy['t_shape']=(2,) 
    dummy['t_range']=[ 12.18,  12.19] 
    dummy['size']=10 
    dummy['serial_number']=2 
    expectedPatchesChunk1[dummy['serial_number']]=dummy




    expectedPatchesChunk2=dict()
    dummy=dict()
    dummy['typelabel']=None 
    dummy['level']=0 
    dummy['s_shape']=(10,)  
    dummy['s_range']=[0,9] 
    dummy['t_shape']=(40,) 
    dummy['t_range']=[ 12.0,   12.39] 
    dummy['size']=220 
    dummy['serial_number']=0 
    expectedPatchesChunk2[dummy['serial_number']]=dummy
    dummy=dict()
    dummy['typelabel']=None 
    dummy['level']=2 
    dummy['s_shape']=(6,)  
    dummy['s_range']=[4 ,9] 
    dummy['t_shape']=(22,) 
    dummy['t_range']=[ 12.18,  12.39] 
    dummy['size']=120 
    dummy['serial_number']=2 
    expectedPatchesChunk2[dummy['serial_number']]=dummy
    dummy=dict()
    dummy['typelabel']=None 
    dummy['level']=1 
    dummy['s_shape']=(5,)  
    dummy['s_range']=[5, 9] 
    dummy['t_shape']=(2,) 
    dummy['t_range']=[ 12.38 , 12.39] 
    dummy['size']=10 
    dummy['serial_number']=5 
    expectedPatchesChunk2[dummy['serial_number']]=dummy

    #print('{0}, {1}'.format(r1,r2))
    for patch in r1['patches']:
        print '==1======= \n {} \n ====='.format(patch)
        dummy=expectedPatchesChunk1[patch.serial_number]
        for key, value in dummy.items():
            print('key: {0}, value: {1}'.format(key,value))
            if type(value) == list:
                np.testing.assert_almost_equal( patch.__dict__[key],value,decimal=6)  # microsecond precision
            else:
                assert(value == patch.__dict__[key])
    
    for patch in r2['patches']:
        print '==2======= \n {0} \n ======='.format(patch)
        dummy=expectedPatchesChunk2[patch.serial_number]
        for key, value in dummy.items():
            print('key: {0}, value: {1}'.format(key,value))
            assert(key in patch.__dict__.keys())
            print('value: {0}'.format(patch.__dict__[key]))
            if type(value) == list:
                np.testing.assert_almost_equal( patch.__dict__[key],value,decimal=6) # microsecond precision
            else:
                assert(value == patch.__dict__[key])
    
      
    del p
        
    #assert(False)
