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
from libsoundannotator.streamboard               import processor
from libsoundannotator.streamboard.continuity    import Continuity

import os, numpy as np, h5py
import util

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

class HDF5ImageProcessor(processor.OutputProcessor):
    def __init__(self, *args, **kwargs):
        super(HDF5ImageProcessor, self).__init__(*args, **kwargs)
        self.requiredKeys = ['energy']
        self.requiredParameters('metadata')
        self.requiredParametersWithDefault(
            basedir=kwargs.get('basedir', os.path.join(os.path.expanduser("~"), "data", "libsoundannotator")),
            usewavname=True,
            maxFileSize=104857600
        )

    def processData(self, smartChunk):
        # save the metadata
        self.metadata = smartChunk.chunkMetaData
        return

    def print1D(self, dset, location):
        return

    def print2D(self, key, dset, location):
        image = plt.imshow(dset, interpolation='none', aspect='auto', origin='bottom')
        axes = image.get_axes()
        yticks = axes.get_yticks()
        xticks = axes.get_xticks()
        frequencies = self.metadata['fMap']
        axes.set_ylabel('Frequency (Hz)')
        axes.set_yticklabels(["{0:.1f}".format(f) for f in np.linspace(frequencies[0], frequencies[-1], len(yticks))])
        axes.set_xlabel('Time (s)')
        axes.set_xticklabels(["{0:.1f}".format(t) for t in np.linspace(0, self.metadata['duration'], len(xticks))])
        plt.savefig('{}/{}_{}.png'.format(self.outdir, location, key))

    def finalize(self):
        #here magic happens
        self.outdir = util.resolveOutdir(self.config['basedir'], logger=self.logger)
        location = util.getLocation(self.config['metadata'], self.config)
        h5pyf = util.resolveDataFile(self.outdir, location, logger=self.logger, maxFileSize=self.config['maxFileSize'])
        for key in h5pyf.keys():
            dim = len(h5pyf[key].shape)
            if dim == 1:
                self.print1D(key, h5pyf[key], location)
            elif dim == 2:
                self.print2D(key, h5pyf[key], location)
            else:
                self.logger.error('Unable to print figure with dimensionaly {}'.format(dim))
