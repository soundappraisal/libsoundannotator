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
import socket, sys, select, struct, cPickle, time, lz4, zlib

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

class SocketStateMeta(type):
	def __getattr__(cls, key):
		if key in cls.states:
			return str(key)
		else:
			return None

class SocketState(object):
	__metaclass__ = SocketStateMeta

	states = {
		'READYSEND': "readysend", #ready to send data
		'SENDING' : "sending", #we are sending data
		'RECEIVING' : "receiving", #we are receiving data
		'PACKAGE' : "package", #we have retrieved the package information
		'END' : "end", #we are done sending or receiving
	}

class NetworkMixin(object):
	_sockets = {}
	_socketstates = {} #volatile
	_socketmsglengths = {} #volatile
	_socketpoll = select.poll()
	_socketfrmt = struct.Struct('!I') #struct format can contain 32bits to indicate size
	_socketbuffer = 8192 #8K for now, max buffer on Ubuntu 14.04 can be 65K
	_socketdata = {} #volatile
	_socketdataMaxSize = 10000000 #which is 10MB. Let's make it large ;).
	_sockettimers = {} #volatile
	_listen_sock = None
	_afterdataCallback = None
	_networkType = None

	_sendTimeout = 0.0

	_useCompression = True

	def setupSocket(self, config, **kwargs):
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

		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #create socket object
		sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) #re-use socket address
		sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1) #no delay, send immediately

		if config['type'] == 'server':
			self._logInfo("Setting up socket server {0}:{1}".format(config['interface'],config['port']))
			try:
				sock.bind((config['interface'], config['port']))
				sock.listen(socket.SOMAXCONN) #queued connections (depending on OS, Ubuntu: 128)
				#create hidden class variable _listen_sock, which accepts new connections
				self._listen_sock = sock
				self._socketpoll.register(sock, select.POLLIN) #register socket to receive
			except Exception as e:
				self._logError("Something went wrong binding the listening socket: {0}".format(e))
				raise e

		elif config['type'] == 'client':
			self._logInfo("Setting up socket client")
			try:
				sock.connect((config['interface'], config['port']))
				sock.setblocking(False)
				sock.shutdown(socket.SHUT_RD) #we never read from the socket
				self._socketpoll.register(sock, select.POLLOUT) #register socket to send
			except Exception as e:
				self._logError("Something went wrong binding the connecting socket: {0}".format(e))
				raise e

		self._networkType = config['type']

		#for both options, save the socket into _sockets
		self._sockets = { sock.fileno(): sock }
		#register the afterdataCallback
		afterData = kwargs.get('afterdataCallback', None)
		if afterData != None:
			self._logInfo("Registered afterdataCallback")
			self._afterdataCallback = afterData

		#set timeout, this defines the max allowed time to loop while sending
		self._sendTimeout = kwargs.get('timeout', 0.0)

	def pollSockets(self, maxTimeout, recvNo=None): #timeout in seconds please :)
		if self._networkType == 'server':
			self._recvSockets(maxTimeout, recvNo)
		elif self._networkType == 'client':
			self._sendSockets(maxTimeout)
		else:
			self._logError("Unknown network connection type: {0}".format(self._networkType))

	def closeSockets(self):
		for fd in self._sockets:
			self._logInfo("Closing socket {0}".format(fd))
			sock = self._sockets[fd]
			#crucial step: unregister with select, otherwise the file descriptor will be incorrect in the future
			self._socketpoll.unregister(sock)
			#shutdown both ends of the pipe
			sock.shutdown(socket.SHUT_RDWR)
			sock.close()

	def disconnectSocket(self, sock):
		#sock may be none if we have only one socket
		if sock == None:
			#if instead we have no sockets, a disconnect might have happened
			if len(self._sockets) == 0:
				raise NoNetworkException("No connected sockets")
			#if one socket present
			if len(self._sockets) == 1:
				#just pick the first and only socket
				sock = self._sockets[self._sockets.keys()[0]]
			#if more than one socket present, specifying None won't do :)
			else:
				raise NetworkConfigError("Got 'disconnectSocket' with 'None' as socket but have more than one socket: {0}".format(len(self._sockets)))
		#we could get a socket which is not in our socket list. Possible malicious attempt
		else:
			if not sock.fileno() in self._sockets:
				raise NetworkConfigError("Socket provided to 'disconnectSocket' not in socket list: {0}".format(sock.fileno()))

		fd = sock.fileno()
		self._socketpoll.unregister(fd)
		del self._sockets[fd]
		self._socketstates.pop(sock, None)
		self._socketdata.pop(sock, None)
		self._socketmsglengths.pop(sock, None)
		return


	def _sendSockets(self, maxTimeout):
		start = time.time()
		"""
			For sending, we wrap the whole polling mechanism in a time loop.
			Essentially, a client will always be ready when the buffer is not full. This loop
			ensures that in the given time (by maxTimeout), we send as much data as possible
		"""
		while time.time() < start + maxTimeout:
			#we wait for the maximum allowed time when polling.
			#this will do nothing if a socket is not generating an event,
			#but will return sooner if an event is available
			for fd, event in self._socketpoll.poll(maxTimeout * 1000): #expects timeout in milliseconds
				sock = self._sockets[fd]

				#reset ended socket
				if (sock in self._socketstates) and (self._socketstates[sock] == SocketState.END):
					self._logDebug("auto remove socket {0} end state".format(fd))
					#remove the state
					self._socketstates.pop(sock, None)
					#remove any length
					self._socketmsglengths.pop(sock, None)
					self._socketdata.pop(sock, None)
					#if no more sockets left, break while loop by returning
					if len(self._socketstates) == 0:
						return

				#remove closed socket
				if event & (select.POLLHUP | select.POLLERR | select.POLLNVAL):
					self._logInfo("Remove closed socket due to 'Hung Up', 'Poll Error', or 'Poll Invalid': {0}".format(event))
					self._socketpoll.unregister(fd)
					del self._sockets[fd]
					self._socketstates.pop(sock, None)
					self._socketdata.pop(sock, None)
					self._socketmsglengths.pop(sock, None)
					#break while loop by returning
					return

				#clients send out data
				elif event & select.POLLOUT:
					# only send when there is something to send. POLLOUT registering will always
					# mark the socket as ready
					if sock in self._socketstates and \
						(self._socketstates[sock] == SocketState.READYSEND or
						self._socketstates[sock] == SocketState.SENDING ):
						try:
							"""
								Here sending happens
							"""
							self._sendall(sock)
						except Exception as e:
							msg = "Failed to send with _sendall: {0}".format(e)
							self._logError(msg)

				#if fired event is not caught, do nothing
				else:
					continue

	"""
		Receive data over a socket.
		maxTimeout: specifies max timeout for select.poll.poll() to listen
		recvNo: optional. Specifies fileno of socket to receive from. This constraints the events
		to a single socket, and will raise an exception if events from a different socket are caught
	"""
	def _recvSockets(self, maxTimeout, recvNo):
		#we wait for the maximum allowed time when polling.
		#this will do nothing if a socket is not generating an event,
		#but will return sooner if an event is available
		for fd, event in self._socketpoll.poll(maxTimeout * 1000): #expects timeout in milliseconds
			if fd in self._sockets:
				sock = self._sockets[fd]
			else:
				import ipdb
				ipdb.set_trace()
				raise ClosedSocketException(fd)

			#reset ended socket
			if (sock in self._socketstates) and (self._socketstates[sock] == SocketState.END):
				self._logDebug("auto remove socket {0} end state".format(fd))
				#remove the state
				self._socketstates.pop(sock, None)
				#remove any length
				self._socketmsglengths.pop(sock, None)
				self._socketdata.pop(sock, None)
				self._sockettimers.pop(sock, None)

			#remove closed socket
			if event & (select.POLLHUP | select.POLLERR | select.POLLNVAL):
				self._logInfo("Remove closed socket due to 'Hung Up', 'Poll Error', or 'Poll Invalid': {0}".format(event))
				self._socketpoll.unregister(fd)
				del self._sockets[fd]
				self._socketstates.pop(sock, None)
				self._socketdata.pop(sock, None)
				self._socketmsglengths.pop(sock, None)
				#in this case, we want to propagate the closing of the socket
				raise ClosedSocketException("Removed closed socket {0}".format(fd))

			#accept new connections
			elif sock is self._listen_sock:
				newsock, sockname = sock.accept()
				newsock.shutdown(socket.SHUT_WR) #shutdown for writing since we only read
				newsock.setblocking(False)
				fd = newsock.fileno()
				self._sockets[fd] = newsock
				self._socketpoll.register(fd, select.POLLIN)
				self._socketdata[newsock] = ''
				self._logInfo("Established new connection {0} on listening socket".format(fd))
				#if an old socket was present, remove it for now.
				#TODO: find out why old socket was not closed
				if len(self._sockets) > 2:
					oldfd = None
					oldsock = None
					for fileno in self._sockets:
						if fileno != self._listen_sock.fileno() and fileno != fd:
							oldfd = fileno
							oldsock = self._sockets[fileno]
							break
					self._logDebug("Removing old socket {0}".format(oldfd))
					self._socketpoll.unregister(oldfd)
					del self._sockets[oldfd]
					self._socketstates.pop(oldsock, None)
					self._socketdata.pop(oldsock, None)
					self._socketmsglengths.pop(oldsock, None)
					raise NotSameSocketException
				continue

			#collect incoming data
			elif event & select.POLLIN:
				if not sock in self._socketstates:
					#receive data until the length of the package has been parsed
					#will probably require only one go to read, but we can't be too sure,
					#thats why the receiveUntil function is still called
					self._receiveUntil(sock, SocketState.PACKAGE)
				elif (self._socketstates[sock] == SocketState.PACKAGE) or\
					 (self._socketstates[sock] == SocketState.RECEIVING):
					#receive data until the end of indicated length has been reached
					data = self._receiveUntil(sock, SocketState.END)
					if data:
						try:
							#uncompressed = zlib.decompress(data)
							unpickled = self._unpickle(data)
						except:
							continue #don't perform callback and don't set data
						#extra callback option
						if self._afterdataCallback != None:
							self._logInfo("Invoking afterdataCallback")
							self._afterdataCallback(unpickled)
						#unpickled data sits there until socket is ended
						self._socketdata[sock] = unpickled
				else:
					self._logError("No known socketstate when handling incoming data: {0}".format(self._socketstates[sock]))
					raise e

			else: #do nothing, next socket please
				continue



	"""
		Store a data object for the socket to send
	"""
	def prepareSend(self, sock, data):
		self._logInfo("Prepare Send")
		#sock may be none if we have only one socket
		if sock == None:
			#if instead we have no sockets, a disconnect might have happened
			if len(self._sockets) == 0:
				raise NoNetworkException("No connected sockets")
			#if one socket present
			if len(self._sockets) == 1:
				#just pick the first and only socket
				sock = self._sockets[self._sockets.keys()[0]]
			#if more than one socket present, specifying None won't do :)
			else:
				raise NetworkConfigError("Got 'prepareSend' with 'None' as socket but have more than one socket: {0}".format(len(self._sockets)))
		#we could get a socket which is not in our socket list. Possible malicious attempt
		else:
			if not sock.fileno() in self._sockets:
				raise NetworkConfigError("Socket provided to 'prepareSend' not in socket list: {0}".format(sock.fileno()))

		#if we obtained a socket, check the state to see whether it has ended
		if sock in self._socketstates and self._socketstates[sock] == SocketState.END:
			self._logInfo("Emptying socket state data")
			self._socketmsglengths.pop(sock, None)
			self._socketdata.pop(sock, None)
			self._sockettimers.pop(sock, None)

		pickled = self._pickle(data)
		#optional compressing
		if self._useCompression:
			pickled = lz4.dumps(pickled)

		#self._logDebug("Compression {0:.0f}%".format( float(len(pickled))/float(len(compressed))*100 ))
		"""
				We prepare a byte package that contains the data and metadata combined.
				The first 4 bytes of the package indicate its total length.
		"""
		package = self._socketfrmt.pack(len(pickled)) + pickled #byte length augmented package
		# at this point, check to see if the socket is still sending, and if so, if the package would
		# fit at the end of the buffer
		if sock in self._socketstates and self._socketstates[sock] == SocketState.SENDING:
			#will the package fit inside the buffer?
			if len(self._socketdata[sock]) + len(package) > self._socketdataMaxSize:
				#if not, throw an exception
				raise SocketBufferFullException("Trying to append to full socket buffer:\n{0}".format(sock.fileno(), len(self._socketdata[sock])))

			self._logInfo("Socket {0} still sending. Will append chunk {1} to buffer".format(sock.fileno(), data.number))
			self._socketdata[sock] += package
		else:
			self._socketdata[sock] = package
			self._socketstates[sock] = SocketState.READYSEND
			self._sockettimers[sock] = time.time()
			self._logInfo("Socket {0} ready to send package, {1:.2f}KB".format(sock.fileno(), len(package)/1024.))


	"""
		Send data and metadata over a socket.
		Returns a SocketState message, either SocketState.SENDING or SocketState.END
	"""
	def _sendall(self, sock):
		if not sock in self._socketdata:
			raise Exception("No data for socket to send. This should not happen")
		try:
			package = self._socketdata[sock]
			#create a timed loop, try and send as much data as possible within timeout
			n = sock.send(package)
			if n < len(package):
				self._socketdata[sock] = package[n:] #residual
				self._socketstates[sock] = SocketState.SENDING
				self._logDebug("Buffer size {0}".format(len(self._socketdata[sock])))
			else:
				self._socketstates[sock] = SocketState.END #indicate we're done
				self._logDebug("Sending ended")

		except Exception as e:
			self._logError("Exception occured in sending: {0}".format(e))
			raise e

		return self._socketstates[sock]

	"""
		Workhorse in receiving data from a socket.
		Specifies length of data to receive. If length was not acquired, store data.
		It is guaranteed that this function only returns data if 'length' bytes have been
		read from the socket.
	"""
	def _recvall(self, sock, length):
		data = sock.recv(length)
		fd = sock.fileno()
		self._logDebug("Received {0}/{1}".format(len(data), length))
		if len(data) == length: #we have everything, return the data
			#did we store previous data? then prepend it
			if sock in self._socketdata:
				data = self._socketdata[sock] + data
			return data
		else:
			if not sock in self._socketdata:
				self._logError("No data entry for socket {0}. This should not happen".format(fd))
				self._socketdata[sock] = ''

			self._socketdata[sock] += data
			#log how many bytes still needed
			self._socketmsglengths[sock] -= len(data)
			return


	def _receiveUntil(self, sock, endstate):
		fd = sock.fileno()
		if endstate == SocketState.PACKAGE: #retrieve until package length has been parsed
			try:
				data = self._recvall(sock, self._socketfrmt.size)
				if data:
					#set the endstate
					self._socketstates[sock] = endstate
					(length,) = self._socketfrmt.unpack(data)
					self._socketmsglengths[sock] = length
					self._socketdata[sock] = ''
					self._sockettimers[sock] = time.time()
					self._logDebug("Need to receive {0:.2f} KB from socket {1}".format(length/1024., fd))
					return
				else:
					return
			except Exception as e:
				self._logError("Problem when retrieving package size from socket {0}: {1}".format(fd, e))
				raise e

		elif endstate == SocketState.END: #retrieve until there is nothing more
			try:
				data = self._recvall(sock, self._socketmsglengths[sock])
				if data:
					#set the endstate
					self._socketstates[sock] = endstate
					elapsed = time.time() - self._sockettimers[sock]
					self._logDebug("Package took {0:.2f}s, {1:.2f}KB/s".format(elapsed, (len(data)/elapsed)/1024.))
					#optional decompressing
					if self._useCompression:
						data = lz4.loads(data)

					return data
				else:
					self._socketstates[sock] = SocketState.RECEIVING
					return
			except Exception as e:
				self._logError("Problem when retrieving package data from socket {0}: {1}".format(fd, e))
				raise e
		else:
			self._logError("Not a valid socket end state: {0}".format(endstate))
			return


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

	def _pickle(self, data):
		try:
			return cPickle.dumps(data)
		except Exception as e:
			self._logError("Unable to pickle data object: {0}".format(data))
			raise e

	def _unpickle(self, s):
		try:
			return cPickle.loads(s)
		except Exception as e:
			self._logError("Unable to unpickle serialized object: {0}".format(e))
			raise e
