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
import multiprocessing

class NetworkConfigError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class NoNetworkException(Exception):
    pass
class ClosedSocketException(Exception):
    pass
class NotSameSocketException(Exception):
    pass
class BusyNetworkException(Exception):
    pass
class SocketBufferFullException(Exception):
    pass

class NetworkMixin(object):
    _chunk = None
    _connection = None
    _data = None

    _config = None
    _kwargs = None
    def setupSocket(self, config, **kwargs):
        self._config = config
        self._kwargs = kwargs
        if not 'interface' in config:
            raise NetworkConfigError('No interface specified in network config')
        elif not 'port' in config:
            raise NetworkConfigError('No port specified in network config')
        elif config['port'] < 1024:
            raise NetworkConfigError('Port number lies in the restricted domain <1024: {0}'.format(config['port']))
        elif not 'type' in config:
            raise NetworkConfigError('No config type specified. Specify \'server\' or \'client\'')
        elif not config['type'] in ['server', 'client']:
            raise NetworkConfigError('Wrong config type specified. Needed \'server\' or \'client\', got \'{0}\''.format(config['type']))

        if config['type'] == 'server':
            self._logInfo("Setting up socket listener {0}:{1}".format(config['interface'],config['port']))
            try:
                listener = multiprocessing.connection.Listener((config['interface'], config['port']), 'AF_INET')
                self._connection = listener.accept()
            except Exception as e:
                self._logError("Something went wrong binding the listener: {0}".format(e))
                raise e

        elif config['type'] == 'client':
            self._logInfo("Setting up socket client")
            self._connection = multiprocessing.connection.Client((config['interface'], config['port']))

        self._networkType = config['type']

        # we impersonate a low-level socket connection by telling everyone we
        # have a connected socket. It doesn't matter what we put in there,
        # as long as its length is bigger than 1
        self._sockets = [None, None]
        #register the afterdataCallback
        afterData = kwargs.get('afterdataCallback', None)
        if afterData is not None:
            self._logInfo("Registered afterdataCallback")
            self._afterdataCallback = afterData

    def prepareSend(self, sock, chunk):
        if self._networkType == 'server':
            raise Exception('Unable to send chunk in a receiving connection')

        # stash the chunk
        self._chunk = chunk

    def pollSockets(self, timeout):
        if self._networkType == 'client':
            # send the stashed chunk
            if self._chunk is not None:
                self._connection.send(self._chunk)
                self._chunk = None

        elif self._networkType == 'server':
            hasData = self._connection.poll(timeout)
            if hasData:
                try:
                    data = self._connection.recv()
                    self._afterdataCallback(data)
                except EOFError as e:
                    self.resetConnection()
                    raise ClosedSocketException('Other end has disconnected')

    def resetConnection(self):
        self.closeSockets()
        self.setupSocket(self._config, **self._kwargs)

    def closeSockets(self):
        self._connection.close()
        self._connection = None
        self._chunk = None
        self._data = None

    def _logError(self, msg):
        if hasattr(self, 'logger'):
            self.logger.error(msg)
        else:
            print "[ERROR]: {0}".format(msg)

    def _logInfo(self, msg):
        if hasattr(self, 'logger'):
            self.logger.info(msg)
        else:
            print "[INFO]: {0}".format(msg)

    def _logDebug(self, msg):
        if hasattr(self, 'logger'):
            self.logger.debug(msg)
        else:
            print "[DEBUG]: {0}".format(msg)
