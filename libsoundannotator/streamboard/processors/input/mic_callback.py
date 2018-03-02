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
import datetime, time
import math, pyaudio, random
import sys, subprocess

from libsoundannotator.streamboard 				import processor
from libsoundannotator.streamboard.continuity 	import Continuity, processorAlignment

from libsoundannotator.io.micinput 			  	import MicInputCallback
from libsoundannotator.io.micinput 			  	import MicInputOverflowedException, MicInputException


def getboottime():
    #for Windows TODO: "wmic os get lastbootuptime", returns local time

	if sys.platform == 'darwin':
		proc = subprocess.Popen(['sysctl', '-a'], stdout=subprocess.PIPE)
		output = subprocess.check_output(('grep', 'kern.boottime'), stdin=proc.stdout)
		idx = output.find('sec = ')+6
		boottime = int(output[idx:idx+10])
	else:

		# Call uptime -s to get a string giving the start time
		proc = subprocess.Popen(['uptime','-s'], stdout=subprocess.PIPE)
		proc.wait()
		datetimestring = proc.stdout.readlines()

		# Convert string to list of integers suitable for the datetime constructor
		datetimelist= datetimestring[0].replace('-',' ').replace(':',' ').replace('\n','').split(' ')
		datetimelist=[int(x) for x in datetimelist]

		# Call the datatime constructor
		dt=datetime.datetime(*datetimelist)

		# Convert datetime to seconds since epoch
		boottime=time.mktime(dt.timetuple())

	return boottime





class Fifo(list):
	def __init__(self):
		self.back = [  ]
		self.append = self.back.append

	def pop(self):
		if not self:
			self.back.reverse( )
			self[:] = self.back
			del self.back[:]
		if self:
			result=super(Fifo, self).pop( )
		else:
			result=None
		return result

	def isempty(self):
		if not self:
			self.back.reverse( )
			self[:] = self.back
			del self.back[:]

		if self:
			result=False
		else:
			result=True

		return result


class MicChunk(object):
	def __init__(self,in_data, frame_count, time_info, status):
		self.in_data =in_data
		self.frame_count =frame_count
		self.time_info=time_info
		self.status=status

class MicInputProcessor(processor.InputProcessor):

	""" Reads samples from the mic.

		Parameters:
		SampleRate: in Hz
		ChunkSize: the number of samples you want to read and return
				   per  chunk
	"""

	def __init__(self, *args, **kwargs):
		self.openMicInput=False
		super(MicInputProcessor, self).__init__(*args, **kwargs)
		self.requiredParameters('SampleRate', 'ChunkSize')
		self.requiredParametersWithDefault( Channels=1)
		self.reader = MicInputCallback (rate=self.config['SampleRate'],
								channels=self.config['Channels'],
								readSize=self.config['ChunkSize'],
								callback=self.callback)
		self.logmsg['info'].append(self.reader)
		self.fifo=Fifo()
		self.boottime=getboottime()

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



	def callback(self,in_data, frame_count, time_info, status):
		#print('Shape {}'.format(len(in_data)))
		self.fifo.append(MicChunk(in_data, frame_count, time_info, status))
		return (None, pyaudio.paContinue)


	def process(self):
		self.currentTimeStamp = time.time() #provide a reasonable default time, for more precision provide timestamp in generateData of the derived class
		data = self.generateData()
		if not data is None:
			self.publish(data, self.continuity, self.getTimeStamp('sound'), self.getchunknumber(), {self.name:self.currentTimeStamp}, metadata=self.getMetaData())


	def generateData(self):

		if self.fifo.isempty():
			return None
		else:
			micchunk=self.fifo.pop()

		frames = np.fromstring(micchunk.in_data, dtype=self.reader.getdtype())
		#self.currentTimeStamp=time.time()
		self.timeStamp=micchunk.time_info['input_buffer_adc_time']+self.boottime
		

		dataout=dict()
		dataout['sound'] = frames

		#If in the previous chunk we got invalid continuity, mark this chunk as discontinuous
		if self.continuity == Continuity.invalid:
			self.continuity = Continuity.discontinuous
		else:
			self.continuity = Continuity.withprevious

		return dataout


	def finalize(self):
		self.reader.close()
		super(MicInputProcessor, self).finalize()

	def getTimeStamp(self,key):
		return self.timeStamp
		
		
	def setProcessorAlignments(self): 
		'''
		 setProcessorAlignments: assign empty dict to self.processorAlignments   
		'''
		self.processorAlignments=dict()
		self.processorAlignments['sound']=processorAlignment(fsampling=self.getsamplerate('sound'))


	def getMetaData(self):
		
		return  {self.name: super(MicInputProcessor, self).getMetaData()}
