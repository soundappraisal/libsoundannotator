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
#include "structureExtractor.h"

#include <cassert>
#include <limits>
#include <cstring>
#include <cmath>
#include "thresholdCrossing.h"
#include "framescaleArray.h" 
#include "fsArrayCorrelator.h"
#include "pasCalculator.h"
#include "textureCalculator.h"
 

structureExtractor::structureExtractor(bool normalize){ 
    correlationMatrixAllocated=false;
    initialized=false;
    pasCalculators['f']=new  pasCalculator(normalize); //    Pulse (structure in the frame direction)
    pasCalculators['s']=new  pasCalculator(normalize); //    Tone (structure in the scale direction)
    pasCalculators['u']=new  pasCalculator(normalize);  // Rising chirp (structure in the falling direction)
    pasCalculators['d']=new  pasCalculator(normalize);  // Falling chirp (structure in the rising direction)
};


structureExtractor::~structureExtractor(){
    if(correlationMatrixAllocated){ delete[] correlationMatrix;};
    if(initialized){
        delete initNoise;  
        delete fsArrayCorr;
    };
    
    pasCalculator::pasCalculatorMapCleanup(pasCalculators);
    textureCalculator::textureCalculatorMapCleanup(textureCalculators); 
};


void structureExtractor::init(int nf,int  ns, int md , double *ts){ 
    initNoise = new framescaleArray(nf,ns,ts);
    noofscales=ns;
    maxdelay=md;
    noofdelays=2*maxdelay+1;
    fsArrayCorr = new fsArrayCorrelator(nf,md,ns,ts);
    calculatorInitialization();
    initialized=true;
};
 
void structureExtractor::setThreshold(double threshold){thresholdCrossing::threshold=threshold;}; 
 
// Interface functions
void  structureExtractor::getCorrelationMatrix(double *CM, bool fullMatrix){
    if(fullMatrix){
        calcCorrelationMatrix();   
    }
    std::memcpy(CM,correlationMatrix,sizeof(double)*noofscales*noofscales*noofdelays);
};
  
void structureExtractor::getDimensions(int & ns, int & md){
    ns= noofscales;
    md= maxdelay;
};
    
void  structureExtractor::getPas(char textureType, int nf,int ns, double *P){
    pasCalculators[textureType]->getPas(P);
};

void  structureExtractor::calcPas(char textureType, int nf,int ns, double *fsArrayRaw, double *P){
    framescaleArray * mySound=new framescaleArray(nf,ns ,fsArrayRaw);
    pasCalculators[textureType]->calcPas(mySound );
    pasCalculators[textureType]->getPas(P);
    delete mySound;
};

void  structureExtractor::getPasStats(char textureType, double *Pm, double * Ps, int * tcSamplePoints, int * tcStatus, double * tcInterpolationDeltas, int * frameoffsets, int * scaleoffsets ){
  pasCalculators[textureType]->getPasStats( Pm,Ps, tcSamplePoints,  tcStatus,  tcInterpolationDeltas,frameoffsets, scaleoffsets );
};

void  structureExtractor::getTexture(char textureType, int nf,int ns, double *B){
    textureCalculators[textureType]->getTexture(B);
};

void  structureExtractor::calcTexture(char textureType, int nf,int ns,  double * fsArrayRaw, double *B, double *P){
    framescaleArray * mySound=new framescaleArray(nf,ns,fsArrayRaw);
    pasCalculator * pas=pasCalculators[textureType];
    textureCalculator * tex=textureCalculators[textureType];
    
    pas->calcPas(mySound);
    pas->getPas(P);
    
    tex->calcTexture(pas->PArray);
    tex->getTexture(B);
    
    delete mySound;
};



void  structureExtractor::getTextureStats(char textureType, double *Bm, double * Bs,int *areasizes, int *contextAreas,int * frameoffsets, int * scaleoffsets){
  textureCalculators[textureType]->getTextureStats( Bm,Bs,areasizes, contextAreas, frameoffsets, scaleoffsets);
};

void structureExtractor::calcCorrelationMatrix(){
    int scale, xscale, framedelay;
    double xcorr;
    bool getnext;
    if(correlationMatrixAllocated) delete[] correlationMatrix;
    correlationMatrix=new double [noofscales*noofscales*noofdelays]; 
    correlationMatrixAllocated=true;
    
    int index=0;
    while(index<noofscales*noofscales*noofdelays){
        correlationMatrix[index]=0;
        index++;
    }

    for (scale=0;scale<noofscales ;scale++) {
        getnext=true;
        for (xscale=0;xscale<noofscales ;xscale++) {     
            for(framedelay=-maxdelay;framedelay<=maxdelay;framedelay++){
               if(getnext){
                    getnext=fsArrayCorr->calcCorrelation(framedelay, scale, xscale ,xcorr);
                    correlationMatrix[(scale*noofscales+xscale)*noofdelays+framedelay+maxdelay]=xcorr;
               }
            }
        }
    }
}


void structureExtractor::calculatorInitialization(){
    int scale, xscale, delay;
    double xcorr;
    thresholdCrossing *TC1,*TC2,*TC3,*TC4;
    thresholdPair pb ;
    
    double  dframeForward=0,dframeBackward=0,dscaleUp=0,dscaleDown=0;
    int dframeForwardStatus,dframeBackwardStatus,dscaleUpStatus,dscaleDownStatus;
    
   // Allocate empty correlation matrix
    if(correlationMatrixAllocated) {delete[] correlationMatrix;};
    correlationMatrix=new double [noofscales*noofscales*noofdelays]; 
    for(int index=0;index<noofscales*noofscales*noofdelays;index++){
        correlationMatrix[index]=0;
    }
    correlationMatrixAllocated=true;
    
    // Initialize pasCalculators for Pulses and Tones
   
    for (scale=0;scale<noofscales ;scale++) {
        
        xscale=scale;delay=0;xcorr=1; 
        correlationMatrix[(scale*noofscales+xscale)*noofdelays+delay+maxdelay]=xcorr;// normalized autocorelation at zero delay is 1 
        
       
        TC1=fsArrayCorr->scanLineFromOrigin(scale,0,  1,   correlationMatrix);
        TC2=fsArrayCorr->scanLineFromOrigin(scale,0, -1,  correlationMatrix);
        
        pb.tc1=TC1;
        pb.tc2=TC2;
        pasCalculators['f']->thresholdsPAxis.push_back(pb);
        
        pb.tc1=new thresholdCrossing(TC1);
        pb.tc2=new thresholdCrossing(TC2);
        pasCalculators['s']->thresholdsOrthoAxis.push_back(pb);
        
        TC1=fsArrayCorr->scanLineFromOrigin(scale, 1, 0,   correlationMatrix);
        TC2=fsArrayCorr->scanLineFromOrigin(scale,-1, 0,  correlationMatrix);
        
        pb.tc1=TC1;
        pb.tc2=TC2;
        pasCalculators['f']->thresholdsOrthoAxis.push_back(pb);
        
        pb.tc1=new thresholdCrossing(TC1);
        pb.tc2=new thresholdCrossing(TC2);
        pasCalculators['s']->thresholdsPAxis.push_back(pb);
        
    }
     
    
    // Initialize pasCalculators for Chirps

     for (scale=0;scale<noofscales ;scale++) {
        
        if(pasCalculators['s']->thresholdsOrthoAxis[scale].tc1->status==thresholdCrossing::found){
                                dframeForward=  (pasCalculators['s']->thresholdsOrthoAxis[scale].tc1->frame_sub \
                                                                + pasCalculators['s']->thresholdsOrthoAxis[scale].tc1->frame_super )/2.0;
                                                                dframeForwardStatus=thresholdCrossing::found;
                }else{
                        dframeForwardStatus=thresholdCrossing::illegalsearch;
                }
                
                
        if(pasCalculators['s']->thresholdsOrthoAxis[scale].tc2->status==thresholdCrossing::found){
                        dframeBackward= (pasCalculators['s']->thresholdsOrthoAxis[scale].tc2->frame_super \
                            + pasCalculators['s']->thresholdsOrthoAxis[scale].tc2->frame_sub)/2.0;
                        dframeBackwardStatus=thresholdCrossing::found;
                }else{
                        dframeBackwardStatus=thresholdCrossing::illegalsearch;
                }
                
                if(pasCalculators['s']->thresholdsPAxis[scale].tc1->status==thresholdCrossing::found){
                        dscaleUp=  (pasCalculators['s']->thresholdsPAxis[scale].tc1->scale_sub \
                                           + pasCalculators['s']->thresholdsPAxis[scale].tc1->scale_super - 2*scale)/2.0;
                        dscaleUpStatus=thresholdCrossing::found;
                }else{
                        dscaleUpStatus=thresholdCrossing::illegalsearch;
                }
                
                if(pasCalculators['s']->thresholdsPAxis[scale].tc2->status==thresholdCrossing::found){
                        dscaleDown= ( pasCalculators['s']->thresholdsPAxis[scale].tc2->scale_super \
                                                   + pasCalculators['s']->thresholdsPAxis[scale].tc2->scale_sub - 2*scale)/2.0;
                        dscaleDownStatus=thresholdCrossing::found;
                }else{
                        dscaleDownStatus=thresholdCrossing::illegalsearch;
                }                     

        // Find threshold in the (1,1) and the (-1,-1) direction
        if(dscaleUpStatus==thresholdCrossing::found && dframeForwardStatus==thresholdCrossing::found){
                        TC3=fsArrayCorr->scanLineFromOrigin(scale,dscaleUp, dframeForward, thresholdCrossing::ifloor , correlationMatrix);
                        TC4=fsArrayCorr->scanLineFromOrigin(scale,dscaleUp, dframeForward, thresholdCrossing::iceil, correlationMatrix);
                        TC1=thresholdCrossing::merge(TC3,TC4);
                        delete TC3;
                        delete TC4;     
                }else{
                        TC1=new thresholdCrossing( 0,  0, 0, 0, 0, 0, 0,thresholdCrossing::illegalsearch, scale);
                }
        
         if(dscaleDownStatus==thresholdCrossing::found && dframeBackwardStatus==thresholdCrossing::found){
                        TC3=fsArrayCorr->scanLineFromOrigin(scale,dscaleDown,dframeBackward, thresholdCrossing::ifloor , correlationMatrix);
                        TC4=fsArrayCorr->scanLineFromOrigin(scale,dscaleDown,dframeBackward, thresholdCrossing::iceil, correlationMatrix);
                        TC2=thresholdCrossing::merge(TC3,TC4);
                        delete TC3;
                        delete TC4;             
                }else{
                        TC2=new thresholdCrossing( 0,  0, 0, 0, 0, 0, 0,thresholdCrossing::illegalsearch, scale);
                }
        
        pb.tc1=TC1;
        pb.tc2=TC2;
        pasCalculators['u']->thresholdsPAxis.push_back(pb);
        pb.tc1=new thresholdCrossing(TC1);
        pb.tc2=new thresholdCrossing(TC2);
        pasCalculators['d']->thresholdsOrthoAxis.push_back(pb);
       
        // Find threshold in the (1,-1)and (-1,1) direction
        if(dscaleUpStatus==thresholdCrossing::found && dframeBackwardStatus==thresholdCrossing::found){
                        TC3=fsArrayCorr->scanLineFromOrigin(scale, dscaleUp,dframeBackward, thresholdCrossing::ifloor , correlationMatrix);
                        TC4=fsArrayCorr->scanLineFromOrigin(scale, dscaleUp,dframeBackward, thresholdCrossing::iceil, correlationMatrix);
                        TC1=thresholdCrossing::merge(TC3,TC4);
                        delete TC3;
                        delete TC4;     
                }else{
                        TC1=new thresholdCrossing( 0,  0, 0, 0, 0, 0, 0,thresholdCrossing::illegalsearch, scale);
                }       
        
        if(dscaleDownStatus==thresholdCrossing::found && dframeForwardStatus==thresholdCrossing::found){
                        TC3=fsArrayCorr->scanLineFromOrigin(scale, dscaleDown,dframeForward, thresholdCrossing::ifloor , correlationMatrix);
                        TC4=fsArrayCorr->scanLineFromOrigin(scale, dscaleDown,dframeForward, thresholdCrossing::iceil, correlationMatrix);
                        TC2=thresholdCrossing::merge(TC3,TC4);
                        delete TC3;
                        delete TC4;     
                }else{
                        TC2=new thresholdCrossing( 0,  0, 0, 0, 0, 0, 0,thresholdCrossing::illegalsearch, scale);
                }       
        
        pb.tc1=TC1;
        pb.tc2=TC2;
        pasCalculators['d']->thresholdsPAxis.push_back(pb);
        pb.tc1=new thresholdCrossing(TC1);
        pb.tc2=new thresholdCrossing(TC2);
        pasCalculators['u']->thresholdsOrthoAxis.push_back(pb);
    }
    
    char ch;
    pasCalculator * pas;
    for(pasCalcIt=pasCalculators.begin();pasCalcIt!=pasCalculators.end();pasCalcIt++){
        ch=(*pasCalcIt).first;
        pas=(*pasCalcIt).second;
        pas->initialize(true,initNoise);
        textureCalculators[ch]= new textureCalculator(pas);
    }

}

void structureExtractor::setDimensions(char textureType, int ns){
    noofscales=ns;
    pasCalculators[textureType]->setDimensions(ns);
};

void structureExtractor::getDimensions(char textureType, int & ns){
   
    pasCalculators[textureType]->getDimensions(ns);
};

void structureExtractor::setPasStats(char textureType, double *Pm, double * Ps,\
                     int * tcSamplePoints, int * tcStatus, double * tcInterpolationDeltas,\
                     int * frameoffsets, int * scaleoffsets ){
    pasCalculators[textureType]->setPasStats( Pm,Ps, tcSamplePoints,  tcStatus,  tcInterpolationDeltas,frameoffsets, scaleoffsets );
};


void structureExtractor::setTextureStats(char textureType, int ns, double *Bm,\
                                         double * Bs, int *areasizes, int *contextAreas,\
                                         int * frameoffsets, int * scaleoffsets){
    int ns_;
    bool nt;
    pasCalculator * pas;
    
    // Get pasCalculator
    assert(pasCalculators.count(textureType)==1);
    pas=pasCalculators[textureType];
    
    // Check consistency with pasCalculator for same textureType
    pas->getDimensions(ns_);
    assert(ns==ns_);
    // ... and get type of normalization
    nt= pas->isNormalized();
    
    // Make sure to delete old textureCalculator before replacing it
    if(textureCalculators.count(textureType)==1){
        delete textureCalculators[textureType];
        textureCalculators.erase(textureType);
    };
    
    //Add new textureCalculator
    textureCalculators[textureType]= new textureCalculator(pas, Bm,  Bs, areasizes, contextAreas, frameoffsets, scaleoffsets,  ns, nt);
                                         
};
