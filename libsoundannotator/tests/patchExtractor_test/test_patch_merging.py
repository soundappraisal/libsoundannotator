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


def test_process_continuous_chunks():
    
    logger = multiprocessing.log_to_stderr()
    quantizer=patchProcessor.textureQuantizer()
    p=patchProcessor.patchProcessorCore(quantizer=quantizer,noofscales=100, logger=logger)
    p.prerun()
    
    requiredKeys=frozenset(['TSRep',])
    
    fs=44100
    processorname='testing'
    sources={'mock_tf'}
    
    data1=np.zeros((100,8820),dtype=np.float)
    data2=np.zeros((100,8820),dtype=np.float)
    
    startTime1=12.
    startTime2=12.+8820./fs
    
    not_a_composite_chunk1=compositeChunk(12, requiredKeys)
    not_a_composite_chunk1.received['TSRep'] = DataChunk(data1, startTime1, fs, processorname, sources)
    not_a_composite_chunk1.continuity=Continuity.discontinuous
    not_a_composite_chunk1.chunkcontinuity=Continuity.discontinuous
    not_a_composite_chunk1.received['TSRep'].initialSampleTime=0.1
    
    not_a_composite_chunk2=compositeChunk(13, requiredKeys)
    not_a_composite_chunk2.received['TSRep']= DataChunk(data2, startTime2, fs, processorname, sources)
    not_a_composite_chunk2.received['TSRep'].initialSampleTime=0.1
    
    r1=p.processData(not_a_composite_chunk1.received['TSRep'])
    r2=p.processData(not_a_composite_chunk2.received['TSRep'])

    
    #print('{0}, {1}'.format(r1,r2))
    print('patches {0}, {1}'.format(r1['patches'][0],r2['patches'][0]))
    assert(False)
