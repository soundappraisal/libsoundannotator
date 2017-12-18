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
import numpy                    as np
import libsoundannotator.streamboard as streamboard
import libsoundannotator.cpsp        as cpsp


from libsoundannotator.streamboard                import processor
from libsoundannotator.streamboard.continuity     import Continuity, processorAlignment

from libsoundannotator.cpsp.structureProcessor    import  structureProcessorCore
from libsoundannotator.cpsp.patchProcessor        import  patchProcessorCore

import os
import time

class PTN_Processor(processor.Processor):
    ''' 
    PTN_Processor: Class to calculate the average energy in a time-frequency 
    areas. Outputs pulse, tone, noise, and energy. Where pulse, tone 
    and noise are based on the tract features. 
    
    If only a subset of pulse, tone, noise, and energy is needed use 
    PartialPTN_Processor instead.
    
    Parameters: 
        Required:
            SampleRate                      sampling frequency in samples per second
        Required with default:  
            noofscales (100):               number of frequency channels on the incoming representation
            TfThreshold (60):               threshold for the vertical tract features
            TfSlope (0.2):                  slope at threshold of the sigmoidal threshold fucntion 
            TsThreshold (60):               threshold for the horizontal tract features
            TsSlope (0.2):                  slope at threshold of the sigmoidal threshold fucntion 
            split ([]):                     List of monotonically increasing integers indicating channels 
                                            at which TF-plane will be split in blocks, lower value is 
                                            included in block. Highest allowed value is noofscales. Channels 
                                            preceding first channel or following 
                                            last channel will discarded.
            blockwidth (1):                 blockwidth in seconds
            logBandmeans (True):            if true take the log off the average bandmeans or not
            normalize (False):              normalize pulse, tone and noise by energy in the block
            ptnreferencevalue (None):       potential correction value on the energy
            firstpublished (0):             processor restarts chunk numbering, the chunks 
                                            produced often have a lower publishing frequency as the incoming chunks
    
    
    '''
    requiredKeys=['E','f_tract','s_tract']
    intermediateKeys=['TfGate','TsGate','']
    featurenames=['pulse','tone','noise','energy']  # Functions in __init__ should not use this parameter so it can be overruled in the derived class.

    def __init__(self,boardConn, name,*args, **kwargs):
        super(PTN_Processor, self).__init__(boardConn, name,*args, **kwargs)
        self.requiredParameters('SampleRate')
        self.requiredParametersWithDefault(noofscales=100,
                            TfThreshold=60, TfSlope=0.2,
                            TsThreshold=60, TsSlope=0.2,
                            split=[],
                            blockwidth=1,  # output blockwidth in seconds.
                            logBandmeans=True, #log bandmeans or not
                            normalize=False,
                            ptnreferencevalue=None,
                            firstpublished=0,
                            )

        
        self.F_dB=10./np.log2(10.) # Conversion factor for going from energy to log energy in dB using log2
        self.TfThreshold=self.config['TfThreshold']
        self.TsThreshold=self.config['TsThreshold']
        self.TfSlope=self.config['TfSlope']
        self.TsSlope=self.config['TsSlope']

        self.fs=self.config['SampleRate']
        self.blockwidth=int(np.ceil(self.config['blockwidth']*self.config['SampleRate']))
        self.fs_out = 1./self.config['blockwidth']
        self.number=self.config['firstpublished']
        
        self.resetblockbuffer()

        if 'resultKeys' in self.config:
            self.resultKeys = self.config['resultKeys']


        self.noofbands=len(self.config['split'])-1
        
        self.resetfirstchunkinblock=True
        self.firstchunkinblock=None
        
    def prerun(self):
        self.setProcessorAlignments()
        super(PTN_Processor, self).prerun() 

  
    def getcontinuity(self):
        if self.firstchunkinblock is None:
            self.logger.error('getcontinuity called before stream was initialized')
            return Continuity.discontinuous
        else:
            return self.firstchunkinblock.continuity

    def getnumber(self):
        return self.number

    def getstarttime(self):
        return self.starttime

    def processData(self, data):

        # empty buffer if chunks are discontinuous
        if data.chunkcontinuity < Continuity.withprevious:
            self.logger.debug('Reset block buffer')
            self.resetblockbuffer()
            self.resetfirstchunkinblock=True
        
        if self.resetfirstchunkinblock: 
            self.firstchunkinblock=data
            self.resetfirstchunkinblock=False
        
        '''
            Merge incoming data and calculate Van Elburg-Andringa features.
        '''

        samples_available=list()
        for key in self.requiredKeys:
            noofnewsamples=np.shape(data.received[key].data)[1]
            noofoldsamples=np.shape(self.blockbuffer[key])[1]
            samples_available.append(noofnewsamples+noofoldsamples)
        samples_available=min(samples_available)

        noofblocks=int(np.floor((samples_available)/self.blockwidth))

        currentdata=dict()
        for key in self.requiredKeys:
            self.logger.info('key: {0} shape buffer: {1} shape input: {2}'.format(key,np.shape(self.blockbuffer[key]),np.shape(data.received[key].data)))
            currentdata[key]=np.concatenate((self.blockbuffer[key],data.received[key].data), axis=1)
            self.blockbuffer[key]=currentdata[key][:,noofblocks*self.blockwidth:]

        if( data.continuity == Continuity.withprevious):
            self.starttime=data.startTime- data.alignment.includedPast/data.received['E'].fs- noofoldsamples/data.received['E'].fs
        elif data.chunkcontinuity == Continuity.withprevious:
            self.starttime=data.startTime
        else:
            self.starttime=data.startTime + data.alignment.droppedAfterDiscontinuity/data.received['E'].fs



        if noofblocks <1:
            noofblocks=0
            ptne=None
        else:
            if self.noofbands >1 :
                ptnshape=(self.noofbands, noofblocks)
            else:
                ptnshape=(noofblocks)

            ptne=dict()

            for featurename in self.featurenames:
                ptne[featurename] = np.zeros(ptnshape)

            for blockindex in np.arange(noofblocks,dtype='int'):
                #timestamp= self.starttime+blockindex*self.blockwidth/data.received['E'].fs
                values=self.calcPTNFeatures(currentdata,noofblocks,blockindex)

                for featurename in self.featurenames:


                    if self.noofbands >1 :
                        ptne[featurename][:,blockindex] = values[featurename]
                    else:
                        ptne[featurename][blockindex] = values[featurename]

            for featurename in self.featurenames:
                self.logger.info('{0}: {1}'.format(featurename,ptne[featurename]))
            
            self.resetfirstchunkinblock=True
            
       
        return ptne

    def resetblockbuffer(self):
        self.blockbuffer=dict()
        for key in self.requiredKeys:
            self.blockbuffer[key]=np.zeros((self.config['noofscales'],0))
        
            

    def bandmeans(self, data, split, rangecompression=(lambda x:x),keeptime=False, normalization=None):
        splitdata=np.split(data,split)
        splitdata=splitdata[1:-1] # Throw away invalid first and last band
        bandmeans=[]


        for view in splitdata:
            if keeptime :
                viewmean=np.mean(view,axis=0)
            else:
                viewmean=np.mean(view)

            bandmeans.append(viewmean)

        bandmeans=np.array(bandmeans)

        if normalization is not None:
            bandmeans=bandmeans/normalization

        return rangecompression(bandmeans)



    def calcPTNFeatures(self,currentdata,noofblocks,blockindex):


        '''
            Take out one block of duration blockwidth*fs from both the energy and the tract features.
        '''
        E=currentdata['E'][:,blockindex*self.blockwidth:(blockindex+1)*self.blockwidth]
        Tf=currentdata['f_tract'][:,blockindex*self.blockwidth:(blockindex+1)*self.blockwidth]
        Ts=currentdata['s_tract'][:,blockindex*self.blockwidth:(blockindex+1)*self.blockwidth]

        assert(np.shape(E)==np.shape(Ts) and np.shape(E)==np.shape(Tf))

        '''
            Apply a soft threshold function to the tract features for later use as weight on the energy.
        '''
        TfGate=(1+np.tanh( (Tf-self.TfThreshold)*self.TfSlope ) )/2
        TsGate=(1+np.tanh( (Ts-self.TsThreshold)*self.TsSlope ) )/2

        '''
            Define a range compression function for use with the bandmeans function. This function will be applied to the bandmeans before bandmeans return the bandmeans values. The default is the identity function, in which case you get the real bandmeans.
        '''



        Em=self.bandmeans(E, self.config['split'])

        bandmeansarguments=dict()
        if self.config['logBandmeans']:
            bandmeansarguments['rangecompression']=(lambda x: self.F_dB*np.log2(x))
            Eo=bandmeansarguments['rangecompression'](Em)
        else:
            Eo=Em

        if self.config['normalize']:
            bandmeansarguments['normalization']=Em

        if self.config['ptnreferencevalue'] is not None:
            Eo=Eo-self.config['ptnreferencevalue']


        Po=self.bandmeans(E*TfGate, self.config['split'],**bandmeansarguments)
        To=self.bandmeans(E*TsGate, self.config['split'],**bandmeansarguments)
        No=self.bandmeans(E*(1-TfGate)*(1-TsGate), self.config['split'],**bandmeansarguments)


        return {'pulse':Po,'tone':To,'noise':No,'energy':Eo}


    def publish(self, data, continuity, starttime,number,generationTime, 
                    metadata=None, identifier=None):
        
        super(PTN_Processor, self).publish(data, self.getcontinuity(), self.getstarttime(),self.getnumber(),generationTime, 
                    metadata, identifier)
                    
        if data is not None:
            self.number += 1
            
            
    
    def getsamplerate(self,key):
         return self.fs_out
        
    def setProcessorAlignments(self):        
        ''' 
        setProcessorAlignments: set the dictionary self.processorAlignments. 
        
        '''
        self.processorAlignments=dict()
        
        for featureName in self.featurenames: 
            self.processorAlignments[featureName]=processorAlignment(fsampling=self.getsamplerate(featureName))

class PartialPTN_Processor(PTN_Processor):

    requiredKeys=[]
    intermediateKeys=[]
    featurenames=[]

    requiredKeyMapping={'energy':['E'],'pulse':['E','f_tract'],'tone':['E','s_tract'], 'noise':['E','f_tract','s_tract']}
    intermediateKeyMapping={'energy':[],'pulse':['TfGate'],'tone':['TsGate'], 'noise':['TfGate','TsGate']}

    def __init__(self,boardConn, name,*args, **kwargs):
        super(PartialPTN_Processor, self).__init__(boardConn, name,*args, **kwargs)
        self.requiredParameters('featurenames')
        self.featurenames=self.config['featurenames']

        for key in self.featurenames:
            self.requiredKeys=list(set(self.requiredKeys) | set(self.requiredKeyMapping[key]))
            self.intermediateKeys=list(set(self.intermediateKeys) | set(self.intermediateKeyMapping[key]))

        self.resetblockbuffer()

    def calcPTNFeatures(self,currentdata,noofblocks,blockindex):

        ptne=dict()

        if not self.featurenames:
            return ptne

        '''
            Take out one block of duration blockwidth*fs from both the energy and the tract features.
        '''
        E=currentdata['E'][:,blockindex*self.blockwidth:(blockindex+1)*self.blockwidth]

        if 'TfGate' in self.intermediateKeys:
            Tf=currentdata['f_tract'][:,blockindex*self.blockwidth:(blockindex+1)*self.blockwidth]
            '''
                Apply a soft threshold function to the tract features for later use as weight on the energy.
            '''
            TfGate=(1+np.tanh( (Tf-self.TfThreshold)*self.TfSlope ) )/2
            assert(np.shape(E)==np.shape(Tf) )

        if 'TsGate' in self.intermediateKeys:
            Ts=currentdata['s_tract'][:,blockindex*self.blockwidth:(blockindex+1)*self.blockwidth]
            '''
                Apply a soft threshold function to the tract features for later use as weight on the energy.
            '''
            TsGate=(1+np.tanh( (Ts-self.TsThreshold)*self.TsSlope ) )/2
            assert(np.shape(E)==np.shape(Ts))

        '''
            Define a range compression function for use with the bandmeans function. This function will be applied to the bandmeans before bandmeans return the bandmeans values. The default is the identity function, in which case you get the real bandmeans.
        '''


        if ('energy' in self.featurenames) or self.config['normalize']:
            Em=self.bandmeans(E, self.config['split'])

        bandmeansarguments=dict()
        if self.config['logBandmeans']:
            bandmeansarguments['rangecompression']=(lambda x: self.F_dB*np.log2(x))
            if 'energy' in self.featurenames:
                Eo=bandmeansarguments['rangecompression'](Em)
        elif 'energy' in self.featurenames:
            Eo=Em

        if self.config['normalize']:
            bandmeansarguments['normalization']=Em

        if (self.config['ptnreferencevalue'] is not None) and ('energy' in self.featurenames):
            Eo=Eo-self.config['ptnreferencevalue']

        if 'energy' in self.featurenames:
            ptne['energy']=Eo

        if 'pulse' in self.featurenames:
            Po=self.bandmeans(E*TfGate, self.config['split'],**bandmeansarguments)
            ptne['pulse']=Po

        if 'tone' in self.featurenames:
            To=self.bandmeans(E*TsGate, self.config['split'],**bandmeansarguments)
            ptne['tone']=To

        if 'noise' in self.featurenames:
            No=self.bandmeans(E*(1-TfGate)*(1-TsGate), self.config['split'],**bandmeansarguments)
            ptne['noise']=No


        return ptne


class MaxTract_Processor(PartialPTN_Processor):


    requiredKeyMapping={'energy':['E'],'pulse':['E','f_tract'],'tone':['E','s_tract'], 'noise':['E','f_tract','s_tract'],'tfmax':['f_tract'],'tsmax':['s_tract'],'tfmin':['f_tract'],'tsmin':['s_tract']}
    intermediateKeyMapping={'energy':[],'pulse':['TfGate'],'tone':['TsGate'], 'noise':['TfGate','TsGate'],'tfmax':[],'tsmax':[],'tfmin':[],'tsmin':[]}
    
    def bandmax(self, data, split,keeptime=False):
        splitdata=np.split(data,split)
        splitdata=splitdata[1:-1] # Throw away invalid first and last band
        bandmax=[]

        for view in splitdata:
            if keeptime :
                viewmax=np.max(view,axis=0)
            else:
                viewmax=np.max(view)
                
            bandmax.append(viewmax)
            
        bandmax=np.array(bandmax)


        return bandmax

    def bandmin(self, data, split,keeptime=False):
        splitdata=np.split(data,split)
        splitdata=splitdata[1:-1] # Throw away invalid first and last band
        bandmin=[]

        for view in splitdata:
            if keeptime :
                viewmin=np.min(view,axis=0)
            else:
                viewmin=np.min(view)
                
            bandmin.append(viewmin)
            
        bandmin=np.array(bandmin)


        return bandmin
        

    def calcPTNFeatures(self,currentdata,noofblocks,blockindex):
        
        ptne=super(MaxTract_Processor, self).calcPTNFeatures(currentdata,noofblocks,blockindex)
        
        bandmeansarguments=dict()

        if 'tfmax' in self.featurenames:
            Tf=currentdata['f_tract'][:,blockindex*self.blockwidth:(blockindex+1)*self.blockwidth]
            tfmax=self.bandmax(Tf, self.config['split'],**bandmeansarguments)
            ptne['tfmax']=tfmax

        if 'tsmax' in self.featurenames:
            Ts=currentdata['s_tract'][:,blockindex*self.blockwidth:(blockindex+1)*self.blockwidth]
            tsmax=self.bandmax(Ts, self.config['split'],**bandmeansarguments)
            ptne['tsmax']=tsmax

        if 'tfmin' in self.featurenames:
            Tf=currentdata['f_tract'][:,blockindex*self.blockwidth:(blockindex+1)*self.blockwidth]
            tfmin=self.bandmin(Tf, self.config['split'],**bandmeansarguments)
            ptne['tfmin']=tfmin

        if 'tsmin' in self.featurenames:
            Ts=currentdata['s_tract'][:,blockindex*self.blockwidth:(blockindex+1)*self.blockwidth]
            tsmin=self.bandmin(Ts, self.config['split'],**bandmeansarguments)
            ptne['tsmin']=tsmin

        return ptne
