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
import h5py
import numpy as np
import time

class HdfChunkReader(object):

    def __init__(self, soundfile, *args, **kwargs):
        self.openfile(soundfile)

    def openfile(self, soundfile):
        self.h5filehandle = h5py.File(soundfile,'r')
        self.fs=self.h5filehandle.attrs["inputrate"]
        self.data=self.h5filehandle["sound"]
        self.nframes=self.data.len()
        self.starttime=float(self.data.attrs["starttime"])
        self.dtype=self.data.dtype
        self.framepointer = 0

    def closefile(self):
        self.h5filehandle.close()

    def hasFrames(self):
        return self.framepointer < self.nframes

    def readFrames(self, N):
        #raise when not opened properly
        if not hasattr(self, 'h5filehandle'):
            raise Exception("No h5filehandle attribute set")

        '''
            Our convention to read frames is that this function returns at most N frames,
            but possibly less when there are less frames left.
            The next call to hasFrames should return false at the end because the 
            framepointer is set to nframes.
            When the maximum amount of frames is read, the wavereader is closed, 
            so the next call to this function will raise an exception
        '''
        if self.framepointer + N < self.nframes:
            frames = self.data[self.framepointer:self.framepointer+N]
            self.framepointer += N
        else:
            frames = self.data[self.framepointer:]
            self.framepointer = self.nframes

            #close the reader and remove it for safety
            self.closefile()
            del self.h5filehandle

        return frames

    def getNullChunk(self, N):
        return np.zeros(N,dtype=self.dtype)

    def getSamplerate(self):
        return self.fs
    def getFramepointer(self):
        return self.framepointer
        
    def getTime(self):
        return self.starttime+float(self.framepointer) / float(self.fs)
        
    def getPercent(self):
        return (float(self.framepointer) / float(self.nframes)) * 100.


