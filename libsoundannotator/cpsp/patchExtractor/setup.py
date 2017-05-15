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
from distutils.core import setup, Extension
import sys
import numpy
import os
import shutil

'''
To builds the python extension the PatchExtractor module run setup.py:
python setup.py build_ext --inplace

For installation:
python setup.py build install --prefix=<local package dir>

or with debugging info
python setup.py build --debug install --prefix=<local package dir>

extra_link_args for windows are based on: http://bugs.python.org/issue4431
'''

swig_command='swig -c++ -python -I{0} -o patchExtractor_wrap.cpp patchExtractor.i'.format(os.path.join('..','framescaleArray'))
os.system(swig_command)
shutil.copy('patchExtractor.py','..')

if sys.platform.startswith('win'):
    extra_link_args=['/MANIFEST']
else:
    extra_link_args=[]
    
include_dirs =[numpy.get_include(),os.path.join('..','framescaleArray')]  
    
module1=Extension('_patchExtractor', 
					sources=['patchExtractor_wrap.cpp',
					'patchExtractor.cpp',os.path.join('..','framescaleArray','framescaleArray.cpp'),],
					extra_link_args=extra_link_args,
					include_dirs =include_dirs,
					)

setup(name='patchExtractor', 
		version='1.0', 
		description='This is a demo', 
		ext_modules=[module1],
		py_modules=['patchExtractor'],
		)

