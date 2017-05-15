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
import json, os, sys, time

class StorageFormatter(object):

	def __init__(self, *args, **kwargs):
		pass

	def format(self, data):
		raise Exception("Implement this in subclass")

class XmlStorage(StorageFormatter):

	def __init__(self, *args, **kwargs):
		super(XmlStorage, self).__init__(*args, **kwargs)

		self.foldername = 'xml'

	def format(self, data):
		pass

class JsonStorage(StorageFormatter):

	def __init__(self, *args, **kwargs):
		super(JsonStorage, self).__init__(*args, **kwargs)

		self.foldername = 'json'

	def format(self, data):
		return json.dumps(data)

class HDF5Storage(StorageFormatter):

	def __init__(self, *args, **kwargs):
		super(HDF5Storage, self).__init__(*args, **kwargs)

		self.foldername = 'hdf5'

	def format(self, data):
		pass

class StorageFormatterFactory(object):
	
	@staticmethod	
	def getInstance(class_name, *args, **kwargs):
		try:
			instance = getattr(sys.modules[__name__], class_name)
			obj = instance(*args, **kwargs)
			return obj
		except:
			raise Exception("Could not instantiate class {0}".format(class_name))