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
class BoardMessage(object):
    """ Object used as messages between the Board and processors
    """

    stop = 0
    subscribe = 1
    subscription=2
    networksubscription=3
    testrequiredkeys=4

    def __init__(self, mType, args):
        self.mType = mType
        self.contents = args

    def getContents(self):
        return self.contents

    def getType(self):
        return self.mType

class ProcessorMessage(object):
    """ Object used as messages between the Board and processors
    """

    error = 0
    def __init__(self, mType, contents):
        self.mType = mType
        self.contents = contents

    def getContents(self):
        return self.contents

    def getType(self):
        return self.mType


class NetworkMessageMeta(type):
    def __getattr__(cls, key):
        if key in cls.values:
            return str(key)
        else:
            return None

class NetworkMessage(object):
    __metaclass__ = NetworkMessageMeta
    """ Object used as network message for test handshake between two ends of the pipe
    """

    values = {
        'PING' : "ping",
        'PONG' : "pong"
    }
