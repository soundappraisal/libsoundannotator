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
@with_setup(setup_each())
def test_horizontal_stripes():
    p=patchExtractor.patchExtractor()
    result=np.zeros(np.shape(horizontal_stripes),'int32') 
    N=p.cpp_calcPatches(horizontal_stripes,result)
    print('{0}'.format(horizontal_stripe_labels))
    print('{0}'.format(horizontal_stripes))
    print('{0}'.format(result))
    np.testing.assert_equal(result,horizontal_stripe_labels)
    assert N==10
    
@with_setup(setup_each())
def test_vertical_stripes():
    p=patchExtractor.patchExtractor()
    result=np.zeros(np.shape(vertical_stripes),'int32')
    N=p.cpp_calcPatches(vertical_stripes,result)
    print('{0}'.format(vertical_stripe_labels))
    print('{0}'.format(vertical_stripes))
    print('{0}'.format(result))
    np.testing.assert_equal(result,vertical_stripe_labels)
    assert N==20 

@with_setup(setup_each())
def test_broken_vertical_stripes():
    p=patchExtractor.patchExtractor()
    result=np.zeros(np.shape(broken_vertical_stripes),'int32')
    N=p.cpp_calcPatches(broken_vertical_stripes,result)
    print('{0}'.format(broken_vertical_stripe_labels))
    print('{0}'.format(broken_vertical_stripes))
    print('{0}'.format(result))
    np.testing.assert_equal(result,broken_vertical_stripe_labels)
    assert N==40
       
'''
Testing primitive patch descriptors
'''
@with_setup(setup_each())
def test_simple_descriptors_broken_vertical_stripes():
    expected=np.array(
        [[11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50],
         [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19],
         [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19],
         [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5],
         [4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9],
         [5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5]]
    )
    p=patchExtractor.patchExtractor()
    dummy=np.zeros(np.shape(broken_vertical_stripes),'int32')
    N=p.cpp_calcPatches(broken_vertical_stripes,dummy)
    result=np.zeros([6,N],'int32')
    p.cpp_getDescriptors(result)
    print('{0}'.format(result))
    np.testing.assert_equal(result,expected)
    
@with_setup(setup_each())
def test_simple_descriptors_horizontal_stripes():
    expected=np.array(
      [[1,2,3,4,5,6,7,8,9,10],
        [0,0,0,0,0,0,0,0,0,0],
        [19,19,19,19,19,19,19,19,19,19],
        [0,1,2,3,4,5,6,7,8,9],
        [0,1,2,3,4,5,6,7,8,9],
        [20,20,20,20,20,20,20,20,20,20]]
    )
    p=patchExtractor.patchExtractor()
    dummy=np.zeros(np.shape(horizontal_stripes),'int32')
    N=p.cpp_calcPatches(horizontal_stripes,dummy)
    result=np.zeros([6,N],'int32')
    p.cpp_getDescriptors(result)
    print('{0}'.format(result))
    np.testing.assert_equal(result,expected)  

    
@with_setup(setup_each())
def test_inrow_count_broken_vertical_stripes():
    expected_row_count=np.ones([5])
    p=patchExtractor.patchExtractor()
    dummy=np.zeros(np.shape(broken_vertical_stripes),'int32')
    N=p.cpp_calcPatches(broken_vertical_stripes,dummy)
    descriptors=np.zeros([6,N],'int32')
    p.cpp_getDescriptors(descriptors)
    
    for patchNo in np.arange(N):
        inRowCountVector=np.zeros([descriptors[4,patchNo]-descriptors[3,patchNo]+1],'int32')
        p.cpp_getInRowCount(int(patchNo),inRowCountVector)
        print('patchNo:{0}, {1}'.format(patchNo,inRowCountVector))
        np.testing.assert_equal(inRowCountVector,expected_row_count)

@with_setup(setup_each())
def test_inrow_count_horizontal_stripes():
    expected_row_count=np.ones([1])*20
    p=patchExtractor.patchExtractor()
    dummy=np.zeros(np.shape(horizontal_stripes),'int32')
    N=p.cpp_calcPatches(horizontal_stripes,dummy)
    descriptors=np.zeros([6,N],'int32')
    p.cpp_getDescriptors(descriptors)
    
    for patchNo in np.arange(N):
        inRowCountVector=np.zeros([descriptors[4,patchNo]-descriptors[3,patchNo]+1],'int32')
        p.cpp_getInRowCount(int(patchNo),inRowCountVector)
        print('patchNo:{0}, {1}'.format(patchNo,inRowCountVector))
        np.testing.assert_equal(inRowCountVector,expected_row_count)


@with_setup(setup_each())
def test_incol_count_broken_vertical_stripes():
    expected_col_count=np.ones(1)*5
    p=patchExtractor.patchExtractor()
    dummy=np.zeros(np.shape(broken_vertical_stripes),'int32')
    N=p.cpp_calcPatches(broken_vertical_stripes,dummy)
    descriptors=np.zeros([6,N],'int32')
    p.cpp_getDescriptors(descriptors)
    
    for patchNo in np.arange(N):
        inColCountVector=np.zeros([descriptors[2,patchNo]-descriptors[1,patchNo]+1],'int32')
        p.cpp_getInColCount(int(patchNo),inColCountVector)
        print('patchNo:{0}, {1}'.format(patchNo,inColCountVector))
        np.testing.assert_equal(inColCountVector,expected_col_count)

@with_setup(setup_each())
def test_incol_count_horizontal_stripes():
    expected_col_count=np.ones(20)
    p=patchExtractor.patchExtractor()
    dummy=np.zeros(np.shape(horizontal_stripes),'int32')
    N=p.cpp_calcPatches(horizontal_stripes,dummy)
    descriptors=np.zeros([6,N],'int32')
    p.cpp_getDescriptors(descriptors)
    
    for patchNo in np.arange(N):
        inColCountVector=np.zeros([descriptors[2,patchNo]-descriptors[1,patchNo]+1],'int32')
        p.cpp_getInColCount(int(patchNo),inColCountVector)
        print('patchNo:{0}, {1}'.format(patchNo,inColCountVector))
        np.testing.assert_equal(inColCountVector,expected_col_count)


@with_setup(setup_each())
def test_mask_extraction_horizontal_stripes():
    p=patchExtractor.patchExtractor()
    patches=np.zeros(np.shape(horizontal_stripes),'int32')
    patchesfrommask=np.zeros(np.shape(horizontal_stripes),'int32')
    N=p.cpp_calcPatches(horizontal_stripes,patches)
    
    for patchNo in np.arange(N):
        mask=np.zeros(np.shape(horizontal_stripes),'int32')
        p.cpp_getMasks(int(patchNo),mask)
        patchesfrommask[:,:]+=patchNo*mask
        print('patchNo:{0}, {1}'.format(int(patchNo),mask))
    np.testing.assert_equal(patchesfrommask,patches)
    
@with_setup(setup_each())
def test_mask_extraction_broken_vertical_stripes():
    p=patchExtractor.patchExtractor()
    patches=np.zeros(np.shape(broken_vertical_stripes),'int32')
    patchesfrommask=np.zeros(np.shape(broken_vertical_stripes),'int32')
    N=p.cpp_calcPatches(broken_vertical_stripes,patches)
    
    for patchNo in np.arange(N):
        mask=np.zeros(np.shape(broken_vertical_stripes),'int32')
        p.cpp_getMasks(int(patchNo),mask)
        patchesfrommask[:,:]+=patchNo*mask
        print('patchNo:{0}, {1}'.format(int(patchNo),mask))
    np.testing.assert_equal(patchesfrommask,patches)

@with_setup(setup_each())
def test_incoldistribution_broken_vertical_stripes():
    p=patchExtractor.patchExtractor()
    patches=np.zeros(np.shape(broken_vertical_stripes),'int32')
    N=p.cpp_calcPatches(broken_vertical_stripes,patches)

    descriptors=np.zeros([6,N],'int32')
    p.cpp_getDescriptors(descriptors)

    values=np.zeros(np.shape(broken_vertical_stripes),'double')
    values[:,:]=patches

    try:
        p.cpp_calcInPatchMeans(values)
    except RuntimeError as e:
       print(e)
       print('PyExc_RuntimeError')
    except ValueError as e:
       print(e)
       print('PyExc_ValueError')
    except Exception as e:
       print(e)
       print('Exception')

    for patchNo in np.arange(N):
        colVectorLength=p.getColsInPatch(int(patchNo))
        colVector=np.zeros(colVectorLength,'double')
        colVector_expected=np.ones(colVectorLength,'double')*patchNo
        p.cpp_getInColDist(int(patchNo), colVector)
        print('patchNo:{0}, ColsInPatch {1}, colVector{2}, colVector_expected:{3}'.format(int(patchNo),colVectorLength,colVector, colVector_expected))
        np.testing.assert_equal(colVector,colVector_expected)


@with_setup(setup_each())
def test_incoldistribution_horizontal_stripes():
    p=patchExtractor.patchExtractor()
    patches=np.zeros(np.shape(horizontal_stripes),'int32')
    N=p.cpp_calcPatches(horizontal_stripes,patches)

    descriptors=np.zeros([6,N],'int32')
    p.cpp_getDescriptors(descriptors)

    values=np.zeros(np.shape(horizontal_stripes),'double')
    values[:,:]=patches

    try:
        p.cpp_calcInPatchMeans(values)
    except RuntimeError as e:
       print(e)
       print('PyExc_RuntimeError')
    except ValueError as e:
       print(e)
       print('PyExc_ValueError')
    except Exception as e:
       print(e)
       print('Exception')

    for patchNo in np.arange(N):
        colVectorLength=p.getColsInPatch(int(patchNo))
        colVector=np.zeros(colVectorLength,'double')
        colVector_expected=np.ones(colVectorLength,'double')*patchNo
        p.cpp_getInColDist(int(patchNo), colVector)
        print('patchNo:{0}, ColsInPatch {1}, colVector{2}, colVector_expected:{3}'.format(int(patchNo),colVectorLength,colVector, colVector_expected))
        np.testing.assert_equal(colVector,colVector_expected)



@with_setup(setup_each())
def test_inrowdistribution_broken_vertical_stripes():
    p=patchExtractor.patchExtractor()
    patches=np.zeros(np.shape(broken_vertical_stripes),'int32')
    N=p.cpp_calcPatches(broken_vertical_stripes,patches)

    descriptors=np.zeros([6,N],'int32')
    p.cpp_getDescriptors(descriptors)

    values=np.zeros(np.shape(broken_vertical_stripes),'double')
    values[:,:]=patches

    try:
        p.cpp_calcInPatchMeans(values)
    except RuntimeError as e:
       print(e)
       print('PyExc_RuntimeError')
    except ValueError as e:
       print(e)
       print('PyExc_ValueError')
    except Exception as e:
       print(e)
       print('Exception')

    for patchNo in np.arange(N):
        rowVectorLength=p.getRowsInPatch(int(patchNo))
        rowVector=np.zeros(rowVectorLength,'double')
        rowVector_expected=np.ones(rowVectorLength,'double')*patchNo
        p.cpp_getInRowDist(int(patchNo), rowVector)
        print('patchNo:{0}, rowsInPatch {1}, rowVector{2}, rowVector_expected:{3}'.format(int(patchNo),rowVectorLength,rowVector, rowVector_expected))
        np.testing.assert_equal(rowVector,rowVector_expected)


@with_setup(setup_each())
def test_inrowdistribution_horizontal_stripes():
    p=patchExtractor.patchExtractor()
    patches=np.zeros(np.shape(horizontal_stripes),'int32')
    N=p.cpp_calcPatches(horizontal_stripes,patches)

    descriptors=np.zeros([6,N],'int32')
    p.cpp_getDescriptors(descriptors)

    values=np.zeros(np.shape(horizontal_stripes),'double')
    values[:,:]=patches

    try:
        p.cpp_calcInPatchMeans(values)
    except RuntimeError as e:
       print(e)
       print('PyExc_RuntimeError')
    except ValueError as e:
       print(e)
       print('PyExc_ValueError')
    except Exception as e:
       print(e)
       print('Exception')

    for patchNo in np.arange(N):
        rowVectorLength=p.getRowsInPatch(int(patchNo))
        rowVector=np.zeros(rowVectorLength,'double')
        rowVector_expected=np.ones(rowVectorLength,'double')*patchNo
        p.cpp_getInRowDist(int(patchNo), rowVector)
        print('patchNo:{0}, rowsInPatch {1}, rowVector{2}, rowVector_expected:{3}'.format(int(patchNo),rowVectorLength,rowVector, rowVector_expected))
        np.testing.assert_equal(rowVector,rowVector_expected)


@with_setup(setup_each())
def test_join_horizontal_stripes():
    joinMatrixExpected= np.array([[0,0],[1,1],[2,2],
        [3,3],[4,4],[5,5],[6,6],[7,7],[8,8],[9,9],[100,0],[101,1],
        [102,2],[103,3],[104,4],[105,5],[106,6],[107,7],[108,8],[109,9]])


    p=patchExtractor.patchExtractor()
    patches=np.zeros(np.shape(horizontal_stripes),'int32')
    tex_before=np.zeros([10],'int32')
    tex_before[:]=horizontal_stripes[:,5]
    tex_after=np.zeros([10],'int32')
    tex_after[:]=tex_before
    patch_before=np.zeros([10],'int32')
    patch_before[:]=horizontal_stripe_labels[:,5]
    patch_after=np.zeros([10],'int32')
    patch_after[:]=horizontal_stripe_labels[:,5]
    patch_after[:]+=100
    joinMatrix=np.zeros([20,2],'int32')
    
    #print('{0}, {1}'.format(patch_before,patch_after))
    validpatches=p.cpp_calcJoinMatrix(tex_before, tex_after, patch_before, patch_after, joinMatrix )
    #print('joinMatrix:{0}, validpatches:{1}'.format(joinMatrix[0:validpatches,:],validpatches))
    np.testing.assert_equal(joinMatrixExpected,joinMatrix)
