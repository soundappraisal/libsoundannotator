# This file was automatically generated by SWIG (http://www.swig.org).
# Version 3.0.8
#
# Do not make changes to this file unless you know what you are doing--modify
# the SWIG interface file instead.





from sys import version_info
if version_info >= (2, 6, 0):
    def swig_import_helper():
        from os.path import dirname
        import imp
        fp = None
        try:
            fp, pathname, description = imp.find_module('_patchExtractor', [dirname(__file__)])
        except ImportError:
            import _patchExtractor
            return _patchExtractor
        if fp is not None:
            try:
                _mod = imp.load_module('_patchExtractor', fp, pathname, description)
            finally:
                fp.close()
            return _mod
    _patchExtractor = swig_import_helper()
    del swig_import_helper
else:
    import _patchExtractor
del version_info
try:
    _swig_property = property
except NameError:
    pass  # Python < 2.2 doesn't have 'property'.


def _swig_setattr_nondynamic(self, class_type, name, value, static=1):
    if (name == "thisown"):
        return self.this.own(value)
    if (name == "this"):
        if type(value).__name__ == 'SwigPyObject':
            self.__dict__[name] = value
            return
    method = class_type.__swig_setmethods__.get(name, None)
    if method:
        return method(self, value)
    if (not static):
        if _newclass:
            object.__setattr__(self, name, value)
        else:
            self.__dict__[name] = value
    else:
        raise AttributeError("You cannot add attributes to %s" % self)


def _swig_setattr(self, class_type, name, value):
    return _swig_setattr_nondynamic(self, class_type, name, value, 0)


def _swig_getattr_nondynamic(self, class_type, name, static=1):
    if (name == "thisown"):
        return self.this.own()
    method = class_type.__swig_getmethods__.get(name, None)
    if method:
        return method(self)
    if (not static):
        return object.__getattr__(self, name)
    else:
        raise AttributeError(name)

def _swig_getattr(self, class_type, name):
    return _swig_getattr_nondynamic(self, class_type, name, 0)


def _swig_repr(self):
    try:
        strthis = "proxy of " + self.this.__repr__()
    except Exception:
        strthis = ""
    return "<%s.%s; %s >" % (self.__class__.__module__, self.__class__.__name__, strthis,)

try:
    _object = object
    _newclass = 1
except AttributeError:
    class _object:
        pass
    _newclass = 0


class patchExtractor(_object):
    """Proxy of C++ patchExtractor class."""

    __swig_setmethods__ = {}
    __setattr__ = lambda self, name, value: _swig_setattr(self, patchExtractor, name, value)
    __swig_getmethods__ = {}
    __getattr__ = lambda self, name: _swig_getattr(self, patchExtractor, name)
    __repr__ = _swig_repr

    def cpp_calcPatches(self, ns, ns2):
        """cpp_calcPatches(patchExtractor self, int ns, int ns2) -> int"""
        return _patchExtractor.patchExtractor_cpp_calcPatches(self, ns, ns2)


    def cpp_getDescriptors(self, noofDescriptors):
        """cpp_getDescriptors(patchExtractor self, int noofDescriptors) -> int"""
        return _patchExtractor.patchExtractor_cpp_getDescriptors(self, noofDescriptors)


    def cpp_getInRowCount(self, patchNo, rowsInPatch):
        """cpp_getInRowCount(patchExtractor self, int patchNo, int rowsInPatch)"""
        return _patchExtractor.patchExtractor_cpp_getInRowCount(self, patchNo, rowsInPatch)


    def cpp_getInColCount(self, patchNo, colsInPatch):
        """cpp_getInColCount(patchExtractor self, int patchNo, int colsInPatch)"""
        return _patchExtractor.patchExtractor_cpp_getInColCount(self, patchNo, colsInPatch)


    def cpp_getInColExtrema(self, patchNo, colsInPatch, colsInPatch2):
        """cpp_getInColExtrema(patchExtractor self, int patchNo, int colsInPatch, int colsInPatch2)"""
        return _patchExtractor.patchExtractor_cpp_getInColExtrema(self, patchNo, colsInPatch, colsInPatch2)


    def cpp_getInRowExtrema(self, patchNo, rowsInPatch, rowsInPatch2):
        """cpp_getInRowExtrema(patchExtractor self, int patchNo, int rowsInPatch, int rowsInPatch2)"""
        return _patchExtractor.patchExtractor_cpp_getInRowExtrema(self, patchNo, rowsInPatch, rowsInPatch2)


    def cpp_getMasks(self, patchNo, noRows):
        """cpp_getMasks(patchExtractor self, int patchNo, int noRows)"""
        return _patchExtractor.patchExtractor_cpp_getMasks(self, patchNo, noRows)


    def cpp_calcInPatchMeans(self, noRows):
        """cpp_calcInPatchMeans(patchExtractor self, int noRows)"""
        return _patchExtractor.patchExtractor_cpp_calcInPatchMeans(self, noRows)


    def cpp_getInColDist(self, patchNo, colsInPatch):
        """cpp_getInColDist(patchExtractor self, int patchNo, int colsInPatch)"""
        return _patchExtractor.patchExtractor_cpp_getInColDist(self, patchNo, colsInPatch)


    def cpp_getInRowDist(self, patchNo, rowsInPatch):
        """cpp_getInRowDist(patchExtractor self, int patchNo, int rowsInPatch)"""
        return _patchExtractor.patchExtractor_cpp_getInRowDist(self, patchNo, rowsInPatch)


    def cpp_calcJoinMatrix(self, noofRows, noofRows2, noofRows3, noofRows4, noofRows5):
        """cpp_calcJoinMatrix(patchExtractor self, int noofRows, int noofRows2, int noofRows3, int noofRows4, int noofRows5) -> int"""
        return _patchExtractor.patchExtractor_cpp_calcJoinMatrix(self, noofRows, noofRows2, noofRows3, noofRows4, noofRows5)


    def getColsInPatch(self, patchNo):
        """getColsInPatch(patchExtractor self, int patchNo) -> int"""
        return _patchExtractor.patchExtractor_getColsInPatch(self, patchNo)


    def getRowsInPatch(self, patchNo):
        """getRowsInPatch(patchExtractor self, int patchNo) -> int"""
        return _patchExtractor.patchExtractor_getRowsInPatch(self, patchNo)


    def getNoOfPatches(self):
        """getNoOfPatches(patchExtractor self) -> int"""
        return _patchExtractor.patchExtractor_getNoOfPatches(self)


    def getNoOfCols(self):
        """getNoOfCols(patchExtractor self) -> int"""
        return _patchExtractor.patchExtractor_getNoOfCols(self)


    def getNoOfRows(self):
        """getNoOfRows(patchExtractor self) -> int"""
        return _patchExtractor.patchExtractor_getNoOfRows(self)


    def __init__(self):
        """__init__(patchExtractor self) -> patchExtractor"""
        this = _patchExtractor.new_patchExtractor()
        try:
            self.this.append(this)
        except Exception:
            self.this = this
    __swig_destroy__ = _patchExtractor.delete_patchExtractor
    __del__ = lambda self: None
patchExtractor_swigregister = _patchExtractor.patchExtractor_swigregister
patchExtractor_swigregister(patchExtractor)

# This file is compatible with both classic and new-style classes.


