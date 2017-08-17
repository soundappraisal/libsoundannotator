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
class FileAnnotation(object):
    def __init__(self, filehandle, file_id, storagetype='wav'):
        self.filehandle=filehandle
        self.file_id=file_id
        self.storagetype=storagetype
        self.extra_args = dict()

    def __str__(self):
        return 'FileAnnotation filehandle: {0}  file_id: {1} storagetype: {2}'.format(self.filehandle,self.file_id, self.storagetype)
        
    def setExtraArgs(self, keys, annotation):
        for key in keys:
            if key in annotation:
                self.extra_args[key] = annotation[key]
                
