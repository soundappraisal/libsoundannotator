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
#ifndef STRUCTUREEXTRACTOR_H
#define STRUCTUREEXTRACTOR_H
//class calcTexturesWrapper;

#include "thresholdCrossing.h"
#include "framescaleArray.h" 
#include "fsArrayCorrelator.h"
#include "pasCalculator.h"
#include "textureCalculator.h"
#include <map>

class structureExtractor {
	
	public:
        structureExtractor(bool normalize); //initNoise should be replaced with constructor for the boxes
        void init(int nf,int  ns, int md , double *ts);
		~structureExtractor();
        void setThreshold(double threshold);
        void getCorrelationMatrix(double *CM, bool fullMatrix);
        void calculatorInitialization();
        
        void getDimensions(int & ns, int & md);
        void getDimensions(char textureType, int & ns);
        
        void getPas(char textureType, int nf,int ns, double *P);
        void calcPas(char textureType, int nf,int ns,  double * fsArrayRaw, double *P);
        void getPasStats(char textureType, double *Pm, double * Ps, int * tcSamplePoints, int * tcStatus, double * tcInterpolationDeltas, int * frameoffsets, int * scaleoffsets );
        
 
        void getTexture(char textureType, int nf, int ns, double *B);
        void calcTexture(char textureType, int nr, int nc, double * fsArrayRaw, double *B, double *P);
        void getTextureStats(char textureType, double *Bm, double * Bs, int *areasizes, int *contextAreas,int * frameoffsets, int * scaleoffsets);
        void setTextureStats(char textureType, int ns, double *Bm, double * Bs, int *areasizes, int *contextAreas,int * frameoffsets, int * scaleoffsets);
               
        void setDimensions(char textureType, int ns);
        void setPasStats(char textureType, double *Pm, double * Ps, int * tcSamplePoints, int * tcStatus, double * tcInterpolationDeltas, int * frameoffsets, int * scaleoffsets );
               
        void calcCorrelationMatrix();
       
        
    private:
        framescaleArray * initNoise;
        fsArrayCorrelator * fsArrayCorr;
        bool initialized;
        
        double *correlationMatrix;
        bool correlationMatrixAllocated;
        int noofscales;
        int maxdelay;
        int noofdelays;
       
        pasCalculatorMap pasCalculators;
        pasCalculatorMap::iterator pasCalcIt;
        textureCalculatorMap textureCalculators;
        textureCalculatorMap::iterator textCalcIt;
};





#endif
