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
import numpy as np
import time, math, pyaudio, random, sys

from libsoundannotator.streamboard 				import processor
from libsoundannotator.streamboard.continuity 	import Continuity, processorAlignment

from libsoundannotator.io.micinput 			  	import MicInput
from libsoundannotator.io.micinput 			  	import MicInputOverflowedException, MicInputException

class MicInputProcessor(processor.InputProcessor):

	""" Reads samples from the mic.

		Parameters:
		DeviceIndex: set to the OS sound device index you want to use
					 for input
		SampleRate: in Hz
		ChunkSize: the number of samples you want to read and return
				   per  chunk
	"""

	format = pyaudio.paInt16

	def __init__(self, *args, **kwargs):
		self.openMicInput=False
		super(MicInputProcessor, self).__init__(*args, **kwargs)
		self.requiredParameters('SampleRate', 'ChunkSize')
		self.requiredParametersWithDefault(DeviceIndex=0, Channels=1,Microphone=None)
		self.reader = MicInput(rate=self.config['SampleRate'],
								channels=self.config['Channels'],
								readSize=self.config['ChunkSize'],
								inputDevices=self.config['Microphone'])
		self.logmsg['info'].append(self.reader)
		self.samplerate=self.config['SampleRate']

	def prerun(self):
		super(MicInputProcessor, self).prerun()
		self.setProcessorAlignments()

		self.stayAlive = True
		while self.stayAlive:
			self.checkAndProcessBoardMessage()
			#only open stream the moment we get subscribers
			if(len(self.subscriptions) > 0):
				try:
					self.reader.open(self.logger)
				except Exception as e:
					self.logger.error("Unable to open input reader: {0}".format(e))
					self.finalize()
					sys.exit(1)

				self.openMicInput =True
				self.stayAlive = False #make sure we get out of the while loop
		#set true again
		self.stayAlive = True

	def generateData(self):
		dataout=dict()
		if(self.reader.isActive()):
			#read blocks until the requested amount of frames can be returned
			#or until an error with the stream occurs
			try:
				frames, self.timeStamp = self.reader.getRead(self.logger)
				self.logger.info('frames: {0}'.format(frames))

			#we don't want to raise 'e' because input overflow might happen once in a while
			except MicInputOverflowedException as e:
				self.continuity = Continuity.invalid
				self.logger.critical('MicInput pyaudio.paInputOverflowed: {0}'.format(e))
				return None

			except MicInputException as e:
				self.logger.error("Something went wrong with the microphone input: {0}".format(e))
				raise e

			except Exception as e:
				self.logger.error("An unknown exception occured when reading the microphone: {0}".format(e))
				raise e

			#return early if we got nothing
			if frames is None:
				return frames

			#If in the previous chunk we got invalid continuity, mark this chunk as discontinuous
			if self.continuity == Continuity.invalid:
				self.continuity = Continuity.discontinuous
			else:
				self.continuity = Continuity.withprevious

			dataout['sound'] = frames
			return dataout

		#in case reader is not active
		else:
			self.logger.warning("The microphone stream is not active")
			return None

	def finalize(self):
		self.reader.close()
		super(MicInputProcessor, self).finalize()
		
	def getTimeStamp(self,key):
		return self.timeStamp

	def getsamplerate(self, key):
		return self.samplerate


	def setProcessorAlignments(self): 
		'''
		 setProcessorAlignments: assign empty dict to self.processorAlignments   
		'''
		self.processorAlignments=dict()
		self.processorAlignments['sound']=processorAlignment(fsampling=self.getsamplerate('sound'))


	def getMetaData(self):
		
		return  {self.name: super(MicInputProcessor, self).getMetaData()}
