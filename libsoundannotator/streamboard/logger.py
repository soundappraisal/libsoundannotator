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
'''
Unify calls to logger under windows and linux. Multiprocessing 
logger fails under windows, to make some level of logging available 
it is redericted to stdout.
'''
import multiprocessing
import logging
import sys, os

def new(reattach=False, level=logging.WARNING):
    
    if(reattach==True and not (sys.platform=='win32')):
        return
        
    if(sys.platform=='win32'):
        return  win_logger(level)
    else:
        return multiprocessing.get_logger()
            
class win_logger(object):
    
    def __init__(self,level=0):
        self.level=level
        
    def setLevel(self,level):
        self.level=level

    def info(self,info):
        if(self.level <= logging.INFO):
            print('[INFO]: {0}' .format(info))
            
    def warning(self,warning):
        if(self.level <= logging.WARNING):
            print('[WARNING]: {0}' .format(warning)) 
               
    def debug(self,debug):
        if(self.level <= logging.DEBUG):
            print('[DEBUG]: {0}'.format(debug))
            
    def error(self,error):
        if(self.level <= logging.ERROR):
            print('[DEBUG]: {0}'.format(error))
            
    def fatal(self,fatal):
        if(self.level <= logging.FATAL):
            print('[FATAL]: {0}' .format(fatal))

    def critical(self,critical):
        if(self.level <= logging.CRITICAL):
            print('[CRITICAL]: {0}' .format(critical))
