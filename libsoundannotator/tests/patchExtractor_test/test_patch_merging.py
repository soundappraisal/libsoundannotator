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

from libsoundannotator.cpsp import patchExtractor
import numpy as np

horizontal_stripes=np.zeros([10,20],'int32')
horizontal_stripe_labels=np.zeros([10,20],'int32')
vertical_stripes=np.zeros([10,20],'int32')
vertical_stripe_labels=np.zeros([10,20],'int32')
broken_vertical_stripes=np.zeros([10,20],'int32')
broken_vertical_stripe_labels=np.zeros([10,20],'int32')

def setup_each(): #Only inplace changes are effective here!
    '''
        horizontal-stripes fixture and expected horizontal_stripe_labels
    '''        
    horizontal_stripe_labels[:,:]=np.zeros([10,20],'int32')
    for i in np.arange(10):
        horizontal_stripe_labels[i,:]=i
    horizontal_stripes[:,:]=horizontal_stripe_labels+1
    '''
        vertical_stripes fixture and expected vertical_stripe_labels
    '''
    vertical_stripe_labels[:,:]=np.zeros([10,20],'int32')    
    for i in np.arange(20):  
        vertical_stripe_labels[:,i]=i
    vertical_stripes[:,:]=vertical_stripe_labels-12
    '''
        broken_vertical_stripes fixture and expected vertical_stripe_labels
    '''
    broken_vertical_stripe_labels[:,:]=np.zeros([10,20],'int32')    
    for i in np.arange(20):  
        broken_vertical_stripe_labels[:5,i]=i
        broken_vertical_stripe_labels[5:,i]=i+20
    broken_vertical_stripes[:,:]=broken_vertical_stripe_labels+11

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


