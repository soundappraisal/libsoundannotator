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
import redis, os, time
import numpy as np

from libsoundannotator.streamboard                import processor
from libsoundannotator.streamboard.continuity     import Continuity

from libsoundannotator.io.annotations             import FileAnnotation
from libsoundannotator.io.wavinput                import WavChunkReader

from libsoundannotator.io.hdfinput                import HdfChunkReader

class WavProcessor(processor.InputProcessor):
    def __init__(self, conn, name, *args, **kwargs):
        if (conn != None):
            super(WavProcessor, self).__init__(conn, name, *args, **kwargs)

        self.requiredParameters('ChunkSize', 'SoundFiles', 'timestep')
        self.requiredParametersWithDefault(AddWhiteNoise=None, newFileContinuity=Continuity.newfile, startLatency=1.0)

        self.chunksize = self.config['ChunkSize']
        self.soundfiles = self.config['SoundFiles']
        self.timestep = self.config['timestep']
        self.AddWhiteNoise = self.config['AddWhiteNoise']
        self.newFileContinuity=self.config['newFileContinuity']
        self.startLatency = self.config['startLatency']

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

        self.sources = set([soundfile.uid])

        if soundfile.storagetype == 'wav':
            self.reader = WavChunkReader(soundfile.filename)
            self.oldchunk.metadata['wav']=soundfile.filename
            self.oldchunk.metadata['duration']=self.reader.getDuration()
        elif soundfile.storagetype == 'hdf':
            self.reader = HdfChunkReader(soundfile.filename)
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
            noise=(addWhiteNoise * (np.random.rand(frames.shape)-0.5)).astype(frames.dtype)
            
        return noise
        
    def getsamplerate(self, key):
        return self.reader.getSamplerate()

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
        self.publish(data, self.continuity, self.getTimeStamp(None), self.getchunknumber(), {self.name:time.time()}, metadata=self.oldchunk.getMetaData())


class JobProcessor(processor.InputProcessor):

    def __init__(self, conn, name, *args, **kwargs):
        super(JobProcessor, self).__init__(conn, name, *args, **kwargs)

        self.requiredParameters('dir','timestep','ChunkSize')
        self.requiredParametersWithDefault(RedisHost='localhost', RedisPort=6379, AddWhiteNoise=True)

        self.chunksize = self.config['ChunkSize']
        self.timestep = self.config['timestep']
        self.AddWhiteNoise = self.config['AddWhiteNoise']

    '''
        A Redis connection is made
    '''
    def prerun(self):
        self.redis = redis.StrictRedis(host=self.config['RedisHost'], port=self.config['RedisPort'])

    '''
        Every iteration Redis is checked for files in the 'audiojobs' set
        If a job is retrieved, process the sound file(s)
    '''
    def process(self):
        njobs = self.redis.zcard('audiojobs')
        if njobs > 0:
            self.logger.info("Has %d jobs" % njobs)
            jobs = self.redis.zrange('audiojobs', 0, njobs)
            for job in jobs:
                annotation = FileAnnotation(os.path.join(self.config['dir'], job), job)
                self.processSoundfile(annotation)
        else:
            self.logger.info("No jobs available")

    '''
        A new reader is created, and while that reader has frames, input is generated and published
    '''
    def processSoundfile(self, soundfile):
        self.continuity = Continuity.newfile
        self.sources = set([soundfile.uid])
        ID = os.path.splitext(os.path.basename(soundfile.filename))[0]
        self.reader = WavChunkReader(soundfile.filename, chunksize = self.chunksize)
        self.logger.info("Processing file {0}".format(soundfile.filename))
        while (self.reader.hasFrames() and self.stayAlive):
            data = self.generateData()
            self.publish(data,self.continuity, self.getTimeStamp(None), self.getchunknumber(), time.time(), identifier=ID)
            self.checkAndProcessBoardMessage()
            '''
                Sleep is an artificial means of lowering the system load. Here it is done to allow
                chunks to propagate along other modules
            '''
            time.sleep(self.timestep)
            #set continuity
            self.continuity = Continuity.withprevious

    '''
        The actual frames from the reader are read, and returned
    '''
    def generateData(self):
        frames = self.reader.readFrames(self.chunksize)

        # If specified, add some noise to prevent NaN from occuring due to log(E)
        if self.AddWhiteNoise:
            frames += self.AddWhiteNoise * np.random.rand(frames.shape[0])

        data = {
            'sound' : frames
        }
        return data

    '''
        It's necessary to overwrite this parent method because this is the start of the chain,
        so no config['SampleRate'] value is known yet
    '''
    def getsamplerate(self, key):
        return self.reader.getSamplerate()

    '''
        Instead of the current time, this returns the time inside the audio file
    '''
    def getTimeStamp(self, key):
        self.logger.info('Time: {0}'.format(self.reader.getTime()))
        return self.reader.getTime()
