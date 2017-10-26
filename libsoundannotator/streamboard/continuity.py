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
class ContinuityMeta(type):
    
   
    
    #Continuity class: please maintain numerical order, and the code assumes the mapping to be one-to-one
    values = {
        #invalid chunk
        'invalid' : -1,
        #discontinuous subtypes
        'discontinuous' : 0,
        'newfile': 1,
        'calibrationChunk': 2,
        #withprevious subtypes
        'withprevious' : 10,
        'last' : 11
    }
    
    '''
    Note:
        Last chunks with mock data are propagated through the system. The mock-data is needed to pass through the processors and get the right representations out. Alternative would be to litter the code with if statements testing for Continuity.last. That is left solely to output processors and scripts now.
        Last chunks are mock-data chunks, they should therefore not carry data that needs to be processed for real. A last chunk is passed to give processors the opportunity to wrap up before they stop processing. Script can use it to terminate processing.
    '''

    reverse_lookup = dict((value, key) for key, value in values.iteritems())

    def __getattr__(cls, key):
        if key in cls.values:
            return cls.values[key]
        else:
            return None

    @staticmethod
    def getstring(cls,key):
        if key in cls.reverse_lookup:
            return cls.reverse_lookup[key]
        else:
            return None

class Continuity(object):

    __metaclass__ = ContinuityMeta

class chunkAlignment(object):
    """
        Class to keep track of alignment of chunk with respect to the original signal
    """
    def __init__(self, includedPast=0 , droppedAfterDiscontinuity=0 , invalidLargeScales=0 , invalidSmallScales=0, alignable=True, fsampling=None):
        
        self.set(includedPast, droppedAfterDiscontinuity, invalidLargeScales, invalidSmallScales, alignable,fsampling)
        
    def set(self, includedPast, droppedAfterDiscontinuity, invalidLargeScales, invalidSmallScales, alignable,fsampling):
        self.includedPast=includedPast
        self.droppedAfterDiscontinuity=droppedAfterDiscontinuity
        self.invalidLargeScales=invalidLargeScales
        self.invalidSmallScales=invalidSmallScales
        self.alignable=alignable
        self.fsampling=fsampling
    
    def copy(self):
        return chunkAlignment(
            self.includedPast,
            self.droppedAfterDiscontinuity,
            self.invalidLargeScales,
            self.invalidSmallScales,
            self.alignable,
            self.fsampling,
        )
        

    def merge(self,other):
        
        if not (self.alignable and other.alignable):
            raise ValueError('chunkAlignment objects can not be aligned because at least on chunk is not alignable') 
        
        if not (self.fsampling == other.fsampling):
            raise ValueError('chunkAlignment objects can not be aligned because of incompatible sampling frequencies') 
        
            
        includedPast=max(self.includedPast,other.includedPast)
        droppedAfterDiscontinuity=max(self.droppedAfterDiscontinuity,other.droppedAfterDiscontinuity)
        invalidLargeScales=max(self.invalidLargeScales,other.invalidLargeScales)
        invalidSmallScales=max(self.invalidSmallScales,other.invalidSmallScales)
        fsampling=self.fsampling
        
        return chunkAlignment(  includedPast=includedPast,
                                droppedAfterDiscontinuity=droppedAfterDiscontinuity,
                                invalidLargeScales=invalidLargeScales,
                                invalidSmallScales=invalidSmallScales,
                                fsampling=fsampling,
                                )

    
    
    def impose_processor_alignment(self,processor_alignment):
        
        if(type(processor_alignment)==processorAlignment):
            #raise TypeError('self.includedPast{0},processor_alignment.includedPast: {1}'.format(type(self.includedPast),type(processor_alignment.includedPast)))
            
            if self.fsampling == processor_alignment.fsampling:
                includedPast=self.includedPast+processor_alignment.includedPast
                droppedAfterDiscontinuity=self.droppedAfterDiscontinuity+processor_alignment.droppedAfterDiscontinuity
            else:
                includedPast=int((self.includedPast*processor_alignment.fsampling)/self.fsampling)+processor_alignment.includedPast
                droppedAfterDiscontinuity=int((self.droppedAfterDiscontinuity*processor_alignment.fsampling)/self.fsampling)+processor_alignment.droppedAfterDiscontinuity
                
            invalidLargeScales=self.invalidLargeScales+processor_alignment.invalidLargeScales
            invalidSmallScales=self.invalidSmallScales+processor_alignment.invalidSmallScales
            fsampling=processor_alignment.fsampling
                
            return chunkAlignment(  includedPast=includedPast,
                                    droppedAfterDiscontinuity=droppedAfterDiscontinuity,
                                    invalidLargeScales=invalidLargeScales,
                                    invalidSmallScales=invalidSmallScales,
                                    fsampling=fsampling)
        else:
            raise TypeError('Trying to impose non processorAlignment. Probably you want merge to chunkAlignment objects. ')
    
    def isAlignable(self):
        return self.alignable
        
    def __eq__(self, other):
        
        if not type(self) == type(other):
            ret = False
        else:
            if(
                self.includedPast==other.includedPast and
                self.droppedAfterDiscontinuity==other.droppedAfterDiscontinuity and
                self.invalidLargeScales==other.invalidLargeScales and
                self.invalidSmallScales==other.invalidSmallScales and
                self.alignable==other.alignable 
            ):
                ret =  True
            else:
                ret = False
        
        return ret
            
    def __str__(self):
        return '\n\t includedPast: {0}\n\t droppedAfterDiscontinuity: {1}\n\t invalidLargeScales: {2}\n\t invalidSmallScales: {3}\n\t alignable: {4}'.format(  self.includedPast,self.droppedAfterDiscontinuity,
        self.invalidLargeScales,self.invalidSmallScales,
        self.alignable)
    

class processorAlignment(chunkAlignment):
    pass
