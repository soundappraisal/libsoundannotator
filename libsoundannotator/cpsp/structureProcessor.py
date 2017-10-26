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

from libsoundannotator.streamboard.processor  import Processor, Continuity
from libsoundannotator.streamboard.continuity import Continuity, chunkAlignment, processorAlignment

import structureExtractor as structureExtractor 
import pickle

class patternCache(object):
    def __init__(self):
        self.noofscales=None
        self.mean=None
        self.stddev=None
        self.thresholdCrossings=None
        self.thresholdStatus=None
        self.interpolationDeltas=None
        self.frameoffsets=None
        self.scaleoffsets=None
        self.textureType=None
    

    
class textureCache(object):
    def __init__(self):
        self.noofscales=None
        self.mean=None
        self.stddev=None
        self.areasizes=None
        self.contextAreas=None
        self.textureType=None
        self.frameoffsets=np.zeros((2),dtype='int32' )
        self.scaleoffsets=np.zeros((2),dtype='int32' )


class structureCache(object):
    def __init__(self,p,t):
        self.pattern=p
        self.texture=t
    
class structureProcessorCore(object):
    allowedTextureTypes=('f','u','s','d')
    senderKeysT={'f':'f_tract','u':'u_tract','s':'s_tract','d':'d_tract'}
    senderKeysP={'f':'f_pattern','u':'u_pattern','s':'s_pattern','d':'d_pattern'}
    
    
    def __init__(self,*args, **kwargs):
        self.textureTypes=list()
        self.config=dict()
        
        
        self.config['noofscales']=kwargs['noofscales']
        self.config['maxdelay']=kwargs['maxdelay']
        
        self.logger= kwargs['logger']
        self.name  = kwargs['name']
        
        if 'textureTypes' in kwargs:
            for textureType in kwargs['textureTypes']:
                if  textureType in self.allowedTextureTypes:
                    self.textureTypes.append(textureType)
                else:
                    self.logger.error('textureType: {0} is not defined allowed texture types are: [1}'.format(textureType,self.allowedTextureTypes))
        else:
             self.textureTypes=self.allowedTextureTypes
             
        if 'cachename' in kwargs:
            self.cachename=kwargs['cachename']
        else:
            self.cachename=self.name
            
        self.logger.debug('Processor: {0}, Cache:{1}'.format(self.name,self.cachename))
        
    def prerun(self):
        self.extractor=structureExtractor.structureExtractor(False)
        self.frameoffsets=dict()
        self.scaleoffsets=dict()
        self.remainder=dict()
        for textureType in self.textureTypes:
            self.remainder[textureType]=np.zeros((self.config['noofscales'],1))
        self.initFromCache()
            
    def initFromCache(self):
        filename = '{0}.cache'.format(self.cachename)
        fileobj = open(filename, 'rb')
        cache=pickle.load(fileobj)
        for textureType in self.textureTypes:
            p=cache[textureType].pattern
            t=cache[textureType].texture
            
            self.logger.info('Get pattern and tract parameters from cache: {0} for textureType {1}'.format(p, textureType))
            self.logger.info('p.frameoffsets: {0}'.format(p.frameoffsets))
            self.logger.info('p.scaleoffsets: {0}'.format(p.scaleoffsets))
            self.logger.info('t.frameoffsets: {0}'.format(t.frameoffsets))
            self.logger.info('t.scaleoffsets: {0}'.format(t.scaleoffsets))
             
            self.extractor.set_pattern_stats(p.noofscales, p.mean, p.stddev,
                                    p.thresholdCrossings, p.thresholdStatus, p.interpolationDeltas,
                                    p.frameoffsets, p.scaleoffsets,
                                    textureType)
            self.extractor.set_tract_stats(t.noofscales, t.mean, t.stddev,
                                           t.areasizes, t.contextAreas,
                                           t.frameoffsets, t.scaleoffsets,
                                           textureType)
                                           
            self.frameoffsets[textureType]=t.frameoffsets
            self.scaleoffsets[textureType]=t.scaleoffsets
            
           

    def processData(self, data):
        # Assuming the first data source is EdB
        if (data.received['TSRep'] is None):
             # This is important to do, prevents empty output publication.
            return None
            
        
        result=dict()
        
        # Get data and merge with history when necessary
        chunk=data.received['TSRep']
        
        
        for textureType in self.textureTypes:
            # merge currentData with textureType dependent remainder
            currentData=chunk.data
            self.logger.info('Received chunk with continuity {0}'.format(chunk.continuity))
            if(chunk.continuity >= Continuity.withprevious):
                currentData=np.concatenate((self.remainder[textureType],currentData), axis=1)
                
            # Get some memory for  C++ module to write in
            texture=np.zeros(np.shape( currentData),dtype='double')
            pattern=np.zeros(np.shape( currentData),dtype='double')
            self.logger.info('Currentdata shape: {0}, continuity: {1}'.format(np.shape(currentData),chunk.continuity))
        
            # ... and call the C++ module to get pattern and tract values
            self.extractor.calc_tract(currentData,texture,pattern,textureType)
            
            
            frameoffsets=self.frameoffsets[textureType]
            self.logger.info('textureType: {0}, frameoffsets: {1}, scaleoffsets: {2}, texture shape: {3}'.format(textureType,frameoffsets,self.scaleoffsets[textureType], np.shape(texture)))
            self.remainder[textureType]=currentData[:, -frameoffsets[0]-frameoffsets[1]:] 
            
            result[self.senderKeysT[textureType]]=texture[:,frameoffsets[0]:-frameoffsets[1]]
            result[self.senderKeysP[textureType]]=pattern[:,frameoffsets[0]:-frameoffsets[1]]
            
        return result
            
 

class structureProcessor(Processor):
    requiredKeys=['TSRep']
    def __init__(self,boardConn, name,*args, **kwargs):
        super(structureProcessor, self).__init__(boardConn, name,*args, **kwargs)
        self.requiredParameters('SampleRate')
        self.requiredParametersWithDefault(noofscales=100,maxdelay=20)
        self.args=args
        self.kwargs=kwargs
        self.kwargs['noofscales']=self.config['noofscales']
        self.kwargs['maxdelay']=self.config['maxdelay']
        self.samplerate=self.config['SampleRate']
        
    def prerun(self):
        self.prerunsuper()
        self.kwargs['logger']=self.logger
        self.kwargs['name']=self.name
        self.structureProcessorCore=structureProcessorCore(*self.args,**self.kwargs)
        self.structureProcessorCore.prerun()
        self.setProcessorAlignments()

    def prerunsuper(self):
        super(structureProcessor, self).prerun()
        
    def processData(self, data):
        return self.structureProcessorCore.processData(data)

    
    def getsamplerate(self,key):
         return self.samplerate
         
    def setProcessorAlignments(self):
        self.processorAlignments=dict()
        for textureType in self.structureProcessorCore.textureTypes:
            
                                           
            frameoffsets=self.structureProcessorCore.frameoffsets[textureType]
            scaleoffsets=self.structureProcessorCore.scaleoffsets[textureType]

            # Calculate and store alignment parameters, temporal alignment between 
            # pattern and tract values are forced to be the same.
            # Frameoffsets and scaleoffsets are defined in textureCalculator.cpp
            #       myMargins.firstframe_offset=frameoffsets[0];
            #       myMargins.lastframe_offset=frameoffsets[1];
            #       myMargins.firstscale_offset=scaleoffsets[0];
            #       myMargins.lastscale_offset=scaleoffsets[1];
            
            
            droppedAfterDiscontinuity=frameoffsets[0]
            includedPast=frameoffsets[1]
                         
            invalidSmallScales=scaleoffsets[0]
            invalidLargeScales=scaleoffsets[1]
            
            self.processorAlignments[self.structureProcessorCore.senderKeysT[textureType]]=processorAlignment(
                invalidSmallScales=invalidSmallScales, 
                invalidLargeScales=invalidLargeScales,
                includedPast=includedPast, 
                droppedAfterDiscontinuity=droppedAfterDiscontinuity,
                fsampling=self.getsamplerate(self.structureProcessorCore.senderKeysP[textureType])
            )
            
            invalidLargeScales=scaleoffsets[1]
            invalidSmallScales=scaleoffsets[0]
            self.processorAlignments[self.structureProcessorCore.senderKeysP[textureType]]=processorAlignment(
                invalidSmallScales=invalidSmallScales, 
                invalidLargeScales=invalidLargeScales,
                includedPast=includedPast, 
                droppedAfterDiscontinuity=droppedAfterDiscontinuity, 
                fsampling=self.getsamplerate(self.structureProcessorCore.senderKeysP[textureType])
            )


class structureProcessorCalibratorCore(structureProcessorCore):
    
    def __init__(self,*args, **kwargs):
        super(structureProcessorCalibratorCore, self).__init__(*args, **kwargs)
        self.logger.info('self.config[noofscales]: {0}   self.config[maxdelay]: {1}'.format(self.config['noofscales'],self.config['maxdelay']))

        
    def prerun(self):
        self.extractor=structureExtractor.structureExtractor(False)
              
    def createCache(self):
        cache=dict()
        noofscales=self.config['noofscales']
        for textureType in self.textureTypes:
            p=patternCache()
            p.noofscales=noofscales
            p.mean=np.zeros((noofscales ) )
            p.stddev=np.zeros((noofscales) )
            p.thresholdCrossings=np.zeros((2*noofscales,8),dtype='int32' )
            p.thresholdStatus=np.zeros((2*noofscales,2),dtype='int32' )
            p.interpolationDeltas=np.zeros((2*noofscales,2) )
            p.frameoffsets=np.zeros((2),dtype='int32' )
            p.scaleoffsets=np.zeros((2),dtype='int32' )
            self.extractor.get_pattern_stats(p.mean, p.stddev,
                                    p.thresholdCrossings, p.thresholdStatus, p.interpolationDeltas,
                                    p.frameoffsets, p.scaleoffsets,
                                    textureType)
                                    

            self.logger.info('textureType: {0}'.format(textureType)) 
            self.logger.info('p.frameoffsets: {0}'.format(p.frameoffsets))
            self.logger.info('p.scaleoffsets: {0}'.format(p.scaleoffsets))
  
                                 
            t= textureCache()
            t.noofscales=noofscales
            t.mean=np.zeros((noofscales ))
            t.stddev=np.zeros((noofscales ))
            t.areasizes=np.zeros((noofscales ),dtype='int32')
            t.contextAreas=np.zeros((noofscales,3*noofscales),dtype='int32')
            t.frameoffsets=np.zeros((2),dtype='int32' )
            t.scaleoffsets=np.zeros((2),dtype='int32' )

            self.extractor.get_tract_stats(t.mean, t.stddev,
                                           t.areasizes, t.contextAreas,
                                           t.frameoffsets, t.scaleoffsets,
                                           textureType)
                                           
            self.logger.info('t.frameoffsets: {0}'.format(t.frameoffsets))
            self.logger.info('t.scaleoffsets: {0}'.format(t.scaleoffsets))
                                      
            c=structureCache(p,t)
            cache[textureType]=c
        
        filename = '{0}.cache'.format(self.cachename)
        fileobj = open(filename, 'wb')   
        pickle.dump(cache,fileobj,2)
        self.logger.info('           Dump to {0}'.format(filename))
        
    def processData(self, data):
        # This is important to do, prevents empty output publication.
        result = None
        
        # Check whether the data source is timescale representation
        if (data.received['TSRep'] is None):
            return result
        
        
        chunk=data.received['TSRep']
        currentData=chunk.data
        self.logger.info('structureProcessorCalibratorCore EdB shape: {0}'.format(np.shape(currentData)))
        if(chunk.continuity==Continuity.calibrationChunk):
            result=dict()
            self.extractor.initialize(currentData,self.config['maxdelay'])
            self.createCache()
            result['cacheCreated']=True
        
        return result
        
            
        
        
        




class structureProcessorCalibrator(structureProcessor):
    def __init__(self,boardConn, name,*args, **kwargs):
        super(structureProcessorCalibrator, self).__init__(boardConn, name,*args, **kwargs)
        
    def prerun(self):
        self.prerunsuper()
        self.kwargs['logger']=self.logger
        self.kwargs['name']=self.name
        self.structureProcessorCore=structureProcessorCalibratorCore(*self.args,**self.kwargs)
        self.structureProcessorCore.prerun()
        self.setProcessorAlignments()

    def processData(self, data):
        return self.structureProcessorCore.processData(data)
        
       
    def setProcessorAlignments(self):        
        ''' 
        setProcessorAlignments: set the dictionary 
        self.processorAlignments. 
        
        Part of the calibration is aimed at finding these parameters. 
        To keep going we initialize to an empty dictionary.
        '''
        self.processorAlignments=dict()
