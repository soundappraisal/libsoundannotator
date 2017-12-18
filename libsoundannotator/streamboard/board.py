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
Streamboard:
This file contains the architectural basis for the streamboard architecture.

A streamboard is an instance of the Board class.

The board class is designed to manage processors which depend on each other
for input and output processing. Example processor can be found in processors.py.

Processor types provided in this file:
    BaseProcessor: implements functionality shared among all processors

    InputProcessor: processor that generates data or reads data from a
    file or stream, and publishes to its subsribers

    Processor: processor that subscribes to another processor to obtain its
    data and to process this data and subsequently publish the processed results
    to its subscribers

    OutputProcessor: processor that subscribes to another processor to obtain its
    data and to process this data and output the data to file or screen.

In addition it is possible to obtain a connection object to a process for usage in the main process.


Authors:
    Coen Jonker
    Ronald van Elburg
    Arryon Tijsma



Example usage pattern:
    # Create Board:
    b = Board()

    # Start input processor, in this case a process
    # that translates a stream in to chunks data:
    b.startProcessor('myMicInput', MicInput)

    # Connect input processor to cochlear model
    b.startProcessor('myTFProcessor', tf_Processor, 'myMicInput')

    # Obtain a connection to use in main process
    toMyCochleogram=b.getConnectionToProcessor('myCochleogram')
'''

from continuity     import Continuity
from subscription   import Subscription, SubscriptionOrder, NetworkSubscriptionOrder
from messages       import BoardMessage, NetworkMessage

import logger
import multiprocessing, time, sys, os, logging, logging.config, logging.handlers
from _multiprocessing import Connection
import threading

class Board(object):
    """ General managing class. Starts and stops streams. Handles
        communication between processors. Contains logging.
    """

    def __init__(self,loglevel=logging.INFO, logdir=os.path.expanduser('~'), logfile='libsoundannotator'):
        self.loglevel=loglevel
        self.logdir = logdir
        self.logfile = logfile

        self.processors = dict()
        self.testprocessors=dict()
        self.connections = list()
        self.heartbeats = dict()

        #for internal use
        self._BoardConnectionTimeOut = 0.01
        self._heartBeatTimeout = 0.1
        self._firstTimeMonitor = True

        self.addLogger()

    def addLogger(self):
        filepath = os.path.join(self.logdir, '{0}.log'.format(self.logfile))
        formatter = logging.Formatter('%(asctime)s %(name)-15s %(levelname)-8s %(processName)-10s %(message)s')
        self.handler = logging.handlers.RotatingFileHandler(filepath,
            maxBytes=1000000,
            backupCount=10)
        self.handler.setFormatter(formatter)

        self.logger = logging.getLogger(self.logfile)
        self.logger.setLevel(self.loglevel)
        self.logger.addHandler(self.handler)

        self.logger.info("Logger was attached to Board {0}".format(self.logfile))


    def subscribeToNetwork(self, subscriptionorder, subscribing_processorName):
        """ Subscribe a network connection to a processor

            subscriptionorder                   the network subscription properties
            subscribing_processorName           name of the subscribing processor
        """
        if subscribing_processorName in self.processors:
            self.logger.info("Creating network connection to {0}".format(subscribing_processorName))

            (instance, fromBoard) = self.processors[subscribing_processorName]

            #create network connection from subscriptionorder
            serverconfig = {
                'interface': subscriptionorder.IP,
                'port': subscriptionorder.port,
                'type': 'server'
            }

            fromBoard.send(BoardMessage(BoardMessage.networksubscription, Subscription(serverconfig, subscriptionorder)))

            return True

        else:
            self.logger.error('Trying to obtain connection to unknown processor {0}'
                .format(input_processorName))
            return


    def subscribeToProcessor(self, subscriptionorder, subscribing_processorName):
        """ Subscribe a connection to a processor and post the other
            end of the Pipe to the receiving Processor

            subscriptionorder.processorName     the processor that will send data to the subscriptionorder
            subscribing_processorname           the processor that will receive data from the subscription
        """

        if subscriptionorder.processorName in self.processors:

            #check if subscribing processor exists
            if not subscribing_processorName in self.processors:
                self.logger.error("Trying to create a subscription to unknown subscribing processor: {0}".format(subscribing_processorName))
                return

            self.logger.info('Creating Pipe from {0} to {1}'.format(subscriptionorder.processorName,subscribing_processorName))

            (input_instance, input_connection) = self.processors[subscriptionorder.processorName]
            (subscribing_instance, subscribing_connection)= self.processors[subscribing_processorName]

            (toInput, toProcessor) = multiprocessing.Pipe()

            self.connections.append((toInput, toProcessor))
            self.logger.debug('Sending subscription message')
            
            subscriptionmessage=BoardMessage(BoardMessage.subscribe,Subscription(toInput,subscriptionorder) )
            
            if type(input_connection) == Connection:
                input_connection.send(subscriptionmessage)
            else:
                input_connection.processBoardMessage(subscriptionmessage)
            
            subscriptionmessage=BoardMessage(BoardMessage.subscription, Subscription(toProcessor,subscriptionorder))

            if type(subscribing_connection) == Connection:
                subscribing_connection.send(subscriptionmessage)
            else:
                subscribing_connection.processBoardMessage(subscriptionmessage)
                
            return True

        self.logger.error('Trying to obtain connection to unknown processor {0}'
        .format(input_processorName))
        return


    def getConnectionToProcessor(self,subscriptionorder):
        """ get a connection to a processor and return the other
            end of the Pipe
        """

        if subscriptionorder.processorName in self.processors:

            self.logger.info('Creating Pipe from main process to {0}'.format(subscriptionorder.processorName))


            (input_instance, input_connection) = self.processors[subscriptionorder.processorName]
            (toInput, toProcessor) = multiprocessing.Pipe()
            self.connections.append((toInput, toProcessor))
            
                      
            subscriptionmessage=BoardMessage(BoardMessage.subscribe, Subscription(toInput,subscriptionorder) )
            
            if type(input_connection) == Connection:
                input_connection.send(subscriptionmessage)
            else:
                input_connection.processBoardMessage(subscriptionmessage)

            return Subscription(toProcessor,subscriptionorder)

        self.logger.error('Trying to obtain connection to unknown processor {0}'.format(subscriptionorder.processorName))
        return None

    def startProcessor(self, processorName, processorClass, *subscriptionorders, **kwargs):
        if processorName in self.processors:
            self.logger.error(
            'Trying to start processor with duplicate name {0}. Processors must have unique names.'
            .format(processorName))
            return

        (fromBoard, toInstance) = multiprocessing.Pipe()
            
        self.logger.debug("creating instance of {0}".format(processorName))
        instance = processorClass(toInstance, processorName, logdir=self.logdir, loglevel=self.loglevel, **kwargs)

        self.processors[processorName] = (instance, fromBoard)
        instance.start()

        # Let processor check whether provided subscriptions fit the required keys, processor
        # will raise ValueErrors is not correct.

        subscriptionReceiverKeys=[subscriptionorder.receiverKey for subscriptionorder in subscriptionorders]
        fromBoard.send(BoardMessage(BoardMessage.testrequiredkeys,subscriptionReceiverKeys))


        # After passing checks create the subscriptions
        for subscriptionorder in subscriptionorders:
            # First condition merely indicates that we cannot check this condition for processors initiated outside this board.
            if subscriptionorder.__class__.__name__ == 'SubscriptionOrder' and not (subscriptionorder.processorName in self.processors):
                raise ValueError('Trying to start processor {0} with input from nonexisting processor {1}. Processors providing input must exist.'
                    .format(processorName, subscriptionorder.processorName))

            if subscriptionorder.__class__.__name__ == 'NetworkSubscriptionOrder':
                self.logger.info('Subscribing {0} to data from network {1}:{2}'
                    .format(processorName, subscriptionorder.IP, subscriptionorder.port))

                self.subscribeToNetwork(subscriptionorder, processorName)

            else:
                self.logger.info('Subscribing {0} to {1}'
                    .format(subscriptionorder.processorName, processorName))

                #subscribe each SubscriptionOrder to the processor 'processorName'
                self.subscribeToProcessor(subscriptionorder,processorName)

    


    def stopProcessor(self, processorName):
        if processorName in self.processors:
            self.logger.info('Stopping processor {0}'
            .format(processorName))

            (instance, connection) = self.processors[processorName]


            self.logger.debug('Sending stop message to processor {0}'
            .format(processorName))

            if type(connection) == Connection:
                connection.send(BoardMessage(BoardMessage.stop,None))
            else:
                pass # leave it to Garbage Collector the processor is onBoard
                
            '''
            Earlier we issued a join here, however because join was also issued by the framework after leaving the run loop we elicited an assertion error in the multiprocessing module. This lead to non gracefull termination of the processes and loss of data.
            '''
        else:
            self.logger.error('Trying to stop nonexistent processor {0}'
            .format(processorName))

    def checkForProcessorData(self, name, connection):
        if connection.poll(self._BoardConnectionTimeOut):
            try:
                data = connection.recv()
                return data
            except EOFError:
                self.logger.error(
                'Connection from processor closed. This should not happen! Quitting processor {0}'
                .format(name)
                )
                self.stayAlive = False
                return None
        return False

    def exitOnFalseProcessor(self):
        for processorName in self.processors:
            if not self.processors[processorName][0].is_alive():
                self.logger.warning("Processor {0} is inactive. Stopping whole chain".format(processorName))
                self.stop()

    def isHealthy(self):
        healthy=True
        for processorName in self.processors:
            if not self.processors[processorName][0].is_alive():
                self.logger.warning("Processor {0} is inactive.".format(processorName))
                healthy=False

        return healthy

    def stopallprocessors(self):
        for processorName in self.processors:
            self.stopProcessor(processorName)

        for connection in self.connections:
            connection[0].close()

        self.connections=list()


    def stop(self,*args):
        self.stopallprocessors()
        self.logger.info("Terminating a Board")
        logging.shutdown()
