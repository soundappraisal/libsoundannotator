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
import time, math, pyaudio

#define some custom exceptions
class MicInputOverflowedException(Exception):
	pass
class MicInputException(Exception):
	def __init__(self, value):
		self.value = value
	def __str__(self):
		return repr(self.value)


class MicInput(object):

	def __init__(self, *args, **kwargs):
		#config with defaults
		self.rate = kwargs.get('rate', 44100)
		self.channels = kwargs.get('channels', 1)
		self.format = kwargs.get('format', pyaudio.paInt16)

		'''optional logger from kwargs'''
		logger = kwargs.get('logger', None)
		'''Things having to do with streams, bytes and buffers'''
		#data type conversion from pyaudio stream string to numpy array
		self.dtypes = {
			pyaudio.paInt8: np.int8,
			pyaudio.paInt16: np.int16,
			pyaudio.paInt24: np.int32, #is this right?? probably not :(
			pyaudio.paInt32: np.int32,
			pyaudio.paFloat32: np.float32,
		}
		self.paNames = {
			pyaudio.paInt8: 'paInt8',
			pyaudio.paInt16: 'paInt16',
			pyaudio.paInt24: 'paInt24', #is this right?? probably not :(
			pyaudio.paInt32: 'paInt32',
			pyaudio.paFloat32: 'paFloat32',
		}
		#byte string is longer in size than amount of frames, this is the factor
		self.bytesPerFrame = (self.format / 8) * self.channels
		#assuming that 8K is a safe size
		self.maxBufferSize = kwargs.get('maxBufferSize', 16384)
		#read size may be larger than maxBufferSize. Defaults to half of max buffe
		self.readSize = kwargs.get('readSize', self.maxBufferSize / 4)
		#as a consequence, a too large requested read size will be truncated silently
		self.bufferSize = self.maxBufferSize / 4
		#define a buffer in case more frames than one stream buffer can contain need to be read out
		self.buffer = np.array([], dtype=self.dtypes[self.format]);

		'''Things having to do with actual audio'''
		#registered microphones
		#default ones
		#create a unique set, and add nothing if inputDevice was not a kwarg
		defaultMics = set(["am335x","samson","mic","input"])
		self.inputDevices = set([kwargs.get('inputDevices', "mic")]).union(defaultMics)
		self.pa = pyaudio.PyAudio()
		self.deviceIndex, self.deviceInfo = self.findInputDevice(logger)
		#empty stream
		self.stream = None

		#number of seconds to wait before trying to reset the stream
		self.activityTimer = None
		self.streamTimeout = kwargs.get('streamTimeout', 10.)
		self.clockTolerance = kwargs.get('clockTolerance', 1.0)

	def open(self, logger=None):
		if logger is not None:
			logger.info("Using device {0}".format(self.deviceIndex))
			logger.info('PyAudio format of Microphone stream: {0}'.format(self.format))
		else:
			print "Using device {0}".format(self.deviceIndex)
		try:
			self.stream = self.pa.open( format = self.format,
									channels = self.channels,
									rate = self.rate,
									input = True,
									output = False,
									input_device_index = self.deviceIndex,
									frames_per_buffer = self.maxBufferSize)
			self.chunkStartTime=time.time()
		except Exception as e:
			if logger is not None:
				logger.error("Could not open stream due to Exception: {0}".format(e))
			raise e

	def getRead(self, logger=None):
		if self.stream is not None:
			available = self.stream.get_read_available()
			# Check if startTime is sufficiently close to the clocktime
			self.readtime = time.time()
			if np.abs(self.readtime - self.chunkStartTime) > (self.buffer.size + available)/np.float(self.rate) + self.clockTolerance:
				oldChunkStartTime=self.chunkStartTime
				self.chunkStartTime=self.readtime - (self.buffer.size + available)/np.float(self.rate)

				if logger is not None:
					logger.error("Reset chunkStartTime from : {0} to : {1}".format(oldChunkStartTime,self.chunkStartTime))
			#print "can read {0}, need {1}".format(available, self.bufferSize)
			#if buffer has data, read it
			if (available == 0):
				#have we got anything in the buffer still that is too large?
				if self.buffer.size > self.readSize:
					#split it up
					#print "Need to clean buffer"
					if logger is not None:
						logger.debug("MicInput: Splitting up buffer")
					read = self.buffer[:self.readSize]
					self.buffer = self.buffer[self.readSize:]
					chunkStartTime=self.chunkStartTime
					self.chunkStartTime+=np.float(self.readSize)/np.float(self.rate)
					return read, chunkStartTime
				else:
					#nothing is available, check how long this was the case
					self.monitorActivity(logger)
					return None, None

			else:
				#try and read the stream
				try:
					#read all available untill it is larger than buffer size. In that case, just read what we need
					framesToRetrieve=min(available, self.bufferSize)
					readstring = self.stream.read(framesToRetrieve)
					#no error was raised, so we decide if we have gotten enough frames
					self.activityTimer = time.time()

					read = np.fromstring(readstring, dtype=self.dtypes[self.format])

					#take care of buffering
					#return None when buffer is not full enough yet
					#return a chunk when it's buffered
					return self.appendAndReturnChunkOnFull(read, logger)
				#...but things can still go wrong
				except IOError as e:
					#For instance, a buffer overflow
					if e.strerror == pyaudio.paInputOverflowed:
						if logger is not None:
							logger.error("Mic input overflow")
						raise MicInputOverflowedException(e)
					#Or a yet unknown exception
					else:
						if logger is not None:
							logger.error("Mic input exception: {0}".format(e))
						#propagate the exception sensibly
						raise MicInputException(str(e))
				except Exception as e:
					if logger is not None:
						logger.error("Unknown exception occured: {0}".format(e))
					raise e
		else:
			raise Exception("Trying to read from non-active stream. open() it first!")

	def monitorActivity(self, logger=None):
		if self.activityTimer is not None:
			inactivity = time.time() - self.activityTimer
			if (inactivity > self.streamTimeout):
				if logger is not None:
					logger.warning("Resetting stream because of inactivity")
				self.resetStream()

	def resetStream(self):
		self.close()
		self.open()
		self.activityTimer = time.time()

	def appendAndReturnChunkOnFull(self, frameArray, logger=None):
		remainder = None
		chunk = None
		chunkStartTime=None
		#print("Need to deliver {0} frames, {1} in buffer and got {2}".format(self.readSize, self.buffer.size, frameArray.size))
		#try to decide whether the buffer is full and if we have a remainder
		if self.buffer.size + frameArray.size > self.readSize:
			diff = self.readSize - self.buffer.size
			#append untill the buffer is full, which is readSize - size buffer
			self.buffer = np.append(self.buffer, frameArray[:diff])
			remainder = frameArray[diff:]
			chunk = np.copy(self.buffer)
			if logger is not None:
				logger.debug("MicInput: Return partial buffer")
			#print("too much in read, have remainder of {0}".format(remainder.size))
		elif self.buffer.size + frameArray.size == self.readSize:
			#append everything
			self.buffer = np.append(self.buffer, frameArray)
			chunk = np.copy(self.buffer)
			if logger is not None:
				logger.debug("MicInput: Return full buffer")
			#print("Exactly enough :)")
		else:
			#also append everything, #but don't touch chunk
			self.buffer = np.append(self.buffer, frameArray)
			#print("Too little, buffering")

		#if needed, save remainder as new buffer
		if remainder != None:
			self.buffer = remainder

		if chunk != None:
			chunkStartTime=self.chunkStartTime
			self.chunkStartTime+=np.float(self.readSize)/np.float(self.rate)

		return chunk, chunkStartTime

	def findInputDevice(self, logger=None):
		hasInputChannels = []
		for idx in range(self.pa.get_device_count()):
			devinfo = self.pa.get_device_info_by_index(idx)
			if logger is not None:
				logger.info("Device %d: %s, maxInputChannels: %d" % (idx, devinfo['name'], devinfo['maxInputChannels']))
			else:
				print( "Device %d: %s, maxInputChannels: %d" % (idx, devinfo['name'], devinfo['maxInputChannels']))

			for device in self.inputDevices:
				if device in devinfo["name"].lower() and devinfo['maxInputChannels'] > 0:
					if logger is not None:
						logger.info("Found input device {0} with info {1}".format(idx, devinfo))
					return idx, devinfo
				elif devinfo['maxInputChannels'] > 0:
					hasInputChannels.append(idx)

		if len(hasInputChannels) == 0:
			raise Exception('No suitable input device found')

		return hasInputChannels[0], "No preferred input found; using first device with input channels."

	def close(self):
		if self.isActive():
			try:
				self.stream.close()
			except Exception as e:
				raise e
		try:
			self.pa.terminate()
		except Exception as e:
			raise e

	def isActive(self):
		if self.stream is not None:
			if self.stream.is_active():
				return True

		return False

	def getFormatString(self):
		return self.paNames[self.format]
	def getChannels(self):
		return self.channels
	def getRate(self):
		return self.rate
	def getMaxBufferSize(self):
		return self.maxBufferSize
	def getDeviceInfo(self):
		return self.deviceInfo
	def getDeviceIndex(self):
		return self.deviceIndex

	def __repr__(self):
		return '''MicInput with parameters:
		format: {0},
		rate: {1},
		channels: {2},
		bufferSize: {3}
		maxBufferSize : {4},
		readSize: {5}
		deviceInfo: {6}
		'''.format( self.getFormatString(),
					self.rate,
					self.channels,
					self.bufferSize,
					self.maxBufferSize,
					self.readSize,
					self.deviceInfo)



class MicInputCallback(MicInput):
	
	def __init__(self, *args, **kwargs):
		#config with defaults
		self.callback= kwargs.get('callback', None)
		super(MicInputCallback, self).__init__(*args, **kwargs)
	
	
	def open(self, logger=None):
		if logger is not None:
			logger.info("Using device {0}".format(self.deviceIndex))
			logger.info('PyAudio format of Microphone stream: {0}'.format(self.format))
		else:
			print "Using device {0}".format(self.deviceIndex)
		try:
			self.stream = self.pa.open( format = self.format,
									channels = self.channels,
									rate = self.rate,
									input = True,
									output = False,
									input_device_index = self.deviceIndex,
									frames_per_buffer = self.readSize,
									stream_callback=self.callback)
		except Exception as e:
			if logger is not None:
				logger.error("Could not open stream due to Exception: {0}".format(e))
			raise e


	def getdtype(self):
		return self.dtypes[self.format]
