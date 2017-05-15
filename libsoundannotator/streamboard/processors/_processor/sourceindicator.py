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

from libsoundannotator.streamboard import processor
from libsoundannotator.cpsp.sourceindicators import indicator, config, util

class SourceIndicatorProcessor(processor.Processor):
    '''
        Processor for relaying audio to the network
    '''
    requiredKeys = ['energy', 'pulse', 'tone', 'noise']

    def __init__(self, boardConn, name, *args, **kwargs):
        super(SourceIndicatorProcessor, self).__init__(boardConn, name, *args, **kwargs)

    def prerun(self):
        super(SourceIndicatorProcessor, self).prerun()
        self.config['logger'] = self.logger
        self.indicators, self.models, self.bgmodels = util.initFromConfig(config, **self.config)

    def processData(self, compositeChunk):
        inputs = {}
        for name in compositeChunk.received:
            inputs[name] = compositeChunk.received[name].data
        util.calculateBGModels(inputs, self.indicators, self.bgmodels, normalize=True)
        result = {}

        for i in self.indicators:
            resp = i.calculate()
            if resp is not None:
                self.logger.info("Detector {} got value {}".format(i.name, resp))
                result[i.name] = resp

        if any([res is not None for res in result.values()]):
            return result
        else:
            return None
