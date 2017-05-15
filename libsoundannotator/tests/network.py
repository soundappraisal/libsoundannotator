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
from libsoundannotator.streamboard.network import NetworkMixin
from libsoundannotator.streamboard.subscription import NetworkConnection
import time, numpy as np, sys, cPickle

config = {
	'interface': sys.argv[2],
	'port': 1060
}

class DataObject(object):
	def __init__(self, n, data, metadata):
		self.n = n
		self.data = data
		self.metadata = metadata

class ServerTest(NetworkMixin):

	def __init__(self, config, *args, **kwargs):
		serverconf = config
		serverconf['type'] = 'server'
		self.connection = NetworkConnection(serverconf)

	def printData(self, data):
		print data.metadata

	def run(self):
		print "Running server"
		while True:
			new = self.connection.poll()
			if new:
				data = self.connection.recv()
				if data:
					print "Got package {0}".format(data.n)
			time.sleep(0.025)

class ClientTest(NetworkMixin):
	
	def __init__(self, config, *args, **kwargs):
		clientconf = config
		clientconf['type'] = 'client'
		self.connection = NetworkConnection(clientconf, pollTimeout=2.0)

	def run(self):
		print "Running client"
		n = 1
		data = np.random.randint(1, 150, size=22050)
		metadata = {
				'description': 'Test for client :)'
		}
		package = DataObject(n, data, metadata)
		while True:
				package.n += 1
				print "Send package {0}".format(package.n)
				try:
						self.connection.send(package)
				except:
						pass
				time.sleep(0.5)



if sys.argv[1] == 'server':
	config['type'] = 'server'
	st = ServerTest(config)
	st.run()
elif sys.argv[1] == 'client':
	config['type'] = 'client'
	st = ClientTest(config)
	st.run()
