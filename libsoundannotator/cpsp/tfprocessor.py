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
import numpy as np
import math
import sys
from oafilterbank_numpy import OAFilterbank

import time
import os
from xml.etree.ElementTree import ElementTree, Element, SubElement, Comment, tostring
import xml.etree.ElementTree as ET


pi = np.pi


class GCFilterBank(object):

    """ Gamma Chirp Filterbank """


    """
    This dictionary is the default configuration for the Gamma Chirp Filterbank
    It specifies all fields needed to create a GCFB. If the filterbank is changed
    in a way that makes additional parameters necessary, please add them here.


    Filter bank parameters:
    nseg:     number of segments
    fmin:     lowest frequency (Hz)
    fmax:     highest frequency (Hz)
    SampleRate:       sampling rate (Hz)
    desiredT: desired length of impulse response (seconds)

    Gamma chirp parameters (set to Andringa defaults):
    TODO: find decent descriptions for these parameters
    n:        gamma-chirp order
    B:        ???
    C:        ???
    ch:       ??? 

    """

    defaultGCFBConfig = {
        'nseg': 100,
        'fmin': 60,
        'fmax': 4000,
        'desiredT': 0.1,
        'SampleRate': 8000,
        'n': 4,
        'B': (2.02*0.35*0.1039*0.75),
        'C': (2.02*0.35*24.7),
        'ch': -3.7,
        'scale': 'loglin'
    }


    def __init__(self, *args):
        # Create a config dictionary
        self.config = dict()
        self.config['DataType'] = np.complex64
        
        # If no arguments are given, use default configuration
        if len(args) == 0:
            self.config = self.defaultGCFBConfig
        
        
        
        
        # Otherwise check if argument is a dictionary
        else:
            if type(args[0]) == dict:
                configDict = args[0]

                # For each parameter in the defaultconfig
                for parameter in self.defaultGCFBConfig:
                    # Check if there is an overriding value in the argument dictionary
                    if parameter in configDict:
                        self.config[parameter] = configDict[parameter]
                    else:
                        self.config[parameter] = self.defaultGCFBConfig[parameter]
            else:
                raise TypeError('Expected Dictionary, got {0}'.format(type(args[0])))

        # Will be set during filter calculation
        self.chirpLength = 0
        # Calculate the filterbank
        self.recalculate()

    def ERB_Scale(self,f):
        B = self.config['B']
        C = self.config['C']
        ERB_Value = np.log(B*f+C)
        return ERB_Value
    
    def ERB_Value2Freq(self,ERB_Value):
        B = self.config['B']
        C = self.config['C']
        freq=(np.exp(ERB_Value) -C)/B
        return freq
        
    def getFilterBank(self):
        """ Returns the filterbank """
        return self.h

    def getChirpLength(self):
        """ Returns the length of the impulse response of this
            this filterbank
        """
        return self.chirpLength

    def getNSeg(self):
        """ Returns the number of segments
            or the number of filters in the bank
        """
        return self.config['nseg']

    def setParameters(self, changeDict):
        """ Sets specific parameters
            TODO: Change __init__ to use this function
        """
        for par in changeDict:
            self.config[par] = changeDict[par]

    def getParameter(self, par):
        """ Gets the value of a specific parameter
            Returns None if the parameter is unknown
        """
        if par in self.config:
            return self.config[par]
        else:
            return None

    def recalculate(self):
        """ (re)calculate the GCFB """

        nseg = self.config['nseg']
        fmin = self.config['fmin']
        fmax = self.config['fmax']
        desiredT = self.config['desiredT']
        fs = self.config['SampleRate']
        n = self.config['n']
        B = self.config['B']
        C = self.config['C']
        ch = self.config['ch']

        # Length of gamma chirp in frames
        chirpLength = round(fs*desiredT)

        # tmax is real length of impulse response in seconds
        tmax = chirpLength / float(fs)

        # Define the time axis
        t = np.array(np.arange((1/float(fs)),tmax,(1/float(fs))), dtype=self.config['DataType'])
        len_t = len(t)

        # Define the frequency axis
        # Calculate positions on ERB scale
        
        if self.config['scale'] =='ERBScale':
            E_min=self.ERB_Scale(fmin)
            E_max=self.ERB_Scale(fmax)
            E_raw = np.array(np.linspace(E_min, E_max, nseg), dtype=self.config['DataType'])
            f_raw=self.ERB_Value2Freq(E_raw)
            
        if self.config['scale'] =='loglin':    
            f_raw = np.array(np.logspace(np.log10(fmin), np.log10(fmax), nseg), dtype=self.config['DataType'])
            
        len_f = len(f_raw)
        # Reverse order of f to put high frequencies first
        f = f_raw[sorted(range(len_f), reverse=False)]

        """ Now make numpy ndarray of impuls responses per cochlear segment
            The first dimension (0) is the filter time axis
            The second dimension (1) contains the cochlear segments
        """

        # Precalculate some constants to avoid calculating them in the for-loop
        print('Gammachirp parameters {0}, {1}, {2}'.format(B,C,nseg))
        F = B*f+C
        logTime = ch*np.log(t)
        bComplex = -B + 1j

        # Allocate memory space for the filter kernel
        h = np.empty([len_t, len_f], dtype=self.config['DataType'])

        # Create the filterbank for all segments
        # This is equivalent to the for-loop in GCFilterBankClean_init.m
        for (i,fi) in enumerate(f):
            hamp_cur= (t**(n-1)*np.exp(-2*pi*F[i]*t))
            exponential = np.exp(1j*((2*pi*fi*t)+(logTime))).T
            h_cur = hamp_cur*exponential
            #h[:,i] = h_cur / np.sqrt(sum(np.abs(hamp_cur)**2)) * fi/np.sqrt(fs) # Numerical equivalent of exact result below.
            h[:,i] = h_cur*np.sqrt((4*pi*F[i])**(2*n-1) / np.float(math.factorial(2*n-2))) *fi/fs
        
        self.f=np.real(f)
        self.h = h
        self.chirpLength = chirpLength
        return h,chirpLength



class GCFBProcessor(OAFilterbank):

    """ Overlap-and-add implementation of a
        Gamma Chirp Filter Processor
    """
    
    requiredKeys=['timeseries']
    
    def __init__(self,boardConn, name,*args, **kwargs):
        self.GCConfig=kwargs
        
        super(GCFBProcessor, self).__init__(boardConn, name, *args, **kwargs)
        self.requiredParameters('metadata')
        self.requiredParametersWithDefault(
            mode='EdB', 
            samplesPerFrame=5
        ) 
        self.mode=self.config['mode']
        self.script_started=self.config['metadata']['script_started']


        self.F_dB=20./np.log2(10.)  # Conversion factor for going from magnitude to log energy in dB using log2
        
        self.xmloutput=False
        if 'globalOutputPathModifier' in kwargs:
            self.PathModifier='{0}-{1}'.format(self.config['globalOutputPathModifier'],self.script_started)
            
            self.resultspath=os.path.join(self.config['baseOutputDir'],self.PathModifier)
            if not os.path.exists(self.resultspath):
                os.makedirs(self.resultspath)
            
            self.xmlmetafilename_relative='{0}_MetaData.xml'.format(self.name)
            self.xmlmetafilename=os.path.join(self.resultspath,self.xmlmetafilename_relative)
            self.xmloutput=True 
        
        self.offset=0

    def prerun(self):
        self.factory = GCFilterBank(self.GCConfig)
        self.filter_t = self.factory.getFilterBank()
        super(GCFBProcessor, self).prerun()
        if self.xmloutput:
            self.writexml()

    def writexml(self):
        xmlmetafile=open(self.xmlmetafilename,'w+')
        xmlmetaroot=Element('Gammachirp_parameters')
        xmlmetatree=ElementTree(xmlmetaroot)
        f_map   = SubElement(xmlmetaroot,'frequency_map')
        f_map.text=''.join(['{0:.2f}, '.format(frequency) for frequency in self.factory.f])
        
        nodelist=list()
        for key in ['nseg', 'fmin','fmax','SampleRate','n']:
            newnode = SubElement(xmlmetaroot,key)
            newnode.text ='{0:d}'.format(self.factory.config[key])
            nodelist.append(newnode)
        
        for key in ['samplesPerFrame']:
            newnode = SubElement(xmlmetaroot,key)
            newnode.text ='{0:d}'.format(self.config[key])
            nodelist.append(newnode)
        
        for key in ['desiredT','B','C','ch']:
            newnode = SubElement(xmlmetaroot,key)
            newnode.text ='{0:.2f}'.format(self.factory.config[key])
            nodelist.append(newnode)
        
        filteroverlap=SubElement(xmlmetaroot,'filteroverlap')
        filteroverlap.text='{0:d}'.format(self.nOverlap)
        
        blocklength=SubElement(xmlmetaroot,'blocklength')
        blocklength.text='{0:d}'.format(self.nBlock)
        
        xmlmetatree.write(xmlmetafile)
        xmlmetafile.close()
        
    def getMetaData(self):  
        return {'fMap':self.factory.f}
        
    def processData(self, data):
        """ Process a signal using the GCFB
            Valid mode:
                 'EdB': return log energy
                 'Amp': return response magnitude
            Returns tuple (EdB, Amp) if any other value than string 'Amp' or 'EdB' given.
        """
        # Assuming the first data source is audio
        audioChunk = data.received['timeseries']
        
        result=dict()
        if audioChunk is not None:
            self.logger.info('GCFBProcessor {0} processes data with startTime {1}' .format(self.name,self.currentTimeStamp))
            if not audioChunk.fs==self.config['SampleRate']:
                self.logger.warning('Input sample rate {0} is different from output SampleRate setting {1}'
                .format(audioChunk.fs, self.config['SampleRate']))
            self.logger.debug('Current Microphone time {0} with data length {1} '.format(audioChunk.startTime, np.shape(audioChunk.data)[0]))
            
            amplitudes = self.oafilter(audioChunk.data, audioChunk.continuity)
            
            thinned=np.absolute(amplitudes[:,self.offset::self.GCConfig['samplesPerFrame']])
            
            self.offset=np.remainder(self.offset-np.shape(amplitudes)[-1],self.GCConfig['samplesPerFrame'])
            
            
            result['E']=np.square(thinned)
            result['EdB']=self.calcEdB(thinned)
            
            return result
       
        # This is important to do, prevents trying to output.
        return None

    def calcEdB(self, thinned):
        
        return self.F_dB*np.log2(thinned)

    def getsamplerate(self,key):
        return self.config['SampleRate']/self.GCConfig['samplesPerFrame']