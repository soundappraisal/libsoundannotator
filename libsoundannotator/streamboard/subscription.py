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
import multiprocessing.reduction as reduction
import sys, time
import numpy as np
try:
    from network import NetworkMixin, NoNetworkException, BusyNetworkException, SocketBufferFullException
except AttributeError as e:
    from networkfallback import NetworkMixin, NoNetworkException, BusyNetworkException, SocketBufferFullException
from decimal import *

class NetworkSubscriptionOrder(object):
    def __init__(self, senderKey, receiverKey, IP, port, **kwargs):
        self.senderKey      = senderKey
        self.receiverKey    = receiverKey
        self.IP             = IP
        self.port           = port
        self.type           = kwargs.get('type', 'server')

    def list(self):
        return (self.senderKey, self.receiverKey, self.IP, self.port, self.type,)

class SubscriptionOrder(object):
    def __init__(self, processorName, subscriberName, senderKey, receiverKey, **kwargs):
        self.processorName  = processorName
        self.subscriberName = subscriberName
        self.senderKey      = senderKey
        self.receiverKey    = receiverKey

    def list(self):
        return (self.processorName, self.subscriberName, self.senderKey, self.receiverKey,)

class Subscription(object):

    def __init__(self, connection, subscriptionorder,connectionReduced=False):
        self.connectionReduced=False
        self.connection  = connection
        self.subscriptionorder = subscriptionorder
        if not connectionReduced and not (subscriptionorder.__class__.__name__ == "NetworkSubscriptionOrder"):
            self.__reduceConnection()
            self.connectionReduced=True

        self.senderKey      = subscriptionorder.senderKey
        self.receiverKey    = subscriptionorder.receiverKey

    def __reduceConnection(self):
        # Reduce the connection object to enable sending it
        if(sys.platform=='win32'):
            self.connection = reduction.reduce_pipe_connection(self.connection)
        else:
            self.connection = reduction.reduce_connection(self.connection)

    def riseConnection(self,logger):
        if self.connectionReduced:
            logger.info('Connection for subscription to {0} with channel name {1} has risen!'.format(self.senderKey, self.receiverKey))
            red_conn = self.connection
            self.connection = red_conn[0](*red_conn[1])
            self.connectionReduced=False

        else:
            logger.info('Connection to {0} with channel name {1} had risen already!'.format(self.senderKey, self.receiverKey))

class NetworkConnection(NetworkMixin):
    def __init__(self, config, **kwargs):
        if 'logger' in kwargs:
            self.logger = kwargs.get('logger')
        self.sendTimeout = kwargs.get('sendTimeout', 0.2)
        self.pollTimeout = kwargs.get('pollTimeout', 0.025)
        self.config = config
        self.setupNetworkWithBackoff(kwargs.get('retries', None))
        self.hasData = False
        self.data = None
        self.afterDataCallback = kwargs.get('afterDataCallback', self.callback)

    """Exponential backoff while trying to connect"""
    def setupNetworkWithBackoff(self, retries=None):
        self.connected = False
        gen = self.backoffGenerator()
        tries = 0
        while not self.connected:
            if retries != None and tries > retries:
                #here's when we stop
                break

            try:
                self.setupSocket(self.config,
                    afterdataCallback=self.callback,
                    timeout = self.sendTimeout)
                self.connected = True
                return
            except Exception as e:
                timeout = gen.next()
                self._logError("Unable to connect: {0}. Backoff for {1:.2f}s".format(e, timeout))
                tries += 1
                #do backoff
                time.sleep(timeout)

        self._logError("Unable to connect and max retries reached. Giving up.")

    """Initiate a poll on the socket's data status"""
    def poll(self, timeout=None):
        if timeout == None:
            timeout = self.pollTimeout
        self.pollSockets(timeout)
        return self.hasData

    """Send a chunk of data, wait for a maximum of self.pollTimeout before returning"""
    def send(self, chunk):
        #send data to socket None, which defaults to the only one if there is only one registered
        try:
            self.prepareSend(None, chunk)
            self.pollSockets(self.pollTimeout)
        except NoNetworkException as e:
            self._logError("Unable to send: network disconnected.")
            raise e
        except BusyNetworkException as e:
            self._logError("Unable to send: {0}".format(e))
            raise e
        except SocketBufferFullException as e:
            self._logError("{0}".format(e))
            self.disconnectSocket(None)
            self.connected = False
            raise NoNetworkException(e)

    """Return data if it was callback'ed"""
    def recv(self):
        self.hasData = False
        return self.data

    """Callback for the NetworkMixin to initiate if data was retrieved from the socket"""
    def callback(self, data):
        self.hasData = True
        self.data = data

    """
        Exponential backoff when connection has failed. Feel free to adjust power factor
        or limit.
    """
    def backoffGenerator(self):
        start = 0.025
        power = 1.3 #determines how fast the number grows
        lim = 15 #limit in seconds to wait when connecting
        i = 0
        while True:
            i += 1
            yield min(start*(power**i), lim)
