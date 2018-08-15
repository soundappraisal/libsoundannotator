/*
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
*/
%module patchExtractor

%feature("autodoc", "1");

%{
#define SWIG_FILE_WITH_INIT

#include "patchExtractor.h"
%}
%include numpy.i
%include exception.i


%init %{
import_array()
%}

%apply (int DIM1, int DIM2, int *IN_ARRAY2) {(int ns, int nf, int *ts)};
%apply (int DIM1, int DIM2, int *INPLACE_ARRAY2) {(int ns2, int nf2, int *patches)};
%apply (int DIM1, int DIM2, int *INPLACE_ARRAY2) {(int noofDescriptors, int noofPatches, int *descriptors)};
%apply (int DIM1, int *INPLACE_ARRAY1) {(int rowsInPatch, int * inRowCountVector)};
%apply (int DIM1, int *INPLACE_ARRAY1) {(int colsInPatch, int * inColCountVector)};

%apply (int DIM1, int *INPLACE_ARRAY1 ) {(int colsInPatch,   int * inColLowerRow), (int colsInPatch2, int * inColUpperRow)};
%apply (int DIM1, int *INPLACE_ARRAY1 ) {(int rowsInPatch, int * inRowLowerCol), (int rowsInPatch2, int * inRowUpperCol)};

%apply (int DIM1, int DIM2, int *INPLACE_ARRAY2) {(int noRows, int noCols, int *masks)}
%apply (int DIM1, int DIM2, double *INPLACE_ARRAY2) {(int noRows, int noCols,  double * TF_Observable)}
%apply (int DIM1, double *INPLACE_ARRAY1) {( int colsInPatch, double * ColDistVector)}
%apply (int DIM1, double *INPLACE_ARRAY1) {( int rowsInPatch, double * RowDistVector)}   
 
%apply (int DIM1, int *INPLACE_ARRAY1) {(int noofRows, int * texturesBefore )}
%apply (int DIM1, int *INPLACE_ARRAY1) {(int noofRows2, int * texturesAfter  )}
%apply (int DIM1, int *INPLACE_ARRAY1) {( int noofRows3, int * patchNumbersBefore  )}
%apply (int DIM1, int *INPLACE_ARRAY1) {( int noofRows4, int * patchNumbersAfter )}
%apply (int DIM1, int DIM2, int *INPLACE_ARRAY2) {( int noofRows5, int sizeistwo, int * joinMatrix  )}
 
 
%exception {
    
    $action    
    if (PyErr_Occurred()) SWIG_fail;

}


class patchExtractor{ 
public:
    %extend {
        int cpp_calcPatches(int ns, int nf, int *ts, int ns2, int nf2, int *patches){
            
            if(ns==ns2 && nf==nf2){
                return $self->setTimeScaleData(ns, nf, ts,  patches);
            }else{
                PyErr_Format(PyExc_ValueError,
                "pyPatchExtractor: required size of inplace patches matrix is: \
                noofscales (%d) by noofframes (%d)",ns,nf);
            }
            
            return -1;
        }
    }
    
    %extend {
        int cpp_getDescriptors(int noofDescriptors, int noofPatches, int *descriptors){
            int _noofPatches=$self->getNoOfPatches();
            if(noofPatches==_noofPatches && noofDescriptors==6){
                return $self->getSimplePatchDescriptors( noofDescriptors, noofPatches, descriptors);
            }else{
                PyErr_Format(PyExc_ValueError,
                "pyPatchExtractor: required size of inplace descriptors matrix is: \
                noofPatches (%d) by noofDescriptors (%d)",_noofPatches,6);
            }
            
            return -1;
        }
    }
        
    %extend {
        void cpp_getInRowCount( int patchNo, int rowsInPatch, int * inRowCountVector){
            int _noofPatches=$self->getNoOfPatches();
            if(patchNo >=0 && patchNo< _noofPatches  && rowsInPatch == $self->getRowsInPatch(patchNo)){
                $self->getInRowCount( patchNo, inRowCountVector);
            }else{
                PyErr_Format(PyExc_ValueError,
                "pyPatchExtractor: required size of InRowCount vector for patchNo  \
               (%d) out of (%d) patches is: (%d)",patchNo , _noofPatches, $self->getRowsInPatch(patchNo));
            }
            
            return;
        }
    }
    
            
    %extend {
        void cpp_getInColCount( int patchNo, int colsInPatch, int * inColCountVector){
            int _noofPatches=$self->getNoOfPatches();
            if(patchNo >=0 && patchNo< _noofPatches  && colsInPatch == $self->getColsInPatch(patchNo)){
                $self->getInColCount( patchNo, inColCountVector);
            }else{
                PyErr_Format(PyExc_ValueError,
                "pyPatchExtractor: required size of InColCount vector for patchNo  \
               (%d) out of (%d) patches is: (%d)",patchNo , _noofPatches, $self->getColsInPatch(patchNo));
            }
            
            return;
        }
    }
    
  
    
    %extend {
        void cpp_getInColExtrema( int patchNo, int colsInPatch, int * inColLowerRow, int colsInPatch2, int * inColUpperRow){
            int _noofPatches=$self->getNoOfPatches();
            if(patchNo >=0 && patchNo< _noofPatches  && colsInPatch == $self->getColsInPatch(patchNo)&& colsInPatch2==$self->getColsInPatch(patchNo)){
                $self->getInColExtrema( patchNo, inColLowerRow,inColUpperRow);
            }else{
                PyErr_Format(PyExc_ValueError,
                "pyPatchExtractor: required size of inColLowerRow and inColUpperRow vector for patchNo  \
               (%d) out of (%d) patches is: (%d)",patchNo , _noofPatches, $self->getColsInPatch(patchNo));
            }
            
            return;
        }
    }
    
    %extend {
        void cpp_getInRowExtrema( int patchNo, int rowsInPatch, int * inRowLowerCol, int rowsInPatch2, int * inRowUpperCol){
            int _noofPatches=$self->getNoOfPatches();
            if(patchNo >=0 && patchNo< _noofPatches  && rowsInPatch == $self->getRowsInPatch(patchNo) && rowsInPatch2 == $self->getRowsInPatch(patchNo)){
                $self->getInRowExtrema( patchNo, inRowLowerCol, inRowUpperCol);
            }else{
                PyErr_Format(PyExc_ValueError,
                "pyPatchExtractor: required size of inRowLowerCol and inRowUpperCol vector for patchNo  \
               (%d) out of (%d) patches is: (%d)",patchNo , _noofPatches, $self->getRowsInPatch(patchNo));
            }
            
            return;
        }
    }
    
    
    %extend {
        void cpp_getMasks(int patchNo, int noRows, int noCols, int *masks){
            int noofPatches=$self->getNoOfPatches();
            
            if(noRows==$self->getNoOfRows() && noCols==$self->getNoOfCols() && patchNo >= 0 && patchNo < noofPatches){
                 $self->getMasks(patchNo, noRows, noCols, masks);
            }else{
                PyErr_Format(PyExc_ValueError,
                "pyPatchExtractor: required size of inplace mask matrix is: \
                noofscales (%d) by noofframes (%d), and the patchNo (%d) should not exceed number of patches",noRows,$self->getNoOfCols(), patchNo);
            }
        }
    }
    
    
     %extend {
        void cpp_calcInPatchMeans(int noRows, int noCols,  double * TF_Observable){
                if(noRows==$self->getNoOfRows() && noCols==$self->getNoOfCols() && self->simpleDescriptorsAllocated){
                     $self->calcInPatchMeans(noRows, noCols, TF_Observable);
                }else{
                
                    if(!self->simpleDescriptorsAllocated){
                        PyErr_Format(PyExc_RuntimeError,
                        "pyPatchExtractor: simple patch descriptors need to be calculated first");
                    }
                    
                    if(noRows!=$self->getNoOfRows() || noCols!=$self->getNoOfCols()){
                        PyErr_Format(PyExc_ValueError,
                        "pyPatchExtractor: required size of inplace mask matrix is: \
                        noofscales (%d) by noofframes (%d)",$self->getNoOfRows(),$self->getNoOfCols());
                    }
                    
                }
            }
        }
     
    %extend {
        void cpp_getInColDist(int patchNo, int colsInPatch, double * ColDistVector){
            int _noofPatches=$self->getNoOfPatches();
            if(patchNo >=0 && patchNo < _noofPatches  && colsInPatch == $self->getColsInPatch(patchNo)){
                self->getInColDist(patchNo, ColDistVector);
            }else{
                PyErr_Format(PyExc_ValueError,
                "pyPatchExtractor: required size of InColCount vector for patchNo  \
               (%d) out of (%d) patches is: (%d)",patchNo , _noofPatches, $self->getColsInPatch(patchNo));
            }
            return;
        }
    }
 
       
    %extend {
        void cpp_getInRowDist( int patchNo, int rowsInPatch, double * RowDistVector){
            int _noofPatches=$self->getNoOfPatches();
            if(patchNo >=0 && patchNo< _noofPatches  && rowsInPatch == $self->getRowsInPatch(patchNo)){
                $self->getInRowDist( patchNo, RowDistVector);
            }else{
                PyErr_Format(PyExc_ValueError,
                "pyPatchExtractor: required size of InRowCount vector for patchNo  \
               (%d) out of (%d) patches is: (%d)",patchNo , _noofPatches, $self->getRowsInPatch(patchNo));
            }
            return;
        }
    }
    
    %extend {
        int cpp_calcJoinMatrix(int noofRows, int * texturesBefore, int noofRows2, int * texturesAfter, int noofRows3, int * patchNumbersBefore , int noofRows4, int * patchNumbersAfter,  int noofRows5, int sizeistwo, int * joinMatrix ){
            int validPatchCount=0;
            if(noofRows==noofRows2 &&noofRows==noofRows3 &&noofRows==noofRows4 && 2*noofRows==noofRows5 && sizeistwo==2){
                 validPatchCount=self->calcJoinMatrix(noofRows, texturesBefore, texturesAfter, patchNumbersBefore , patchNumbersAfter, joinMatrix );
            }else{
                PyErr_Format(PyExc_ValueError, "inconsistent sizes");
            }  
            
            return validPatchCount;                                                                                         
        }
    }
   
    int getColsInPatch(int patchNo);
    int getRowsInPatch(int patchNo);
    int getNoOfPatches(){return noPatches;};
    int getNoOfCols(){return noofCols;};
    int getNoOfRows(){return noofRows;};
};
