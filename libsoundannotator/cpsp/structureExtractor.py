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
# This file was automatically generated by SWIG (http://www.swig.org).
# Version 2.0.11
#
# Do not make changes to this file unless you know what you are doing--modify
# the SWIG interface file instead.





from sys import version_info
if version_info >= (2,6,0):
    def swig_import_helper():
        from os.path import dirname
        import imp
        fp = None
        try:
            fp, pathname, description = imp.find_module('_structureExtractor', [dirname(__file__)])
        except ImportError:
            import _structureExtractor
            return _structureExtractor
        if fp is not None:
            try:
                _mod = imp.load_module('_structureExtractor', fp, pathname, description)
            finally:
                fp.close()
            return _mod
    _structureExtractor = swig_import_helper()
    del swig_import_helper
else:
    import _structureExtractor
del version_info
try:
    _swig_property = property
except NameError:
    pass # Python < 2.2 doesn't have 'property'.
def _swig_setattr_nondynamic(self,class_type,name,value,static=1):
    if (name == "thisown"): return self.this.own(value)
    if (name == "this"):
        if type(value).__name__ == 'SwigPyObject':
            self.__dict__[name] = value
            return
    method = class_type.__swig_setmethods__.get(name,None)
    if method: return method(self,value)
    if (not static):
        self.__dict__[name] = value
    else:
        raise AttributeError("You cannot add attributes to %s" % self)

def _swig_setattr(self,class_type,name,value):
    return _swig_setattr_nondynamic(self,class_type,name,value,0)

def _swig_getattr(self,class_type,name):
    if (name == "thisown"): return self.this.own()
    method = class_type.__swig_getmethods__.get(name,None)
    if method: return method(self)
    raise AttributeError(name)

def _swig_repr(self):
    try: strthis = "proxy of " + self.this.__repr__()
    except: strthis = ""
    return "<%s.%s; %s >" % (self.__class__.__module__, self.__class__.__name__, strthis,)

try:
    _object = object
    _newclass = 1
except AttributeError:
    class _object : pass
    _newclass = 0


class structureExtractor(_object):
    __swig_setmethods__ = {}
    __setattr__ = lambda self, name, value: _swig_setattr(self, structureExtractor, name, value)
    __swig_getmethods__ = {}
    __getattr__ = lambda self, name: _swig_getattr(self, structureExtractor, name)
    __repr__ = _swig_repr
    def __init__(self, *args): 
        this = _structureExtractor.new_structureExtractor(*args)
        try: self.this.append(this)
        except: self.this = this
    def initialize(self, *args): return _structureExtractor.structureExtractor_initialize(self, *args)
    def get_correlations(self, *args): return _structureExtractor.structureExtractor_get_correlations(self, *args)
    def calc_pattern(self, *args): return _structureExtractor.structureExtractor_calc_pattern(self, *args)
    def get_pattern_margins(self, *args): return _structureExtractor.structureExtractor_get_pattern_margins(self, *args)
    def calc_tract(self, *args): return _structureExtractor.structureExtractor_calc_tract(self, *args)
    def get_tract_margins(self, *args): return _structureExtractor.structureExtractor_get_tract_margins(self, *args)
    def get_pattern_stats(self, *args): return _structureExtractor.structureExtractor_get_pattern_stats(self, *args)
    def set_pattern_stats(self, *args): return _structureExtractor.structureExtractor_set_pattern_stats(self, *args)
    def get_tract_stats(self, *args): return _structureExtractor.structureExtractor_get_tract_stats(self, *args)
    def set_tract_stats(self, *args): return _structureExtractor.structureExtractor_set_tract_stats(self, *args)
    __swig_destroy__ = _structureExtractor.delete_structureExtractor
    __del__ = lambda self : None;
structureExtractor_swigregister = _structureExtractor.structureExtractor_swigregister
structureExtractor_swigregister(structureExtractor)

# This file is compatible with both classic and new-style classes.


