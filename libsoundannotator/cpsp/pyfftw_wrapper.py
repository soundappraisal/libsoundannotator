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
import numpy as np


class fftw(object):
    
    def __init__(self):
        pass
        
    def importsingle(self):
        import fftw3f
        self.fftw=fftw3f

    def importdouble(self):
        import fftw3 
        self.fftw=fftw3 

    def fftw_plan(self):
        pass
         
    fftwtype={
        np.float32:importsingle,
        np.complex64:importsingle,
        np.float64:importdouble,
        np.complex128:importdouble, 
    }

    fftw_fdomain_type={
        importsingle:np.complex64,
        importdouble:np.complex128,
    }

    def importfftw(self,dTypeIn,dTypeOut):
        
        if not (dTypeIn in self.fftwtype and dTypeOut in self.fftwtype ):
            raise(TypeError('No fftw3 module available for the combination {0} with output {1}'.format(dTypeIn,dTypeOut) )) 
            
        if(self.fftwtype[dTypeIn]==self.fftwtype[dTypeOut]):
            self.fftwtype[dTypeIn](self)
        else:
            raise(TypeError('No fftw3 module available for the combination {0} with output {1}'.format(dTypeIn,dTypeOut) )) 

        return self.fftw_fdomain_type[self.fftwtype[dTypeIn]]
        

if __name__ == '__main__':
    myfftw=fftw()

    try:
        FDomainType=myfftw.importfftw(np.float32,np.float32)
        print('FDomainType={}'.format(FDomainType))
    except TypeError as t:
        print t


    try:
        FDomainType=myfftw.importfftw(np.float32,np.complex64)
        print('FDomainType={}'.format(FDomainType))
    except TypeError as t:
        print t


    try:
        FDomainType=myfftw.importfftw(np.float64,np.complex128)
        print('FDomainType={}'.format(FDomainType))
    except TypeError as t:
        print t
    
    try:
        myfftw.importfftw(np.float64,np.complex64)
        print('Error')
    except TypeError as t:
        print t
       
    try:
        myfftw.importfftw(np.int64,np.complex64)
        print('Error')
    except TypeError as t:
        print t
    
    FDomainType=myfftw.importfftw(np.float32,np.float32)
    print 'fftw_fdomain_type: {0}'.format(FDomainType)
    
