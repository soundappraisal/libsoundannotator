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
import wave
import numpy as np
import time

class WavChunkReader(object):

    def __init__(self, soundfile, *args, **kwargs):
        self.openfile(soundfile)

    def openfile(self, soundfile):
        self.wavereader = wave.open(soundfile)
        self.fs=self.wavereader.getframerate()
        self.nframes=self.wavereader.getnframes()
        self.nchannels=self.wavereader.getnchannels()
        self.duration = float(self.nframes) / float(self.fs)
        samplewidth=self.wavereader.getsampwidth()
        self.dtype='int{0}'.format(2**(samplewidth-1)*8)

        self.framepointer = 0

    def __repr__(self):
        if not hasattr(self, 'wavereader'):
            return "WavChunkReader: no file loaded"

        return """
        fs: {0},
        nframes: {1},
        duration: {2}
        channels: {3},
        sampwidth: {4},
        dtype: {5}
        """.format(self.fs,self.nframes, self.duration, self.wavereader.getnchannels(), self.wavereader.getsampwidth(), self.dtype)

    def closefile(self):
        self.wavereader.close()

    def hasFrames(self):
        return self.framepointer < self.nframes

    def readFrames(self, N):
        #raise when not opened properly
        if not hasattr(self, 'wavereader'):
            raise Exception("No wavereader attribute set")

        '''
            Our convention to read frames is that this function returns at most N frames,
            but possibly less when there are less frames left.
            The next call to hasFrames should return false at the end because the
            framepointer is set to nframes.
            When the maximum amount of frames is read, the wavereader is closed,
            so the next call to this function will raise an exception
        '''
        self.initialframepointer=self.framepointer
        if self.framepointer + N < self.nframes:
            frames = self.wavereader.readframes(N)
            self.framepointer += N
        else:
            frames = self.wavereader.readframes(self.nframes - self.framepointer)
            self.framepointer = self.nframes

            #close the reader and remove it for safety
            self.closefile()
            del self.wavereader
        
        
        return np.fromstring(frames, dtype=self.dtype)[::self.nchannels]

    def getNullChunk(self, N):
        return np.zeros(N,dtype=self.dtype)

    def getSamplerate(self):
        return self.fs
    def getFramepointer(self):
        return self.framepointer
    def getTime(self):
        return float(self.initialframepointer) / float(self.fs)
    def getDuration(self):
        return self.duration
    def getPercent(self):
        return (float(self.framepointer) / float(self.nframes)) * 100.
