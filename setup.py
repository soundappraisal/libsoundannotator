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

The build is nearly fully automatic. For changes to the interface 
linking Python with the C++ modules (at time of writing: 
_structureExtractor,_patchExtractor) rerunning of SWIG will be 
necessary. For ease of distribution the SWIG generated Python and C++ 
code is included in the source tree. 

'''
from setuptools import setup, find_packages, Extension
from distutils.util import get_platform
import pkg_resources
import textwrap
import os, sys

# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

def is_installed(requirement):
    try:
        pkg_resources.require(requirement)
    except pkg_resources.ResolutionError:
        return False
    else:
        return True

if not is_installed('numpy>=1.11.0'):
    print(textwrap.dedent("""
            Error: numpy needs to be installed first. You can install it via:

            $ pip install numpy>=1.11.0
            """))
    sys.exit(1)

import numpy as np

# Generate meta-data for Git
from libsoundannotator.config.generateMetaData import generateMetaData
generateMetaData()

extra_link_args=[]
required_packages= read('requirements.txt').split('\n')


if sys.platform.startswith('win'):
    extra_link_args=['/MANIFEST']
    
extra_packages=[]
if not sys.platform.startswith('linux'):
    extra_packages+=['PyFFTW3>=0.2.1',]
elif not os.uname()[4].startswith('arm'):
    extra_packages+=['PyFFTW3>=0.2.1',]
    
required_packages+= extra_packages 
    
    
ext_modules = []
structureExtractor_path = os.path.join('libsoundannotator','cpsp', 'structureExtractor')
patchExtractor_path = os.path.join('libsoundannotator','cpsp', 'patchExtractor')
framescaleArray_path= os.path.join('libsoundannotator','cpsp', 'framescaleArray')
io_path = os.path.join('libsoundannotator','io')
include_dirs =[np.get_include(),structureExtractor_path,patchExtractor_path,framescaleArray_path, io_path]
ext_modules.append(
                    Extension('_structureExtractor',
                                sources=[os.path.join(structureExtractor_path, fname) for fname in
                                    ('structureExtractor_wrap.cpp',
                                    'structureExtractor.cpp',
                                    'fsArrayCorrelator.cpp',
                                    'thresholdCrossing.cpp',
                                    'pasCalculator.cpp',
                                    'textureCalculator.cpp',)]+
                                    [os.path.join(framescaleArray_path, fname2) for fname2 in
                                    ('framescaleArray.cpp',)],
                                extra_link_args=extra_link_args,
                                include_dirs =include_dirs,
                            )
                )

ext_modules.append(
                    Extension('_patchExtractor',
                                sources=[os.path.join(patchExtractor_path, fname) for fname in
                                    ('patchExtractor_wrap.cpp',
                                    'patchExtractor.cpp',)]+
                                    [os.path.join(framescaleArray_path, fname2) for fname2 in
                                    ('framescaleArray.cpp',)],
                                extra_link_args=extra_link_args,
                                include_dirs =include_dirs,
                            )
                )



if __name__ == "__main__":
    setup(
        name='libSoundAnnotator',
        version='1.1',
        url='http://www.soundappraisal.eu',
        description='Package for online sound classification ',
        long_description=read('README'),
        author='Ronald van Elburg, Coen Jonker, Arryon Tijsma',
        author_email='r.a.j.van.elburg@soundappraisal.eu',
        license='Apache License, Version 2.0',
        download_url='https://github.com/soundappraisal/libsoundannotator',    
        platforms=get_platform(),  
        classifiers=[
            'Development Status :: 3 - Alpha',
            'Environment :: Console',
            'Intended Audience :: Science/Research/Education',
            'Natural Language :: English',
            'Operating System :: Linux',
            'Programming Language :: Python/C++/SWIG',
            'Topic :: Scientific/Engineering :: Computational Auditory Scene Analysis'
        ],
        install_requires=required_packages,
        packages=find_packages(),
        ext_modules = ext_modules,
        ext_package = 'libsoundannotator.cpsp',
        test_suite='nose.collector',

        package_dir={
            'libsoundannotator.tests.structureExtractor_test': os.path.join('libsoundannotator','tests','structureExtractor_test')
        },
        package_data={
            'libsoundannotator.tests.structureExtractor_test': ['*.txt'],
        }
    )
