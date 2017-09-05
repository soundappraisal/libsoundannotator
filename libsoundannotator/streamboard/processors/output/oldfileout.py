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
from libsoundannotator.io.oldstorage             import StorageFormatterFactory

import os, time, glob, sys, datetime
import numpy as np
import h5py

import util

class FileOutputProcessor(processor.OutputProcessor):
    def __init__(self, *args, **kwargs):
        super(FileOutputProcessor, self).__init__(*args, **kwargs)
        #set required keys to subscription keys, or to empty list
        self.requiredKeys = kwargs.get('requiredKeys', self.requiredKeys)
        self.requiredParameters('outdir', 'classType', 'maxFileSize')
        self.requiredParametersWithDefault(
            outdir = os.path.join(os.path.expanduser("~"), "data", "libsoundannotator"),
            classType = "HDF5Storage",
            maxFileSize = 104857600, #100M in bytes
            datatype = 'int16',
            usewavname=False,
        )

        self.fileExt = 'hdf5'
        self.startNum = 1

    def finalize(self):
        self.logger.info("Finalize in FileOutputProcessor")
        if self.h5pyf:
            self.logger.info("Flushing and closing file handler")
            self.h5pyf.flush()
            self.h5pyf.close()

    def prerun(self):
        super(FileOutputProcessor, self).prerun()
        #create output dir if it doesn't exist
        self.storageformatter = StorageFormatterFactory.getInstance(self.config["classType"])
        basedir = os.path.join(self.config['outdir'], self.storageformatter.foldername)
        self.outdir = util.resolveOutdir(basedir)

    def processData(self, compositeChunk):
        metadata = compositeChunk.metadata
        self.logger.info("Received smart chunk with metadata: {0}".format(metadata))

        outdir = self.outdir
        location = util.getLocation(metadata, self.config)
        self.logger.info('Location: {}'.format(location))
        #if discontinuous, force new file
        if compositeChunk.continuity == Continuity.discontinuous or compositeChunk.continuity == Continuity.newfile:
            self.logger.warning("Encountered discontinuity. Saving output into new file")
            #force increment in new file
            self.h5pyf = util.resolveDataFile(outdir, location, logger=self.logger, maxFileSize=self.config['maxFileSize'], forceNewFile=True)
        elif compositeChunk.continuity == Continuity.last:
            pass
        else:
            #resolve current file
            self.h5pyf = util.resolveDataFile(outdir, location, logger=self.logger, maxFileSize=self.config['maxFileSize'])

        if not compositeChunk.continuity == Continuity.last:
            #set or check metadata
            self.setOrCheckClientMetadata(self.h5pyf, metadata)

            #for each required key, open the data set, or retrieve it if it exists
            for key in compositeChunk.received:
                chunk = compositeChunk.received[key]

                if chunk.data.dtype != self.config['datatype']:
                    #convert to config data type if possible
                    chunk.data = chunk.data.astype(self.config['datatype'])

                self.addChunkToDataset(self.h5pyf, key, chunk)

        #close handle to prevent corruption
        self.logger.info('Closing h5py handle')
        
        if self.h5pyf:
            self.h5pyf.flush()
            self.h5pyf.close()

    def addChunkToDataset(self, h5pyf, key, chunk):
        maxshape = (None,)
        shapeDim = 0

        # Check for zero size data and discard it, hdf doesn't  know how to deal with it.
        if chunk.data.size == 0:
            return

        if not key in self.h5pyf:
            # based on the dimensionality, define maxshape. if 1D, this dimension is resizable.
            # if 2D, columns are resizable
            if len(chunk.data.shape) == 1:
                shape = (0,)
                maxshape = (None,)
            elif len(chunk.data.shape) == 2:
                shape=(chunk.data.shape[0], 0)
                maxshape = (chunk.data.shape[0], None)
                shapeDim = 1
            elif len(chunk.data.shape) > 2:
                self.logger.error("Unsupported nr. of dimensions to define maxshape: {0}".format(len(chunk.data.shape)))

            #create a new data set for this key, resizable in column direction
            dset = self.h5pyf.create_dataset(key,
                shape=shape,
                dtype=self.config['datatype'],
                maxshape=maxshape,
                compression="gzip",
                compression_opts=9,
            )
        else:
            dset = self.h5pyf[key]
            if len(dset.shape) == 2:
                maxshape = (dset.shape[0], None)
                shapeDim = 1

        # dset is available, call reshape using the current shape and the chunk's
        # column length

        dset.resize(dset.shape[shapeDim] + chunk.data.shape[shapeDim], shapeDim)
        # place the chunk's data at the end in its place
        if len(chunk.data.shape) == 1:
            dset[-chunk.data.shape[shapeDim]:] = chunk.data
        elif len(chunk.data.shape) == 2:
            dset[:, -chunk.data.shape[shapeDim]:] = chunk.data
        else:
            raise Exception("Cannot append {0}D data".format(len(chunk.data.shape)))

        #call to embed the chunk's meta data into the data set
        self.addChunkMetadata(dset, chunk, shapeDim)

    def setOrCheckClientMetadata(self, h5pyf, metadata):
        for key in metadata:
            #if meta is available in self.h5pyf...
            if key in self.h5pyf.attrs:
                # ...but current value differs, print warning
                if str(self.h5pyf.attrs[key]) != str(metadata[key]):
                    self.logger.warning("New client meta data mismatch on key {0} :{1} vs. {2}"
                        .format(key, self.h5pyf.attrs[key], metadata[key])
                    )
                # if current value doesn't differ, don't update
            else:
                self.logger.info("Setting {0} = {1} in metadata".format(key, metadata[key]))
                val = metadata[key]
                #'escape' None or False to prevent crash
                if type(val) == np.ndarray:
                    pass
                elif val is False or val is None:
                    val = str(val)
                #set the meta data
                self.h5pyf.attrs[key] = val

    def addChunkMetadata(self, dset, chunk, shapeDim):
        #check if 'starttime' attr is set, if not set it
        if not 'starttime' in dset.attrs:
            dset.attrs.create('starttime', str(chunk.dataGenerationTime))
        #always update 'endtime' with chunk's current 'dataGenerationTime'
        if not 'endtime' in dset.attrs:
            dset.attrs.create('endtime', str(chunk.dataGenerationTime))
        else:
            dset.attrs['endtime'] = str(chunk.dataGenerationTime)

        #every 100 chunks, add the generation time to the first sample of the new chunk
        if chunk.number % 100 == 0:
            dset.attrs.create(str(dset.shape[shapeDim] + 1), str(chunk.dataGenerationTime))
