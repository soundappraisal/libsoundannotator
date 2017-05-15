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
# -*- coding: u8 -*-
import scipy as sp
import numpy as np
import numpy.fft as fft
import libsoundannotator.streamboard as streamboard


from libsoundannotator.streamboard               import processor
from libsoundannotator.streamboard.continuity    import Continuity

import scipy.signal as sig
import sys
"""

        Overlap-and-add filter implemented as an streamboard processor
        
"""
class OAFilterbank(processor.Processor):
    """ Overlap and add filter implementation. Can be used for arbitrary
        filters.
    """
   

    
    
    def __init__(self,boardConn, name,*args, **kwargs):
        """ 
            Subclasses need to define:
        
            filter_t = vector of filter coefficients

            filter_t can be a 2D vector in which case the first dimension is
            assumed to be the time dimension

            blocklength = desired length of a block (not guaranteed to
            be the real length due to optimization)
        """
        super(OAFilterbank, self).__init__(boardConn, name,*args, **kwargs)
        self.requiredParameters('SampleRate')
        self.requiredParametersWithDefault(TargetLatency=0.2, DataType=np.complex64)
        self.fs=self.config['SampleRate']
        self.targetlatency=self.config['TargetLatency']
        
    def prerun(self):
        super(OAFilterbank, self).prerun()
        self.initialize()
        
    def initialize(self):
        filter_t=self.filter_t
        self.responseLength = np.shape(filter_t)[0]
        self.nOverlap = self.responseLength - 1
        
    
        if(2*self.nOverlap<self.targetlatency):
            n=np.ceil(np.log2(self.targetlatency*self.fs+self.nOverlap))-1
        else:
            n=np.ceil(np.log2(self.targetlatency*self.fs+self.nOverlap))
            
        self.nfft = int(2**n)
        self.nBlock = self.nfft - self.nOverlap
        
        if len(np.shape(filter_t))==1:
            self.nseg = 1
            self.kernelZ = fft.fft(filter_t,self.nfft)
            self.overlap = np.empty([self.nOverlap, ], dtype=self.config['DataType'])
            self.oafilter = self.process1D
            
        elif len(np.shape(filter_t)) == 2:
            self.nseg = np.shape(filter_t)[1]
            self.kernelZ = fft.fft(filter_t,self.nfft,0)
            self.overlap = np.empty([self.nOverlap, self.nseg], dtype=self.config['DataType'])
            self.oafilter = self.process2D
        else: # len(np.shape(filter_t)) > 2:
            raise ValueError('Input filter should be a 1D or 2D vector')
        self.firstBlock = True

    def reset(self):
        self.logger.info('{0}:Reset OAFilter buffer'.format(self.name))
        if len(np.shape(self.filter_t))==1:
            self.overlap = np.zeros([self.nOverlap, ], dtype=self.config['DataType'])
        elif len(np.shape(self.filter_t)) == 2:
            self.overlap = np.zeros([self.nOverlap, self.nseg], dtype=self.config['DataType'])
        else: # len(np.shape(filter_t)) > 2:
            raise ValueError('Input filter should be a 1D or 2D vector')
        self.firstBlock = True

    def process1D(self,signal,continuity):
        """ This is the overlap-and-add implementation for 2D filters
        """
        startReadingAt = 0
        startWrite = 0
        
        discardFirstBlock= continuity < Continuity.withprevious
        
        # Length of valid convolution is len(signal) - (len(response) - 1)
        if discardFirstBlock:
            self.reset()
            result = np.empty([len(signal)-self.nOverlap,], dtype=self.config['DataType'])
        else:
            result = np.empty([len(signal),], dtype=self.config['DataType'])
        

        
        while startReadingAt < len(signal):
            stopReadingBefore = min(startReadingAt+self.nBlock, len(signal))

            currentBlockLength = stopReadingBefore-startReadingAt

            # Read new samples and bring them to Z-domain
            x = np.array(signal[startReadingAt:stopReadingBefore], dtype=self.config['DataType'])
            X = fft.fft(x,self.nfft)

            # Convolve with kernelZ
            y = fft.ifft(X*self.kernelZ)
            y[0:self.nOverlap]+=self.overlap
            

            """ In the first block we discard the startOverlap, write the
                validProcessed to result. Every next block add the saved
                overlap in self.overlap to the startoverlap and write this sum
                together with validProcessed to result.
            """

            if discardFirstBlock:
                result[startWrite:startWrite+currentBlockLength-self.nOverlap] = y[self.nOverlap:currentBlockLength]
            else:
                result[startWrite:startWrite+currentBlockLength] =  y[0:currentBlockLength]
                
                     
            self.overlap = y[currentBlockLength:currentBlockLength+self.nOverlap]

            startWrite += currentBlockLength
            startReadingAt = stopReadingBefore

            if discardFirstBlock:
                startWrite -= self.nOverlap
                discardFirstBlock = False
            
        return result
    
    
     


    def process2D(self,signal,continuity):
        """ This is the overlap-and-add implementation for 2D filters
        """

        startReadingAt = 0
        startWrite = 0
        discardFirstBlock = continuity < Continuity.withprevious
       
        
        # Length of valid convolution is len(signal) - (len(response) - 1)
        if discardFirstBlock:
            self.reset()
            result = np.empty([self.nseg,len(signal)-self.nOverlap], dtype=self.config['DataType'])
        else:
            result = np.empty([self.nseg,len(signal)], dtype=self.config['DataType'])

        while startReadingAt < len(signal):
            stopReadingBefore = min(startReadingAt+self.nBlock, len(signal))

            currentBlockLength = stopReadingBefore-startReadingAt
            
            # Read new samples and bring them to Z-domain
            x = np.array(signal[startReadingAt:stopReadingBefore], dtype=self.config['DataType'])
            X = fft.fft(x,self.nfft,axis=0)

            # Convolve with kernelZ
            for seg in range(self.nseg):
                y = fft.ifft(X*self.kernelZ[:,seg])
                
                # Add overlap to initial part
                y[0:self.nOverlap]+=self.overlap[:,seg]

                """ In the first block we discard the startOverlap, write the
                    validProcessed to result. Every next block add the saved
                    overlap in self.overlap to the startoverlap and write this sum
                    together with validProcessed to result.
                """

                if discardFirstBlock:
                    result[seg,startWrite:startWrite+currentBlockLength-self.nOverlap] = y[self.nOverlap:currentBlockLength]
                else:
                    result[seg, startWrite:startWrite+currentBlockLength] = y[0:currentBlockLength]
                        
                self.overlap[:,seg] = y[currentBlockLength:currentBlockLength+self.nOverlap]
                  
            startWrite += currentBlockLength
            startReadingAt = stopReadingBefore

            if discardFirstBlock:
                startWrite -= self.nOverlap
                discardFirstBlock = False
        
        return result



class Resampler(OAFilterbank):
    
    requiredKeys=['timeseries']
    def __init__(self,boardConn, name, *args, **kwargs):
        self.openResampler=False
        super(Resampler, self).__init__(boardConn, name, *args, **kwargs)
        #self.logger.info('Resampler initialization start')
        

        self.requiredParametersWithDefault(
            KaiserBeta=5,
            FilterLength=60,
            DecimateFactor=5
        )

        self.config['OutputSampleRate'] = self.config['SampleRate']/float(self.config['DecimateFactor'])
        # Create a low-pass filter
        normalizedCutoff = (float(self.config['OutputSampleRate']))/float(self.config['SampleRate'])
        self.filter_t = sig.firwin(self.config['FilterLength'],normalizedCutoff,None,('kaiser',self.config['KaiserBeta']))
        #self.logger.info('Resampler initialization done')
        self.offset=0

    def processData(self, inputs):
        if(not self.openResampler and  (len(self.subscriptions) > 0 or isinstance(self.config['network'],dict))):
            self.openResampler=True
        
        if(self.openResampler):
            data=dict()
            soundData = inputs.received['timeseries']
            if not soundData==None:
                if not soundData.fs == self.config['SampleRate']:
                    self.logger.warning(
                    'Actual input sample rate {0} is different from set input sample rate {1}'
                    .format(soundData.fs, self.config['SampleRate']))
                lowpassFiltered = self.oafilter(soundData.data,soundData.continuity)
                data['timeseries']=self.decimate(lowpassFiltered,self.config['DecimateFactor'])
                self.logger.info('Publish resampled data, number: {0}'.format(soundData.number))
                return data
        return None
    
    def getsamplerate(self,key):
        return self.config['OutputSampleRate']
    
    def sample_up( self,signal, upfactor):

        if(not isinstance(signal,np.ndarray)):
            raise SyntaxError, 'First argument: Input signals not formatted as a numpy.ndarray'
            
        if(not isinstance( upfactor,(int,long))):
            raise SyntaxError, 'Second argument: Upsampling factor is not an integer'
            
        s=list(np.shape(signal))
        
        if(len(s)>2):
            raise SyntaxError, 'First argument: Dimensionality of input signal exceeds 2'
            
        s[-1]=(upfactor)*s[-1]
        
        upsampledsignal=  np.zeros(s)  
        if(len(s)==1):
            upsampledsignal[slice(None,None,upfactor)]=signal
        else:
            upsampledsignal[:,slice(None,None,upfactor)]=signal
        
        return upsampledsignal
        
    def decimate(self,signal,downfactor):

        if(not isinstance(signal,np.ndarray)):
            raise SyntaxError, 'First argument: Input signal is not a numpy.ndarray'

        if(not isinstance( downfactor,(int,long))):
            raise SyntaxError, 'Second argument: Downsampling factor is not an integer'

        s=np.shape(signal)
        
        if(len(s)>2):
            raise SyntaxError, 'First argument: Dimensionality of input signal exceeds 2'

        if(len(s)==1):
            downsampledsignal=signal[self.offset::downfactor]
        else:
            downsampledsignal=signal[:,self.offset::downfactor]
            
        self.offset=np.remainder(self.offset-s[-1],downfactor)
        return downsampledsignal      








