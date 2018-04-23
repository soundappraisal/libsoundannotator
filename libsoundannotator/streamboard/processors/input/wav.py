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
import os, time
import numpy as np

from libsoundannotator.streamboard                import processor
from libsoundannotator.streamboard.continuity     import Continuity, processorAlignment

from libsoundannotator.io.wavinput                import WavChunkReader
from libsoundannotator.io.hdfinput                import HdfChunkReader


from json import loads, dumps
from hashlib import sha1

class WavProcessor(processor.InputProcessor):
    def __init__(self, conn, name, *args, **kwargs):
        if (conn is not None):
            super(WavProcessor, self).__init__(conn, name, *args, **kwargs)

        self.requiredParameters('ChunkSize', 'SoundFiles', 'timestep','SampleRate')
        self.requiredParametersWithDefault(AddWhiteNoise=None, newFileContinuity=Continuity.newfile, startLatency=1.0)
        self.samplerate = self.config['SampleRate']
        self.chunksize = self.config['ChunkSize']
        self.soundfiles = self.config['SoundFiles']
        self.timestep = self.config['timestep']
        self.AddWhiteNoise = self.config['AddWhiteNoise']
        self.newFileContinuity=self.config['newFileContinuity']
        self.startLatency = self.config['startLatency']
        self.source=None
    
    def prerun(self):
        super(WavProcessor, self).prerun()
        self.setProcessorAlignments()
        
    def run(self):
        self.prerun()
        self.logger.info("Processor {0} started".format(self.name))
        self.stayAlive = True
        self.checkAndProcessBoardMessage()
        self.logger.info("Sleeping for {} seconds".format(self.startLatency))
        time.sleep(self.startLatency)
        for soundfile in self.soundfiles:
            self.processSoundfile(soundfile)

        self.publishlastchunk()

    '''
        Special function defined for the wave reader. What this does is
        overwrite the regular flow of generating data, by generating it for all sound files in a list.
        For every sound file a reader is opened, and closed automatically when the max amount of
        frames in the file is reached.
        Frames are retrieved from the reader and published by generateData
    '''
    def processSoundfile(self, soundfile):
        self.continuity = self.newFileContinuity

        if soundfile.storagetype == 'wav':
            self.reader = WavChunkReader(soundfile.filehandle)
            if not self.samplerate == self.reader.getSamplerate():
                raise  RuntimeError('Sample rate of file is inconsistent with specified sample rate')
             
            self.source=dict()
            self.source['source_id']=soundfile.file_id              # This fields is used to determine name of the outputfile in the FileWriter
            self.source['duration']=self.reader.getDuration()
            if soundfile.extra_args:
                self.source['annotation']=dumps(soundfile.extra_args)
        elif soundfile.storagetype == 'hdf':
            self.reader = HdfChunkReader(soundfile.filehandle)
        else:
            raise Exception("Unknown storage type for soundfile: {0}".format(soundfile.storagetype))

        while (self.reader.hasFrames() and self.stayAlive):
            '''
                we call 'process', because this calls generateData with a chunk timestamp already.
                It also lets us intercept board messages
            '''

            self.process()
            self.checkAndProcessBoardMessage()
            '''
                Sleep is an artificial means of lowering the system load. Here it is done to allow
                chunks to propagate along other modules
            '''
            time.sleep(self.timestep)
            #set continuity
            self.continuity = Continuity.withprevious

    def generateData(self):
        frames = self.reader.readFrames(self.chunksize)

        # If specified, add some noise to prevent NaN from occuring due to log(E)
        if self.AddWhiteNoise:
            frames += self.generateWhitenoise(frames)

        data = {
            'sound' : frames
        }
        return data


    def generateWhitenoise(self,frames,addWhiteNoise=None):
        
        if addWhiteNoise is None:
            addWhiteNoise=self.AddWhiteNoise
        
        if addWhiteNoise is None:
            self.logger.error("generateWhitenoise called without valid value")
            raise TypeError("generateWhitenoise expects that a value is set for addWhiteNoise, received None")
           
        if frames.dtype == np.int16:
            noise=np.random.binomial(np.int16(addWhiteNoise), .5, size=frames.shape).astype(frames.dtype)-addWhiteNoise/2
        elif frames.dtype == np.int32:
            noise=np.random.binomial(np.int32(addWhiteNoise), .5, size=frames.shape).astype(frames.dtype)-addWhiteNoise/2
        else:
            noise=(addWhiteNoise * (np.random.rand(*frames.shape)-0.5)).astype(frames.dtype)
            
        return noise
        
    def getsamplerate(self, key):
        return self.samplerate

    def getTimeStamp(self, key):
        self.logger.info('Time: {0}'.format(self.reader.getTime()))
        return self.reader.getTime()

    def publishlastchunk(self):
  
        '''
            Last chunks with mock data are propagated through the system. The mock-data is needed to pass through the processors and get the right representations out. Alternative would be to litter the code with if statements testing for Continuity.last. That is left solely to output processors and scripts now.
            
            Last chunks are non-data chunks, they should therefore not carry data that needs to be processed for real. A last chunk is passed to give processors the opportunity to wrap up before they stop processing.
        '''
        self.logger.debug("Publish last chunk")
        data=dict()
        
        frames = self.reader.getNullChunk(self.chunksize)
        if self.AddWhiteNoise:
            frames += self.generateWhitenoise(frames)
        elif issubclass(frames.dtype.type, np.integer):
            frames += self.generateWhitenoise(frames, addWhiteNoise=3)
        else:
            frames += self.generateWhitenoise(frames, addWhiteNoise=2**-100)
            
        data['sound'] =frames
        
        self.continuity=Continuity.last
        self.publish(data, self.continuity, self.getTimeStamp(None), self.getchunknumber(), {self.name:time.time()}, metadata=self.getMetaData())

       
    def setProcessorAlignments(self): 
        '''
         setProcessorAlignments: assign empty dict to self.processorAlignments   
        '''
        self.processorAlignments=dict()
        self.processorAlignments['sound']=processorAlignment(fsampling=self.getsamplerate('sound'))



    def getMetaData(self):
        config_serializable=self.config.copy()
        del config_serializable['SoundFiles']
        annotation=dict()
        
        if not self.source is None:
            annotation['source_id']=self.source['source_id']
            annotation['duration']=self.source['duration']
            if 'annotation' in self.source.keys():
                annotation['annotation']=self.source['annotation']
        
        config_json=dumps(config_serializable, sort_keys=True)
        config_hash=sha1(config_json).hexdigest()
        annotation_json=dumps(annotation, sort_keys=True)
        return  {self.name: (config_hash, config_json, annotation_json)}
