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
# -*- coding: u8 -*-
import multiprocessing, math, time, pyaudio, sys, setproctitle, os,  traceback
import numpy as np
import logger as streamboard_logger
import logging
import multiprocessing.connection


from continuity     import Continuity, chunkAlignment, processorAlignment
from messages       import BoardMessage, NetworkMessage, ProcessorMessage
from compositor     import compositeChunk, compositeManager, DataChunk
from subscription   import NetworkConnection, NetworkSubscriptionOrder, Subscription
from json import loads, dumps
from hashlib import sha1

try:
    from network        import NoNetworkException, ClosedSocketException, NotSameSocketException, BusyNetworkException
except AttributeError as e:
    from networkfallback import NoNetworkException, ClosedSocketException, NotSameSocketException, BusyNetworkException

class BaseProcessor(multiprocessing.Process):
    defaultConfig = {
        'BoardConnectionTimeOut': 0.01,
        'InputConnectionTimeOut': 0.025,
        'network': False,
        'NetworkTimeout': 10
    }

    def __init__(self, boardConn, name, logdir=None, loglevel=None, **kwargs):
        super(BaseProcessor, self).__init__()
        # Don't use logging before calling addloger
        if(sys.platform=='win32'):
            self.loglevel=loglevel
        else:
            self.loglevel=loglevel

        self.logdir = logdir

        self.logmsg = self.__createConfig(kwargs)
        self.boardConn = boardConn

        self.name = name

        self.currentTimeStamp = time.time()
        self.sources=set([self.name])
        self.overwriteContinuity = True

    def addlogger(self, reattach=True):
        filepath = os.path.join(self.logdir, '{0}.log'.format(self.name))
        formatter = logging.Formatter('%(asctime)s %(name)-15s %(levelname)-8s %(processName)-10s %(message)s')
        self.handler = logging.handlers.RotatingFileHandler(filepath,
            maxBytes=1000000,
            backupCount=10)
        self.handler.setFormatter(formatter)

        self.logger = logging.getLogger(self.name)
        self.logger.setLevel(self.loglevel)
        self.logger.addHandler(self.handler)

        self.logger.info("=============Logger was attached to Processor {0}============".format(self.name))

        #print any stored messages
        for level in ['debug','info','warning','error','exception','critical']:
            if len(self.logmsg[level]) != 0:
                attr = getattr(self.logger, level)
                for msg in self.logmsg[level]:
                    attr('Stored message: {0}'.format(msg))


    def prerun(self):
        """ Override this class to do things before starting the
            processor.
        """
        self.addlogger()

    def run(self):
        self.prerun()
        setproctitle.setproctitle(self.name)
        self.logger.info('Processor {0} started'.format(self.name))
        self.stayAlive = True

        self.checkAndProcessBoardMessage()
        
        '''
            Main loop
            
            This loop is fortified with a try catch statement sending all error to the board. The board can then act accordingly.
            
            First application: catching errors during testing.
            
            Potential: Can be used to stop a processor and launch a new clean one. However that is not trivial.
            
        '''
        
        while self.stayAlive:
            
            try:
                self.process()
                self.checkAndProcessBoardMessage()
            except Exception as e:
                messageString=['{0}'.format(e.__class__.__name__),'{0}'.format(e),self.name,]
                traceback.print_exc()
                messagetoboard=ProcessorMessage(ProcessorMessage.error,messageString)
                self.boardConn.send(messagetoboard)
                
        self.logger.debug('Running finalize on processor {0}'.format(self.name))
        self.finalize()

    def process(self):
        """ This def gets called every cycle. Should be overriden and
            implemented in subclasses
        """
        self.overrideError('process')

    def processCustomBoardMessage(self, message):
        """ Override this function to process custom board messages
        """
        pass

    def finalize(self):
        """ Override to do anything after processor stops. Like clean
            up and free resources.
        """
        self.logger.debug("Finalize in BaseProcessor called")
        if hasattr(self, 'listener'):
            self.listener.close()

    def checkAndProcessBoardMessage(self):
        m = self.checkForBoardMessage()
        if m:
            self.processBoardMessage(m)

    def checkForBoardMessage(self):
        hasNew = self.boardConn.poll(self.config['BoardConnectionTimeOut'])
        if hasNew:
            try:
                message = self.boardConn.recv()
                return message
            except EOFError:
                self.logger.error(
                'Board connection closed. This should not happen! Quitting processor {0}'
                .format(self.name)
                )
                self.stayAlive = False
                return None
            self.logger.debug('Received boardmessage {0} on processor {1}'
            .format(message.getType(), self.name))
        return False

    def processBoardMessage(self, message):
        """ Processes a BoardMessage
        """
        if message.getType()==BoardMessage.stop:
            self.logger.info('Received stop message on processor {0}, stopping'.format( self.name))
            self.stayAlive = False
        elif message.getType()==BoardMessage.testrequiredkeys:
            self.testRequiredKeys(message)
        else:
            self.procesCustomBoardMessage(message)

    def procesCustomBoardMessage(self, message):
        self.overrideError('process received board message for which no handler was defined messagetype: {0}'.format(message.getType()))

    def testRequiredKeys(self,message):
        subscriptionReceiverKeys=message.getContents()

        if  hasattr(self,'requiredKeys'):
            for receiverKey in subscriptionReceiverKeys:
                if not receiverKey in self.requiredKeys:
                    raise ValueError(
                        'Trying to subscribe to processor {0} with unknown key {1}. Subscriptions should only provide required keys.'
                        .format(self.name, receiverKey)
                    )


            for requiredKey in self.requiredKeys:
                if not requiredKey in subscriptionReceiverKeys:
                    raise ValueError(
                        'RequiredKey {0} is missing in subscription for processor {1}. Subscriptions should  provide all required keys.'
                        .format(requiredKey, self.name)
                    )
        else:
            if len(subscriptionReceiverKeys)>0:
                raise ValueError(
                            'Trying to subscribe to processor {0} a processor which requires no input from other processors. Subscriptions should only provide required keys.'
                            .format(self.name)
                        )

    def overrideError(self, functionName):
        self.logger.error(
        'Definition for {0} should be overriden. Processor {1} will stop'
        .format(functionName, self.name))
        self.stayAlive = False

    def requiredParameters(self, *pars):
        for par in pars:
            if not par in self.config:
                self.logmsg['error'].append('{0} not set, this wil lead to problems!'.format(par))
                raise ValueError('{0} not set on processor {1}'.format(par,self.name))

    def requiredParametersWithDefault(self, **pars):
        for (par, default) in pars.items():
            if not par in self.config:
                self.logmsg['info'].append('{0} not set, using default value: {1}'
                .format(par, default))
                self.config[par] = default

    def __createConfig(self, kwargs):
        """ Creates the config dictionary and sets all fields according
            to the defaultConfig or override from keyword parameters.
        """
        self.config = dict()

        #store logger messages because logger is not yet configured
        logmsg = {
            'debug': [],
            'info': [],
            'warning': [],
            'error': [],
            'exception': [],
            'critical': []
        }

        for par in BaseProcessor.defaultConfig:
            if par in kwargs:
                logmsg['debug'].append('Setting config parameter {0} to {1}'
                .format(par, kwargs[par]))
                self.config[par] = kwargs[par]
            else:
                logmsg['debug'].append('Setting config parameter {0} to default value {1}'
                .format(par, BaseProcessor.defaultConfig[par]))
                self.config[par] = BaseProcessor.defaultConfig[par]

        for par in kwargs:
            logmsg['debug'].append('Setting config parameter {0} to {1}'
            .format(par, kwargs[par]))
            self.config[par] = kwargs[par]

        return logmsg

class InputProcessor(BaseProcessor):
    """ Start of the line. Creates input for other processors has
        subscribers as well!
    """

    def __init__(self, boardConn, name, **kwargs):
        super(InputProcessor, self).__init__(boardConn, name, **kwargs)
        self.subscriptions = dict()
        
        #genesis chunk
        self.oldchunk = DataChunk([],dict(), 0, self.name, set([self.name]), number=0)
        self.continuity=Continuity.discontinuous
        
    def prerun(self):
        super(InputProcessor, self).prerun()
        #if processor has network property, set it up
        if self.config['network'] != False:
            #add client property (implicit through this config)
            self.config['network']['type'] = 'client'
            self._subscribeNetwork(self.config['network'])
        
    def generateData(self):
        """ Override this function with one that actually generates input
        """
        self.overrideError('generateData')

    def process(self):
        self.currentTimeStamp = time.time() #provide a reasonable default time, for more precision provide timestamp in generateData of the derived class
        data = self.generateData()
        self.publish(data, self.continuity, self.getTimeStamp(None), self.getchunknumber(), {self.name:self.currentTimeStamp}, metadata=self.getMetaData())

    def getchunknumber(self):
        return self.oldchunk.number+1

    def getsamplerate(self,key):
        return self.config['SampleRate']

    def getTimeStamp(self,key):
        return self.currentTimeStamp

    def publish(self, data, continuity, starttime,number,generationTime, 
                    metadata=None, identifier=None):
        #initialize chunk
        chunk = None
        if identifier is None:
          identifier = self.__class__.__name__


        '''=== Some sanity checks to perform before publishing ==='''
        # If no data is given, return. This will prevent the system collapsing when a Processor
        # already has a check for subscriptions but chooses to continue anyway
        if data is None:
            self.logger.info("Processor {0} generated empty data, not publishing".format(self.name))
            return

        data['technicalkey']=None
        for subscriptionorder, subscriber in self.subscriptions.viewitems():
            self.logger.info('Processor {0} publishing with sendingKey:{1} receiverKey:{2} continuity:{3} '.format(self.name,subscriber.senderKey,subscriber.receiverKey, continuity))

            #wildcard discards data
            if (subscriber.senderKey == '*'):
                dataout = None
            else:
                dataout=data[subscriber.senderKey]
                if type(dataout) is np.ndarray:
                    if dataout.shape[-1] == 0:
                        raise ValueError("Empty 2d array produced. Please consider removing processor {} sending {} or increasing chunk size!".format(self.name,subscriber.senderKey))

            chunk = DataChunk(dataout,
                starttime,
                self.getsamplerate(subscriber.senderKey),
                self.name,
                self.sources,
                continuity=continuity,
                number=number,
                alignment=self.getAlignment(subscriber.senderKey),
                dataGenerationTime = generationTime,
                metadata = metadata,
                identifier = identifier,
            )
            try:
                subscriber.connection.send(chunk)
            except NoNetworkException as e:
                self.logger.info("Initiating reconnect")
                subscriber.connection.setupNetworkWithBackoff()
            except BusyNetworkException as e:
                #thrown when network buffer is full
                #don't send anything, but mark the continuity as discontinuous
                self.continuity = Continuity.discontinuous

        #TODO why this code? It interferes with the last chunk continuity...
        if (len(self.subscriptions) > 0): # Make sure oldchunk exists
            self.oldchunk=chunk
            #hacky way of preventing overwriting from continuity, when also set in a processor
            if self.overwriteContinuity:
                self.continuity=chunk.continuity
            chunk.data=None

        self.logger.debug('Processor {0} published output with startTime {1}, continuity is now {2}' .format(self.name,self.currentTimeStamp, self.continuity))

    def processBoardMessage(self, message):
        if message.getType()==BoardMessage.subscribe:
            self.logger.info('Received subscription message: ' + str(message.getContents()))
            subscription = message.getContents()
            self._subscribe(subscription)
        else:
            super(InputProcessor, self).processBoardMessage(message)

    def _subscribeNetwork(self, config):
        order = NetworkSubscriptionOrder(config['senderKey'],
            'network({0}:{1})'.format(config['interface'],config['port']),
            config['interface'],
            config['port'],
            type='client'
        )
        try:
            connection = NetworkConnection(config, logger=self.logger)
            subscription = Subscription(connection, order)
            self.subscriptions[subscription.subscriptionorder.list()] = subscription
            self.logger.info('Subscribed a new network connection to processor {0}. Now have {1} subscribers'
                .format(self.name, len(self.subscriptions)))
        except Exception as e:
            self.logger.error("Could not create network subscription: {0}".format(e))

    def _subscribe(self, subscription):
        subscription.riseConnection(self.logger)
        #replace connection config with real connection in case of network
        if "Network" in subscription.subscriptionorder.__class__.__name__:
            subscription.connection = NetworkConnection(subscription.connection,
                logger=self.logger
            )

        self.subscriptions[subscription.subscriptionorder.list()]= subscription
        self.logger.info('Subscribed a new connection to processor {0}. Now have {1} subscribers.'
        .format(self.name,len(self.subscriptions)))
    
         
    def getMetaData(self):
        config_json=dumps(self.config, sort_keys=True)
        config_hash=sha1(config_json).hexdigest()
        return  config_hash, config_json
    
    def getAlignment(self,key):
        chunkalignment=chunkAlignment(fsampling=self.getsamplerate(key))
        
        
        
        if key in self.processorAlignments:
            #self.logger.error('========== type of fsampling: {0} and value {1}'.format(type(self.processorAlignments[key].fsampling),self.processorAlignments[key].fsampling))
            #self.logger.error('========== type of self.alignment_in: {0} and value {1}'.format(type(self.processorAlignments[key] ),self.processorAlignments[key] ))
            #self.logger.error('========== type of self.processor.processorAlignments: {0} and value {1}'.format(type(self.processorAlignments),self.processorAlignments ))
            if self.processorAlignments[key].fsampling is None:
                raise ValueError('fsampling should be set on processor {0} for key {1}'.format(self.name,key))
            return chunkalignment.impose_processor_alignment(self.processorAlignments[key])
        
        return chunkalignment
    
    
        
    def setProcessorAlignments(self):        
        ''' 
        setProcessorAlignments: this function should set the dictionary self.processorAlignments. 
        
        minimal implementation: self.processorAlignments=dict()
        '''
        self.overrideError('setProcessorAlignments')

        
class Processor(InputProcessor):
    """ Processor that gets input from one or more other processors,
        processes that input and publishes the result to subscribers
    """
    requiredKeys=[]
    previousClaimNumber=-1

    def __init__(self, boardConn, name, **kwargs):
        super(Processor,self).__init__(boardConn, name, **kwargs)
        self.inConn = []
        self.timeout=self.config['InputConnectionTimeOut']


    def prerun(self):
        super(Processor, self).prerun()
        self.compositeManager=compositeManager(self.requiredKeys, self)

    def processData(self, data):
        self.overrideError('processData')

    def process(self):
        self.currentTimeStamp = time.time() #provide a reasonable default time, for more precision provide timestamp in generateData of the derived class
        data = self.getInputs()

    def finalize(self):
        self.logger.warning("=================Finalize in Processor called===================\n\n")
        """ Close the bound socket on finalize """
        super(Processor, self).finalize()

    def getInputs(self):
        for idx, subscription in enumerate(self.inConn):
            try:
                new = subscription.connection.poll(self.timeout)
            except (ClosedSocketException, NotSameSocketException) as e:
                self.logger.error("Recoverable incoming socket error. Need to re-initialize: {0}".format(e))
                new = False

            if new:
                try:
                    self.logger.debug("Got new. Calling blocking recv()")
                    dataChunk = subscription.connection.recv()
                    self.logger.debug(dataChunk)
                except Exception as e:
                    self.logger.error("Could not recv data: {0}".format(e))
                    dataChunk=None

                if not dataChunk is None:
                    self.compositeManager.inject(subscription.receiverKey, dataChunk)


    def processBoardMessage(self, message):
        self.logger.debug(' Processor {0}  received BoardMessage' .format(self.name))

        if message.getType()==BoardMessage.subscription:
            subscription = message.getContents()
            self.__subscription(subscription)
        elif message.getType()==BoardMessage.networksubscription:
            subscription = message.getContents()
            self.__subscription(subscription)
        else:
            super(Processor, self).processBoardMessage(message)

    def __subscription(self, subscription):
        subscription.riseConnection(self.logger)
        #replace connection config with real connection in case of network receiver
        if "Network" in subscription.subscriptionorder.__class__.__name__:
            subscription.connection = NetworkConnection(subscription.connection,
                logger=self.logger
            )

        self.inConn.append(subscription)
        noofInputs=len(self.inConn)
        if(noofInputs>0):
            self.timeout=self.config['InputConnectionTimeOut']/noofInputs

        self.logger.info('New input subcription for processor {0}. Now have {1} subcriptions.'
        .format(self.name,len(self.inConn)))

    def getTimeStamp(self,key):
        return self.compositeManager.startTime
   
    def getAlignment(self,key):
        return self.compositeManager.getAlignment(key)
        
    
        
class OutputProcessor(Processor):
    """ Processor that gets input from one or more processors
        and processes this to something outside of the framework
        fits GUI's and filewriters.
    """

    def processBoardMessage(self, message):
        self.logger.debug('{0} received BoardMessage'.format(self.name))
        if message.getType()==BoardMessage.subscribe:
            self.logger.error(' Output processor {0} incorrectly received subscription request '.format(self.name))
        else:
            super(OutputProcessor, self).processBoardMessage(message)

    def publish(self,result,continuity, starttime, number, generationTime, *args, **kwargs):
        pass
