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
import logging, multiprocessing, os, glob, sys, datetime, h5py
from json import loads, dumps
from hashlib import sha1

def getLocation(metadata, config):
    if 'usesource_id' in config.keys() and config['usesource_id'] is True:
        sourcedata=loads(metadata[config['source_processor']][1])
        location=os.path.basename(sourcedata['source_id'])
    elif 'location' in config.keys():
        location=config['location'].replace(' ', '_')
    else: # provide reasonable default
        datadir=os.path.join(os.path.expanduser('~'),'soundannotator_data')
        if  not os.path.isdir(datadir):
            if os.path.exists(datadir):
                raise  RuntimeError('Data directory path, ~/soundannotator_data, unavailable for directory creation.') 
            else:
                os.mkdir(datadir)
        location=os.path.join(datadir,'libsoundannotator','hdfdump')
            

    return location

def resolveDataFile(basedir, location, startNum=1, logger=None, forceNewFile=False, maxFileSize=104857600, fileExt='hdf5'):
    if logger is None:
        logger = multiprocessing.log_to_stderr()
        logger.setLevel(logging.INFO)
    # look if there are files with 'location' in their name in the basedir
    # following the convention <location>.*.<ext>
    files = glob.glob(os.path.join(basedir, "{0}.*.{1}".format(location, fileExt)))
    if len(files) == 0:
        num = startNum
    else:
        '''
            Try to find the number of the last file.
            Since the convention is <location>.<num>.<ext>, we can remove the location and
            extension with a map, and parse the rest as ints, then sort it and determine
            the last number.

            If unsuccesful, we don't know where to save and cannot continue
        '''
        try:
            full_loc = os.path.join(basedir, location)
                                        #example: room.5.hdf5 will yield '5'
            ints = map(lambda x: int(x[len(full_loc) + 1:-(len(fileExt)+1)]), files)
            ints = sorted(ints)[::-1] #reverse-sort integers by height
        except Exception as e:
            logger.critical("Cannot determine output file")
            raise e

        #first entry of ints is heighest rotated file number
        num = ints[0]
        # increment by one if force new file
        if forceNewFile:
            num += 1
        #if filesize is too large, increment as well
        else:
            abspathToFile = os.path.join(basedir, "{0}.{1}.{2}".format(location, num, fileExt))
            size = os.stat(abspathToFile).st_size
            if size >= maxFileSize:
                logger.info("Current file's size too large: {0} vs. max {1}"
                    .format(size, maxFileSize)
                )
                num += 1

    filename = "{0}.{1}.{2}".format(location, num, fileExt)
    logger.info("Resolved filename {0}".format(filename))
    #open or create
    h5pyf = h5py.File(os.path.join(basedir, filename),'a')

    return h5pyf

def resolveOutdir(basedir, logger=None):
    if logger is None:
        logger = multiprocessing.log_to_stderr()
        logger.setLevel(logging.INFO)
    if not os.path.isdir(basedir):
        logger.info("Base outdir does not exist. Creating output directory: {0}".format(basedir))
        try:
            os.makedirs(basedir)
        except Exception as e:
            logger.error("Unable to create directories: {0}".format(e))
            return

    now = datetime.date.today()
    foldername = now.strftime('%Y-%m-%d')
    todaydir = os.path.join(basedir, foldername)
    if not os.path.isdir(todaydir):
        logger.info("Current-day folder does not exist. Creating output folder {0}".format(foldername))
        try:
            os.makedirs(todaydir)
            return todaydir
        except Exception as e:
            logger.error("Unable to create output folder: {0}".format(e))
            return
    else:
        logger.info("Storing to output directory {0}".format(todaydir))
        return todaydir
