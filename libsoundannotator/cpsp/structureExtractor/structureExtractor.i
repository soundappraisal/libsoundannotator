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
%module structureExtractor

%{
#define SWIG_FILE_WITH_INIT

#include "structureExtractor.h"
%}
%include numpy.i
%include exception.i


%init %{
import_array()
%}

%apply (int DIM1,int DIM2, double *IN_ARRAY2) {(int ns, int nf, double *ts)};
%apply (int DIM1,int DIM2, double *INPLACE_ARRAY2) {(int ns2, int nf2, double * pattern)};
%apply (int DIM1,int DIM2, double *INPLACE_ARRAY2) {(int ns3, int noofdelays, double * corr)};
%apply (int DIM1,int DIM2, double *INPLACE_ARRAY2) {(int ns4, int nf4, double * tract)};
%apply (int DIM1, double *INPLACE_ARRAY1) {(int ns5, double *Pm)};
%apply (int DIM1, double *INPLACE_ARRAY1) {(int ns6, double *Ps)};
%apply (int DIM1,int DIM2, int *INPLACE_ARRAY2) {(int ns7, int noofcoords, int * tcSamplePoints)};
%apply (int DIM1,int DIM2, int *INPLACE_ARRAY2) {(int ns8, int nois8, int * tcStatus)};
%apply (int DIM1,int DIM2, double *INPLACE_ARRAY2) {(int ns9, int nois2, double * tcInterpolationDeltas)};

%apply (int DIM1, double *INPLACE_ARRAY1) {(int ns10, double * Bm)};
%apply (int DIM1, double *INPLACE_ARRAY1) {(int ns11, double * Bs)};
%apply (int DIM1, int DIM2, int *INPLACE_ARRAY2) {(int ns12, int nsx3, int * contextAreas)};
%apply (int DIM1, int *INPLACE_ARRAY1) {(int ns13, int *_areaSizes)};
%apply (int DIM1, int *INPLACE_ARRAY1) {(int istwo1, int * frameoffsets)};
%apply (int DIM1, int *INPLACE_ARRAY1) {(int istwo2, int * scaleoffsets)};
%exception {
    
    $action    
    if (PyErr_Occurred()) SWIG_fail;

}



class structureExtractor{ 
public:

    
    structureExtractor(bool normalize);

    %extend {
        void initialize(int ns, int nf, double *ts, int md){
            $self->init(nf, ns, md, ts);
        }
    }

    %extend {
        void  get_correlations(int ns3, int noofdelays, double *corr, bool fullMatrix){
            int md,ns;
            $self->getDimensions(ns, md);
            if(ns3==ns*ns && 2*md+1==noofdelays){
                $self->getCorrelationMatrix(corr, fullMatrix);
            }else{
                PyErr_Format(PyExc_ValueError,
                "pyStructureExtractor: required size of inplace correlation matrix is: noofdelays %d, noofscales^2= (%d)^2",
                2*md+1, ns);
            }           
        }
    }

    %extend {
        void calc_pattern(int ns, int nf, double *ts, int ns2, int nf2, double * pattern, char textureType){
            int md_,ns_;
            $self->getDimensions(ns_, md_);
            if(ns==ns_ && ns2==ns_ && nf==nf2){
                $self->calcPas(textureType, nf, ns,  ts, pattern);
            }else{
                PyErr_Format(PyExc_ValueError,
                "pyStructureExtractor: required size of inplace pattern matrix is: noofscales= (%d) by nooframes in input", ns_);
            }   
        
        }
    }

    %extend {
        void get_pattern_margins(char textureType){
            PyErr_Format(PyExc_NotImplementedError,
                "pyStructureExtractor: get_pattern_margins future extension");
        }
    }
    
    
    
    %extend {
        void calc_tract(int ns, int nf, double *ts, int ns4, int nf4, double * tract, int ns2, int nf2, double * pattern, char textureType){
            int md_,ns_;
            $self->getDimensions(ns_, md_);
            if(ns==ns_ && ns2==ns_ && nf==nf2 && ns4==ns_ && nf==nf4){
                $self->calcTexture(textureType, nf, ns,  ts, tract, pattern);
            }else{
                PyErr_Format(PyExc_ValueError,
                "pyStructureExtractor: required size of inplace tract and pattern  matrices is: noofscales= (%d) by nooframes in input", ns_);
            }   
        
        }
    }
    
    %extend {
        void get_tract_margins(char textureType){
        PyErr_Format(PyExc_NotImplementedError ,
                "pyStructureExtractor: get_tract_margins future extension");
            
        }
    }
        
    %extend {
        void get_pattern_stats(int ns5, double *Pm, \
                                int ns6, double * Ps, \
                                int ns7, int noofcoords, int * tcSamplePoints, \
                                int ns8, int nois8, int * tcStatus, \
                                int ns9, int nois2, double * tcInterpolationDeltas, \
                                int istwo1, int * frameoffsets,\
                                int istwo2, int * scaleoffsets,\
                                char textureType){
            int md_,ns_;
            $self->getDimensions(ns_, md_);
            if(ns6==ns_ && ns5==ns_ && ns7==2*ns_ && ns8==2*ns_ && ns9==2*ns_  && noofcoords==8 && nois8==2 && nois2==2 && istwo1==2 && istwo2==2){
                $self->getPasStats(textureType, Pm, Ps, tcSamplePoints, tcStatus,  tcInterpolationDeltas, frameoffsets, scaleoffsets);

            }else{
                PyErr_Format(PyExc_ValueError,
                "pyStructureExtractor: required size of inplace matrices is: \n \
                Ps, Pm: noofscales= (%d) by 1 \n \
                tcSamplePoints: 2*noofscales= (%d) by 8 \n \
                tcStatus, tcInterpolationDeltas: 2*noofscales= (%d) by 2 ", ns_,2*ns_, 2*ns_);
            }   
        
        }
    }
        
    %extend {
        void set_pattern_stats( int ns_,\
                                int ns5, double *Pm, \
                                int ns6, double * Ps, \
                                int ns7, int noofcoords, int * tcSamplePoints, \
                                int ns8, int nois8, int * tcStatus, \
                                int ns9, int nois2, double * tcInterpolationDeltas, \
                                int istwo1, int * frameoffsets,\
                                int istwo2, int * scaleoffsets,\
                                char textureType){
            
            $self->setDimensions(textureType, ns_);
            if(ns6==ns_ && ns5==ns_ && ns7==2*ns_ && ns8==2*ns_ && ns9==2*ns_  && noofcoords==8 && nois8==2 && nois2==2 && istwo1==2 && istwo2==2){
                $self->setPasStats(textureType, Pm, Ps, tcSamplePoints, tcStatus,  tcInterpolationDeltas, frameoffsets, scaleoffsets);
            }else{
                PyErr_Format(PyExc_ValueError,
                "pyStructureExtractor: required size of inplace matrices with given dimensions is: \n \
                Ps, Pm: noofscales= (%d) by 1 \n \
                tcSamplePoints: 2*noofscales= (%d) by 8 \n \
                tcStatus, tcInterpolationDeltas: 2*noofscales= (%d) by 2 ", ns_,2*ns_, 2*ns_);
            }   
        
        }
    }
    
    %extend {
        void get_tract_stats(int ns10, double *Bm, \
                                int ns11, double * Bs, \
                                int ns13, int *_areaSizes,\
                                int ns12, int nsx3, int * contextAreas, \
                                int istwo1, int * frameoffsets,\
                                int istwo2, int * scaleoffsets,\
                                char textureType){
            int md_,ns_;
            $self->getDimensions(ns_, md_);
            if(ns10==ns_ && ns11==ns_ && ns12==ns_  && nsx3==3*ns_  && istwo1==2 && istwo2==2){
                $self->getTextureStats(  textureType,  Bm,   Bs, _areaSizes,  contextAreas, frameoffsets, scaleoffsets);
            }else{
                PyErr_Format(PyExc_ValueError,
                "pyStructureExtractor: required size of inplace matrices is: \n \
                    Bm, Bs: noofscales= (%d) by 1 \n \
                    contextAreas: noofscales= (%d)  by 3* noofscalesby= (%d) ", ns_, ns_, 3*ns_);
            }   
        
        }
    }
    
     %extend {
        void set_tract_stats(int ns,\
                                int ns10, double *Bm, \
                                int ns11, double * Bs, \
                                int ns13, int *_areaSizes,\
                                int ns12, int nsx3, int * contextAreas, \
                                int istwo1, int * frameoffsets,\
                                int istwo2, int * scaleoffsets,\
                                char textureType){
                                
            if(ns10==ns && ns11==ns && ns12==ns  && nsx3==3*ns && istwo1==2 && istwo2==2){
                $self->setTextureStats(  textureType, ns,  Bm,   Bs,_areaSizes,  contextAreas, frameoffsets, scaleoffsets);
            }else{
                PyErr_Format(PyExc_ValueError,
                "pyStructureExtractor: required size of inplace matrices is: \n \
                    Bm, Bs: noofscales= (%d) by 1 \n \
                    contextAreas: noofscales= (%d)  by 3* noofscalesby= (%d) ", ns, ns, 3*ns);
            }   
        
        }
    } 
};


