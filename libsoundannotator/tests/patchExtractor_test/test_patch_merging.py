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

from  psutil import virtual_memory
from time import sleep

from multiprocessing import Process, Queue


''' Some of the test in this file are very memory intensive and thus 
create a grow of memory consumption. This leads to problems when later 
processes are forking, because the child process is forked with the 
same amount of memory as the parent. To prevent this from causing 
memory allocation related errors the most memory intensive tests 
now run in separate processes. Also they contain checks to allocate no 
more memory than present at execution time. 

The TestProces class is used for this purpose to ease the propagation 
of exceptions from child to parent. ''' 

class TestProcess(Process):
    
    def __init__(self,*args,**kwargs):
        self.myQueue=kwargs['args'][0]
        super(TestProcess,self).__init__(*args,**kwargs)
        
    def run(self):
        result=None
        try:
            super(TestProcess,self).run()
        except Exception as e:
            result = e 
        self.myQueue.put(result)


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
        [[0,0],[-1,-1],[-1,-1],[3,3],[4,4]
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
        [[0,0],[-1,-1],[-1,-1],[3,3],[4,0]
        ,[5,5],[-1,-1],[10,0],[11,3],[13,5]
        ,[-1,-1],[0,0],[0,0],[0,0],[0,0]
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
        [[0,0],[-1,-1],[-1,-1],[3,3],[5,5]
        ,[-1,-1],[10,0],[11,3],[13,5],[-1,-1]
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
    
    

def memory_allocation_exercise1(myQueue):
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
    
    p=patchProcessor.patchProcessorCore(quantizer=quantizer,
                                        noofscales=noofscales, 
                                        logger=logger,
                                        SampleRate=fs,
                                        PatchType={'ts_rep':'mock_tf','quantizer':type(quantizer).__name__ })
    p.prerun()
    
    
   
    mem = virtual_memory()
    testrange=[np.min([13, np.floor(np.log2(mem.available/20000.)).astype(np.int32)-3]),7,-2]
    print('Available Memory: {0}  '.format(mem.available))
    
    for power in np.arange(*testrange): 
        
        print('Power: {0}  '.format(power))
        data1=np.tile(datapattern,2**power)
        
        mem = virtual_memory()
        print('Memory: {0}  '.format(mem.available))
                
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
        
        del data1, r1, r2 ,not_a_composite_chunk1, not_a_composite_chunk2

def test_memory_allocation_exercise1():
    logger = multiprocessing.log_to_stderr()
    myQueue=Queue()
    p = TestProcess(target=memory_allocation_exercise1, args=[myQueue,],name='TestProcess')
    p.start()
    p.join() # this blocks until the process terminates
    result=myQueue.get()
    if not result is None:
        raise result
    

def memory_allocation_exercise2(myQueue):
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
    
    p=patchProcessor.patchProcessorCore(    quantizer=quantizer,
                                            noofscales=noofscales, 
                                            logger=logger,
                                            SampleRate=fs,
                                            PatchType={'ts_rep':'mock_tf','quantizer':type(quantizer).__name__ })
    p.prerun()
  
    mem = virtual_memory()
    testrange=[7,np.min([14, np.floor(np.log2(mem.available/20000.)).astype(np.int32)-3]),2]
    
    for power in np.arange(*testrange): 
        
        
        print('Power: {0}  '.format(power))
        
        data1=np.tile(datapattern,2**power)
        
        mem = virtual_memory()
        print('Memory: {0}  '.format(mem.available))
      
        print('Data shape: {0}  '.format(data1.shape))
        
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
        



def test_memory_allocation_exercise2():
    logger = multiprocessing.log_to_stderr()
    myQueue=Queue()
    p = TestProcess(target=memory_allocation_exercise2, args=[myQueue,],name='TestProcess2')
    p.start()
    p.join() # this blocks until the process terminates
    result=myQueue.get()
    if not result is None:
        raise result





def process_continuous_chunks(myQueue):
    
    fs=100
    
    logger = multiprocessing.log_to_stderr()
    quantizer=patchProcessor.textureQuantizer()
    p=patchProcessor.patchProcessorCore(quantizer=quantizer,
                                        noofscales=10, 
                                        logger=logger,
                                        SampleRate=fs,                                       
                                        PatchType={'ts_rep':'mock_tf','quantizer':type(quantizer).__name__ })
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
   
    np.testing.assert_equal(r1['matrix'],1+np.array(
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
                                                    
    np.testing.assert_equal(r2['matrix'],1+np.array(
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
    dummy['typelabel']={'quantizer': 'textureQuantizer', 'ts_rep': 'mock_tf'}
    dummy['level']=0 
    dummy['s_shape']=(10,)  
    dummy['s_range']=[0, 9] 
    dummy['t_shape']=(20,) 
    dummy['t_range_seconds']=[ 12. ,   12.20] 
    dummy['size']=140 
    dummy['serial_number']=1+0 
    expectedPatchesChunk1[dummy['serial_number']]=dummy
    dummy=dict()
    dummy['typelabel']={'quantizer': 'textureQuantizer', 'ts_rep': 'mock_tf'}
    dummy['level']=1 
    dummy['s_shape']=(5,)  
    dummy['s_range']=[5, 9] 
    dummy['t_shape']=(10,) 
    dummy['t_range_seconds']=[ 12. ,   12.10] 
    dummy['size']=50 
    dummy['serial_number']=1+1
    expectedPatchesChunk1[dummy['serial_number']]=dummy
    dummy=dict()
    dummy['typelabel']={'quantizer': 'textureQuantizer', 'ts_rep': 'mock_tf'}
    dummy['level']=2 
    dummy['s_shape']=(5,)  
    dummy['s_range']=[5, 9] 
    dummy['t_shape']=(2,) 
    dummy['t_range_seconds']=[ 12.18,  12.20] 
    dummy['size']=10 
    dummy['serial_number']=1+2 
    expectedPatchesChunk1[dummy['serial_number']]=dummy




    expectedPatchesChunk2=dict()
    dummy=dict()
    dummy['typelabel']={'quantizer': 'textureQuantizer', 'ts_rep': 'mock_tf'}
    dummy['level']=0 
    dummy['s_shape']=(10,)  
    dummy['s_range']=[0,9] 
    dummy['t_shape']=(40,) 
    dummy['t_range_seconds']=[ 12.0,   12.40] 
    dummy['size']=220 
    dummy['serial_number']=1+0 
    expectedPatchesChunk2[dummy['serial_number']]=dummy
    dummy=dict()
    dummy['typelabel']={'quantizer': 'textureQuantizer', 'ts_rep': 'mock_tf'}
    dummy['level']=2 
    dummy['s_shape']=(6,)  
    dummy['s_range']=[4 ,9] 
    dummy['t_shape']=(22,) 
    dummy['t_range_seconds']=[ 12.18,  12.40] 
    dummy['size']=120 
    dummy['serial_number']=1+2 
    expectedPatchesChunk2[dummy['serial_number']]=dummy
    dummy=dict()
    dummy['typelabel']={'quantizer': 'textureQuantizer', 'ts_rep': 'mock_tf'}
    dummy['level']=1 
    dummy['s_shape']=(5,)  
    dummy['s_range']=[5, 9] 
    dummy['t_shape']=(2,) 
    dummy['t_range_seconds']=[ 12.38 , 12.40] 
    dummy['size']=10 
    dummy['serial_number']=1+5 
    expectedPatchesChunk2[dummy['serial_number']]=dummy

    #print('{0}, {1}'.format(r1,r2))
    for patch in r1['patches']:
        logger.info('==1======= \n {} \n ====='.format(patch))
        dummy=expectedPatchesChunk1[patch.serial_number]
        for key, value in dummy.items():
            logger.info('key: {0}, value: {1}'.format(key,value))
            if type(value) == list:
                np.testing.assert_almost_equal( patch.__dict__[key],value,decimal=6)  # microsecond precision
            else:
                assert(value == patch.__dict__[key])
    
    for patch in r2['patches']:
        logger.info('==2======= \n {0} \n ======='.format(patch))
        dummy=expectedPatchesChunk2[patch.serial_number]
        for key, value in dummy.items():
            logger.info('key: {0}, value: {1}'.format(key,value))
            assert(key in patch.__dict__.keys())
            logger.info('value: {0}'.format(patch.__dict__[key]))
            if type(value) == list:
                np.testing.assert_almost_equal( patch.__dict__[key],value,decimal=6) # microsecond precision
            else:
                assert(value == patch.__dict__[key])
    



def test_process_continuous_chunks():
    logger = multiprocessing.log_to_stderr()
    myQueue=Queue()
    p = TestProcess(target=process_continuous_chunks, args=[myQueue,],name='TestProcess3')
    p.start()
    p.join() # this blocks until the process terminates
    
    result=myQueue.get()
    if not result is None:
        raise result



def process_continuous_chunks_non_trivial_alignment(myQueue):
    
    fs=100
    
    logger = multiprocessing.log_to_stderr()
    quantizer=patchProcessor.textureQuantizer()
    p=patchProcessor.patchProcessorCore(quantizer=quantizer,
                                        noofscales=10, 
                                        logger=logger,
                                        SampleRate=fs,
                                        PatchType={'ts_rep':'mock_tf','quantizer':type(quantizer).__name__ })
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
   
    np.testing.assert_equal(r1['matrix'],1+np.array(
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
                                                    
    np.testing.assert_equal(r2['matrix'],1+np.array(
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
    dummy['typelabel']={'quantizer': 'textureQuantizer', 'ts_rep': 'mock_tf'}
    dummy['level']=0 
    dummy['s_shape']=(10,)  
    dummy['s_range']=[0, 9] 
    dummy['t_shape']=(20,) 
    dummy['t_range_seconds']=[ 12. ,   12.20] 
    dummy['size']=140 
    dummy['serial_number']=1+0 
    expectedPatchesChunk1[dummy['serial_number']]=dummy
    dummy=dict()
    dummy['typelabel']={'quantizer': 'textureQuantizer', 'ts_rep': 'mock_tf'}
    dummy['level']=1 
    dummy['s_shape']=(5,)  
    dummy['s_range']=[5, 9] 
    dummy['t_shape']=(10,) 
    dummy['t_range_seconds']=[ 12. ,   12.10] 
    dummy['size']=50 
    dummy['serial_number']=1+1
    expectedPatchesChunk1[dummy['serial_number']]=dummy
    dummy=dict()
    dummy['typelabel']={'quantizer': 'textureQuantizer', 'ts_rep': 'mock_tf'} 
    dummy['level']=2 
    dummy['s_shape']=(5,)  
    dummy['s_range']=[5, 9] 
    dummy['t_shape']=(2,) 
    dummy['t_range_seconds']=[ 12.18,  12.20] 
    dummy['size']=10 
    dummy['serial_number']=1+2 
    expectedPatchesChunk1[dummy['serial_number']]=dummy




    expectedPatchesChunk2=dict()
    dummy=dict()
    dummy['typelabel']={'quantizer': 'textureQuantizer', 'ts_rep': 'mock_tf'}
    dummy['level']=0 
    dummy['s_shape']=(10,)  
    dummy['s_range']=[0,9] 
    dummy['t_shape']=(40,) 
    dummy['t_range_seconds']=[ 12.0,   12.40] 
    dummy['size']=220 
    dummy['serial_number']=1+0 
    expectedPatchesChunk2[dummy['serial_number']]=dummy
    dummy=dict()
    dummy['typelabel']={'quantizer': 'textureQuantizer', 'ts_rep': 'mock_tf'}
    dummy['level']=2 
    dummy['s_shape']=(6,)  
    dummy['s_range']=[4 ,9] 
    dummy['t_shape']=(22,) 
    dummy['t_range_seconds']=[ 12.18,  12.40] 
    dummy['size']=120 
    dummy['serial_number']=1+2 
    expectedPatchesChunk2[dummy['serial_number']]=dummy
    dummy=dict()
    dummy['typelabel']={'quantizer': 'textureQuantizer', 'ts_rep': 'mock_tf'}
    dummy['level']=1 
    dummy['s_shape']=(5,)  
    dummy['s_range']=[5, 9] 
    dummy['t_shape']=(2,) 
    dummy['t_range_seconds']=[ 12.38 , 12.40] 
    dummy['size']=10 
    dummy['serial_number']=1+5 
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
    



def test_process_continuous_chunks_non_trivial_alignment():
    logger = multiprocessing.log_to_stderr()
    myQueue=Queue()
    p = TestProcess(target=process_continuous_chunks_non_trivial_alignment, args=[myQueue,],name='TestProcess4')
    p.start()
    p.join() # this blocks until the process terminates
    result=myQueue.get()
    if not result is None:
        raise result
