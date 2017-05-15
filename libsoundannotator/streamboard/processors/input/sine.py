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
import numpy as np, time

from libsoundannotator.streamboard               import processor
from libsoundannotator.streamboard.continuity    import Continuity

class SineWaveGenerator(processor.InputProcessor):

    """ SineWaveGenerator:
            Does what you expect from the name

        Parameters:
            SampleRate: in Hz
            ChunkSize: the number of samples you want to read and return
                       per block
    """

    def __init__(self, *args, **kwargs):
        super(SineWaveGenerator, self).__init__(*args, **kwargs)
        self.requiredParameters('SampleRate', 'ChunkSize')
        self.requiredParametersWithDefault(Frequency=1000)

    def prerun(self):
        super(SineWaveGenerator, self).prerun()
        subscription = False
        while not subscription:
            self.checkAndProcessBoardMessage()
            if(len(self.subscriptions) >0):
                subscription = True
        self.startframe=0

    def generateData(self):
        dataout=dict()
        self.logger.debug('Processor generate data for startframe:{0}'.format(self.startframe))
        f=self.config['Frequency']
        w=2*np.pi*f/self.config['SampleRate']
        sampleIndices=np.arange(self.startframe,self.startframe+self.config['ChunkSize'])
        data = 2000*np.sin(w*sampleIndices)
        self.startframe+=self.config['ChunkSize']
        time.sleep(float(self.config['ChunkSize'])/float(self.config['SampleRate']))
        dataout['sound']=data
        return dataout
