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
import libsoundannotator.cpsp as cpsp

from  libsoundannotator.cpsp.patchProcessor import joinScaleDistributions, Patch
import numpy as np 

def test_discontinuous_merge():
    dist1=np.arange(10)*0.1
    dist2=np.arange(15)*0.4
    range1=np.array([12,21])
    range2=np.array([33,47])
    weights1=np.arange(10)+1
    weights2=np.arange(15)+1
    
    newdist_expected=np.zeros([47-12+1])
    newdist_expected[0:10]=dist1
    newdist_expected[-15:]=dist2
    
    newrange_expected=np.array([12,47])
    
    newweight_expected=np.zeros([47-12+1])
    newweight_expected[0:10]=weights1
    newweight_expected[-15:]=weights2
    
    newdist,  newweights=joinScaleDistributions(dist1, dist2, range1, range2, weights1, weights2 )
    
    np.testing.assert_almost_equal(newdist_expected,newdist)
    #np.testing.assert_equal(newrange_expected,newrange)
    np.testing.assert_equal(newweight_expected,newweights)
    
    
def test_continuous_merge():
    dist1=np.arange(10)*0.1
    dist2=np.arange(15)*0.4
    range1=np.array([12,21])
    range2=np.array([22,36])
    weights1=np.arange(10)+1
    weights2=np.arange(15)+1
    
    newdist_expected=np.zeros([36-12+1])
    newdist_expected[0:10]=dist1
    newdist_expected[-15:]=dist2
    
    newrange_expected=np.array([12,36])
    
    newweight_expected=np.zeros([36-12+1])
    newweight_expected[0:10]=weights1
    newweight_expected[-15:]=weights2
    
    newdist,  newweights=joinScaleDistributions(dist1, dist2, range1, range2, weights1, weights2 )
    
    np.testing.assert_almost_equal(newdist_expected,newdist)
    #np.testing.assert_equal(newrange_expected,newrange)
    np.testing.assert_equal(newweight_expected,newweights)

   
def test_discontinuous_patch_merge_simple():
    s_range1=np.array([100,111])
    t_range1=np.array([12,17])
    level=33
    
    s_weights1=np.arange(s_range1[1]-s_range1[0]+1,dtype='int32')+1
    t_weights1=np.ones([t_range1[1]-t_range1[0]+1],'int32')
    t_weights1[-1]=np.sum(s_weights1)-np.sum(t_weights1)+t_weights1[-1]
    
    
    s_dist1=np.arange(s_range1[1]-s_range1[0]+1)*0.1
    t_dist1=np.arange(t_range1[1]-t_range1[0]+1)*0.1
    
    s_range2=np.array([10,26])
    t_range2=np.array([12,17])
    level=33
    
    s_weights2=np.arange(s_range2[1]-s_range2[0]+1,dtype='int32')+1
    t_weights2=np.ones([t_range2[1]-t_range2[0]+1],'int32')
    t_weights2[-1]=np.sum(s_weights2)-np.sum(t_weights2)+t_weights2[-1]
    
    s_dist2=np.arange(s_range2[1]-s_range2[0]+1)*0.1
    t_dist2=np.arange(t_range2[1]-t_range2[0]+1)*0.1

    p1=Patch(   level, t_range1[0], t_range1[1] , s_range1[0], s_range1[1] , 
                np.sum(s_weights1),samplerate=44100,chunknumber=42,
                t_offset=1)
    p1.set_inFrameCount(t_weights1)
    p1.set_inFrameExtrema(t_weights1,t_weights1)
    p1.set_inScaleCount(s_weights1)
    p1.set_inScaleExtrema(s_weights1,s_weights1)
    print('Patch 1: {0}'.format(p1))
    
    p2=Patch(   level, t_range2[0], t_range2[1] , s_range2[0], s_range2[1] , 
                np.sum(s_weights2) ,samplerate=44100,chunknumber=42,
                t_offset=1)
    p2.set_inFrameCount(t_weights2)
    p2.set_inFrameExtrema(t_weights2,t_weights2)
    p2.set_inScaleCount(s_weights2)
    p2.set_inScaleExtrema(s_weights2,s_weights2)
    
    
    print('Patch 2: {0}'.format(p2))
    
    p1.merge(p2)
    print('Patch merged: {0}'.format(p1))
    inScaleCountExpected=np.zeros([111-10+1])
    inScaleCountExpected[:s_weights2.shape[0]]=s_weights2
    inScaleCountExpected[-s_weights1.shape[0]:]=s_weights1
    np.testing.assert_equal(inScaleCountExpected,p1.inScaleCount)
    
    inFrameCountExpected=np.zeros([17-12+1])
    inFrameCountExpected[:]+=t_weights2
    inFrameCountExpected[:]+=t_weights1
    np.testing.assert_equal(inFrameCountExpected,p1.inFrameCount)

   
def test_discontinuous_patch_merge_distribution():
    s_range1=np.array([100,111])
    t_range1=np.array([12,17])
    level=33
    
    s_weights1=np.arange(s_range1[1]-s_range1[0]+1,dtype='int32')+1
    t_weights1=np.ones([t_range1[1]-t_range1[0]+1],'int32')
    t_weights1[-1]=np.sum(s_weights1)-np.sum(t_weights1)+t_weights1[-1]
    
    
    s_dist1=np.arange(s_range1[1]-s_range1[0]+1)*0.1
    t_dist1=np.arange(t_range1[1]-t_range1[0]+1)*0.1
    
    s_range2=np.array([10,26])
    t_range2=np.array([12,17])
    level=33
    
    s_weights2=np.arange(s_range2[1]-s_range2[0]+1,dtype='int32')+1
    t_weights2=np.ones([t_range2[1]-t_range2[0]+1],'int32')
    t_weights2[-1]=np.sum(s_weights2)-np.sum(t_weights2)+t_weights2[-1]
    
    s_dist2=np.arange(s_range2[1]-s_range2[0]+1)*0.1
    t_dist2=np.arange(t_range2[1]-t_range2[0]+1)*0.1

    p1=Patch(   level, t_range1[0], t_range1[1] , s_range1[0], s_range1[1] , 
                np.sum(s_weights1),samplerate=44100,chunknumber=42,
                t_offset=1)
    p1.set_inFrameCount(t_weights1)
    p1.set_inFrameExtrema(t_weights1,t_weights1)
    p1.set_inScaleCount(s_weights1)
    p1.set_inScaleExtrema(s_weights1,s_weights1)
    p1.set_inFrameDistribution('dist',t_dist1)
    p1.set_inScaleDistribution('dist',s_dist1)
    print('Patch 1: {0}'.format(p1))
    
    p2=Patch(   level, t_range2[0], t_range2[1] , s_range2[0], s_range2[1] , 
                np.sum(s_weights2) ,samplerate=44100,chunknumber=42,
                t_offset=1)
    p2.set_inFrameCount(t_weights2)
    p2.set_inFrameExtrema(t_weights2,t_weights2)
    p2.set_inScaleExtrema(s_weights2,s_weights2)
    p2.set_inScaleCount(s_weights2)
    p2.set_inFrameDistribution('dist',t_dist2)
    p2.set_inScaleDistribution('dist',s_dist2)
    print('Patch 2: {0}'.format(p2))
    
    p1.merge(p2)
    print('Patch merged: {0}'.format(p1))
    inScaleCountExpected=np.zeros([111-10+1])
    inScaleCountExpected[:s_weights2.shape[0]]=s_weights2
    inScaleCountExpected[-s_weights1.shape[0]:]=s_weights1
    np.testing.assert_equal(inScaleCountExpected,p1.inScaleCount)
    
    inFrameCountExpected=np.zeros([17-12+1])
    inFrameCountExpected[:]+=t_weights2
    inFrameCountExpected[:]+=t_weights1
    np.testing.assert_equal(inFrameCountExpected,p1.inFrameCount)  
    
    s_distExpected=np.zeros([111-10+1])
    s_distExpected[:s_weights2.shape[0]]=s_dist2
    s_distExpected[-s_weights1.shape[0]:]=s_dist1
    print('inScaleDistributions: {0}'.format(p1.inScaleDistributions))
    print('inFrameDistributions p1: {0}, weights: {1}'.format(p1.inFrameDistributions,p1.inFrameCount ))
    print('inFrameDistributions p2: {0}, weights: {1}'.format(p2.inFrameDistributions,p2.inFrameCount ))
    
    np.testing.assert_almost_equal(s_distExpected,p1.inScaleDistributions['dist']) 
    
    t_distExpected=np.zeros([17-12+1])
    t_distExpected[:]+=t_dist2*t_weights2
    t_distExpected[:]+=t_dist1*t_weights1
    expected_t_weights=t_weights1+t_weights2
    t_distExpected[:]=t_distExpected/expected_t_weights
    np.testing.assert_almost_equal(t_distExpected,p1.inFrameDistributions['dist']) 
