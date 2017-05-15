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
from libsoundannotator.cpsp import structureExtractor        
import numpy as np
import os



def constructor_test():
    myExtractor=structureExtractor.structureExtractor(False)
    assert(myExtractor)
    
def correlation_matrix_test():
    myExtractor=structureExtractor.structureExtractor(True)
    noofscales=5
    noofframes=6000
    myarray=np.random.randn(noofscales,noofframes)
    myarray[2,:]=myarray[1,:]-myarray[3,:]
    myarray[4,:]=-myarray[3,:]
    maxdelay=10
    myExtractor.initialize(myarray,maxdelay)
    
    corr=np.zeros((noofscales*noofscales, 2*maxdelay+1),'double')
    myExtractor.get_correlations(corr,True)
    
    # The correlation matrix should within the margin of numerical errors satisfy the following symmetry:
    #   corr(noofscales*(frame-1)+xframe,delay+maxdelay)= corr(noofscales*(xframe-1)+frame,maxdelay-delay)
    #  it should actually involve addition of the same numbers in the same order, 
    #  therefore the following test should pass
    for frame in np.arange(noofscales):
        for xframe in np.arange(frame+1):
            row1=corr[noofscales*frame+xframe,:]
            row2=np.flipud(corr[noofscales*xframe+frame,:])
            np.testing.assert_almost_equal(row1,row2)
            
    # All autocorrelations at zero lag should be one:
    #   corr(noofscales*(frame-1)+frame,maxdelay)==1
    for frame in np.arange(noofscales):
            result=corr[noofscales*frame+frame,maxdelay]
            expected=np.array([1])
            np.testing.assert_almost_equal(result,expected)
            
    # In the definition of our probing signal we introduced some dependencies, 
    # leading to more or less well defined cross correlations at zero lag:
    #     corr(noofscales*(frame-1)+xframe,maxdelay)
    #       frame       xframe          corr
    #       3           4               -1   
    frame=3
    xframe=4
    result=corr[noofscales*frame+xframe,maxdelay]
    expected=np.array([-1])
    np.testing.assert_almost_equal(result,expected)
    #       1           2                if(frame and thirdframe i.i.d.) approximately: sqrt(0.5)(1 - corr[noofscales*(frame-1)+thirdframe,maxdelay])    thirdframe=3
    frame=1
    xframe=2
    thirdframe=3
    result=corr[noofscales*frame+xframe,maxdelay]
    expected=np.array([np.sqrt(0.5)*(1 - corr[noofscales*(frame-1)+thirdframe,maxdelay])])
    np.testing.assert_approx_equal(result,expected,significant=1)
    #       2           3               if(xframe and thirdframe i.i.d.) approximately: -sqrt(0.5)(1 - corr[noofscales*(thirdframe-1)+xframe,maxdelay])   thirdframe=1   
    frame=2
    xframe=3
    thirdframe=1
    result=corr[noofscales*frame+xframe,maxdelay]
    expected=np.array([-np.sqrt(0.5)*(1 - corr[noofscales*(thirdframe-1)+xframe,maxdelay])])
    np.testing.assert_approx_equal(result,expected,significant=1)
   

def second_correlation_matrix_test():
    dirname = os.path.dirname(os.path.abspath(__file__))

    # Test against earlier matlab implementation results
    myExtractor=structureExtractor.structureExtractor(False)    
    myExtractor2=structureExtractor.structureExtractor(False)
    # Load log energy EB gammachirp processed noise signal from file
    filename=os.path.join(dirname,'initNoise_EB.txt')
    initNoise_EB=np.loadtxt(filename,dtype='double',skiprows=0)
    
    # Calculate correlations in gammachirp processed noise and compare to matlab output
    maxdelay=20
    noofscales=np.shape(initNoise_EB)[0]
    myExtractor.initialize(initNoise_EB,maxdelay)
    correlation_matrix=np.zeros((noofscales*noofscales, 2*maxdelay+1),'double')
    myExtractor.get_correlations(correlation_matrix,False)
    # ... load correlation_matrix as calculated by matlab for comparison
    filename=os.path.join(dirname,'initNoise_N.txt')
    initNoise_N=np.loadtxt(filename,dtype='double',skiprows=0)
    # ... and test for equality. 
    np.testing.assert_allclose(correlation_matrix,initNoise_N,rtol=1e-7,atol=1e-8)
    
    # Calculate pattern (P) and tract (B) features and compare to matlab 
    # result.
    # load log energy from file
    filename=os.path.join(dirname,'richWavSignal_EB.txt')
    EB=np.loadtxt(filename,dtype='double',skiprows=0)
    
    # Check wheteher EB is well formed
    condition = np.isinf(EB)
    EBhasinf=np.extract(condition,EB)
    assert(EBhasinf.size==0)
    
    

    texturetypes=('f','u','s','d')
    validscales={'f':(6,-7),'u':(9,-9),'s':(9,-9),'d':(9,-9)}
    
    for texturetype in texturetypes:
        # load pattern (P) and tract (B) features from file for texturetype type
        filename=os.path.join(dirname,'richWavSignal_B_{0}.txt'.format(texturetype))
        B=np.loadtxt(filename,dtype='double',skiprows=0)
        filename=os.path.join(dirname,'richWavSignal_P_{0}.txt'.format(texturetype))
        P=np.loadtxt(filename,dtype='double',skiprows=0)
        
        # calculate pattern (P) and tract (B) features from log energy for texturetype type
        pyB=np.zeros(np.shape(EB),dtype='double')
        pyP=np.zeros(np.shape(EB),dtype='double')
        myExtractor.calc_tract(EB,pyB,pyP,texturetype)
        # ... and test for approximate equality
        np.testing.assert_allclose(pyP[:,60:-60],P[:,60:-60],rtol=1e-7,atol=3e-8) 
        #np.testing.assert_allclose(pyB[:,60:-60],B[:,60:-60],rtol=1e-13,atol=1e-7)
        valids=validscales[texturetype]
        print('texturetype {0}'.format(texturetype))
        np.testing.assert_allclose(pyB[valids[0]:valids[1],60:-60],B[valids[0]:valids[1],60:-60],rtol=1e-13,atol=1e-7)

        # calculate pattern (P) feature from log energy for texturetype type
        pyP=np.zeros(np.shape(EB),dtype='double')
        myExtractor.calc_pattern(EB,pyP,texturetype)
        # ... and test for approximate equality
        np.testing.assert_allclose(pyP[:,60:-60],P[:,60:-60],rtol=1e-7,atol=1e-8)

        mean=np.zeros((noofscales ) )
        stddev=np.zeros((noofscales) )
        thresholdCrossings=np.zeros((2*noofscales,8),dtype='int32' )
        thresholdStatus=np.zeros((2*noofscales,2),dtype='int32' )
        interpolationDeltas=np.zeros((2*noofscales,2) )
        frameoffsets=np.zeros((2),dtype='int32' )
        scaleoffsets=np.zeros((2),dtype='int32' )
        
        # Test storing and restoring pas and texture configuration data:
        print('get_pattern_stats')
        myExtractor.get_pattern_stats(mean, stddev,
                                    thresholdCrossings, thresholdStatus, interpolationDeltas,
                                    frameoffsets, scaleoffsets,
                                    texturetype)
        
        myExtractor2.set_pattern_stats(noofscales, mean, stddev,
                                    thresholdCrossings, thresholdStatus, interpolationDeltas,
                                    frameoffsets, scaleoffsets,
                                    texturetype)
        
         # calculate pattern (P) feature from log energy for texturetype type
        pyP2=np.zeros(np.shape(EB),dtype='double')
        myExtractor2.calc_pattern(EB,pyP2,texturetype)
        # ... and test for approximate equality
        np.testing.assert_allclose(pyP2[:,60:-60],P[:,60:-60],rtol=1e-7,atol=1e-8)
        np.testing.assert_equal(pyP,pyP2)
        
        print('get_tract_stats')
        mean=np.zeros((noofscales ))
        stddev=np.zeros((noofscales ))
        areasizes=np.zeros((noofscales ),dtype='int32')
        contextAreas=np.zeros((noofscales,3*noofscales),dtype='int32')
        myExtractor.get_tract_stats(mean,stddev,areasizes,contextAreas,
                                    frameoffsets, scaleoffsets,texturetype)
        

        myExtractor2.set_tract_stats(noofscales, mean, stddev, areasizes, contextAreas,
                                    frameoffsets, scaleoffsets, texturetype)
        # calculate pattern (P) and tract (B) features from log energy for texturetype type
        pyB2=np.zeros(np.shape(EB),dtype='double')
        pyP2=np.zeros(np.shape(EB),dtype='double')
        myExtractor2.calc_tract(EB,pyB2,pyP2,texturetype)
        # ... and test for approximate equality
        np.testing.assert_allclose(pyP2,pyP,rtol=1e-7,atol=3e-8) 
        np.testing.assert_allclose(pyB2,pyB,rtol=1e-13,atol=1e-8)
        
        # Test whether context areas are equivalent 
        mean2=np.zeros((noofscales ))
        stddev2=np.zeros((noofscales ))
        areasizes2=np.zeros((noofscales ),dtype='int32')
        contextAreas2=np.zeros((noofscales,3*noofscales),dtype='int32')
        myExtractor2.get_tract_stats(mean2,stddev2,areasizes2,contextAreas2,
                                    frameoffsets, scaleoffsets,texturetype)
        np.testing.assert_equal(mean,mean2)
        np.testing.assert_equal(stddev,stddev2)
        np.testing.assert_equal(areasizes,areasizes2)
        np.testing.assert_equal(mean,mean2)
        
