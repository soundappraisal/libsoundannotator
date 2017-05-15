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
#include "pasCalculator.h"
#include <iostream>
#include <algorithm>
#include <cmath>
#include <cstring>
#include <cassert>

pasCalculator::pasCalculator(){
    isInitialized=false;
    normalizePas=false;    
    PMean=new double[1];
    PSigma=new double[1];
}

pasCalculator::pasCalculator(bool normalize){
    isInitialized=false; 
    normalizePas=normalize;
    PMean=new double[1];
    PSigma=new double[1];
}


pasCalculator::~pasCalculator(){
    if(isInitialized){
        delete PArray;
        delete[] PArrayRaw;
        isInitialized=false;
    }
    delete[] PMean;
    delete[] PSigma;
    for_each(thresholdsPAxis.begin(),thresholdsPAxis.end(),thresholdPair::cleanup);
    for_each(thresholdsOrthoAxis.begin(),thresholdsOrthoAxis.end(),thresholdPair::cleanup);
}

bool pasCalculator::isNormalized(){return normalizePas;}

void pasCalculator::initialize(bool bWhite, framescaleArray * fsa ){
    int scale=0;
    thresholdPairVector::iterator it;
    
    noofscales= fsa->noofscales;
    noofframes= fsa->noofframes;
    
   
    setMargins(fsa->margin);
      
    if(normalizePas){
        
        if(isInitialized){
            delete[] PArray;
            delete[] PArrayRaw;
        }

        // Allocate P matrix
        PArrayRaw=new double[noofframes*noofscales];
        for(int k=0;k<noofframes*noofscales;k++){ PArrayRaw[k]=0;}
        PArray=new framescaleArray(fsa->noofframes,fsa->noofscales ,PArrayRaw);
        PArray->setMargins(myMargins);
        isInitialized=true;
        
        // Allocate PMean and PSigma matrices and initialize them for calculating 
        // unnormalized P values
        delete[] PMean;
        PMean=new double[noofscales];
        for(int k=0;k<noofscales;k++){ PMean[k]=0;}
        
        
        delete[] PSigma;
        PSigma=new double[noofscales];
        for(int k=0;k<noofscales;k++){ PSigma[k]=1;} 
       
        // Calculate P scale by scale
        for ( it=thresholdsPAxis.begin(),scale=0 ; it < thresholdsPAxis.end(); it++, scale++ ){
            calcP4Scale(scale, it->tc1, it->tc2,  fsa );
        }


        // Reinitialize PMean and PSigma matrices for calculating 
        // normalized P values
        calcPMoments(bWhite,  fsa );
       
        // Calculate normalized P scale by scale
        for ( it=thresholdsPAxis.begin(),scale=0 ; it < thresholdsPAxis.end(); it++, scale++ ){
            calcP4Scale(scale, it->tc1, it->tc2,fsa);
        }
    }
};

void pasCalculator::setMargins(_margin InMargin){
    int scale=0;
    
    thresholdCrossing* tc1,* tc2;
    thresholdPairVector::iterator it;
    
    int low_scale_horizon;
    int high_scale_horizon;
    int low_frame_horizon;
    int high_frame_horizon;
    marginCalculator * myMarginCalculator;
  
    myMarginCalculator = new marginCalculator(noofscales);
    
// Calculate minimally safe offset valid for all scales
    for ( it=thresholdsPAxis.begin(),scale=0; it != thresholdsPAxis.end(); it++,scale++){
        tc1= it->tc1;
        tc2= it->tc2;
        if(tc1->status==thresholdCrossing::found && tc2->status==thresholdCrossing::found){
            if(tc1->frame_sub < tc2->frame_sub){
                low_frame_horizon=tc1->frame_sub;
                high_frame_horizon=tc2->frame_sub;
            }else{
                high_frame_horizon=tc1->frame_sub;
                low_frame_horizon=tc2->frame_sub;
            }
            
            if(tc1->scale_sub < tc2->scale_sub){
                low_scale_horizon=tc1->scale_sub-scale;
                high_scale_horizon=tc2->scale_sub-scale;
            }else{
                high_scale_horizon=tc1->scale_sub-scale;
                low_scale_horizon=tc2->scale_sub-scale;
            }
            
            low_scale_horizon = std::abs(low_scale_horizon);
            high_scale_horizon= std::abs(high_scale_horizon);
            low_frame_horizon = std::abs(low_frame_horizon);
            high_frame_horizon= std::abs(high_frame_horizon);
            
            myMarginCalculator->setRegionDescriptor(scale,\
                        low_scale_horizon,high_scale_horizon,\
                        low_frame_horizon,high_frame_horizon);
        }
   }
   
   myMargins= myMarginCalculator->calcMargins(InMargin);
   delete myMarginCalculator;
};

_margin pasCalculator::getMargins(){
    return myMargins;
} 

void pasCalculator::calcPas(framescaleArray * fsa ){
    int scale=0;
    thresholdPairVector::iterator it;
    noofframes=fsa->noofframes; 
    assert(noofscales == fsa->noofscales);
    
    // Allocate P matrix
    if(isInitialized) {
            delete PArray;
            delete[] PArrayRaw;
    }
    
    PArrayRaw=new double[noofframes*noofscales];
    for(int k=0;k<noofframes*noofscales;k++){ PArrayRaw[k]=0;}
    PArray=new framescaleArray(fsa->noofframes,fsa->noofscales ,PArrayRaw);
    PArray->setMargins(myMargins);
                
    isInitialized=true;

    // Calculate P scale by scale
    for ( it=thresholdsPAxis.begin(),scale=0 ; it < thresholdsPAxis.end(); it++, scale++ ){
        calcP4Scale(scale, it->tc1, it->tc2,fsa);
    }
    
}

void pasCalculator::calcP4Scale(int scale,  thresholdCrossing* tc1, thresholdCrossing * tc2,framescaleArray * fsa){
    int scalep[2], scaleb[2];
    int framep[2], frameb[2];
    double delta[2];
    int runframe;
    int startframe;
    int endframe;
    int point;

    if(tc1->status==thresholdCrossing::found && tc2->status==thresholdCrossing::found){
        // Get stored threshold crossing locations 
        scalep[0]=tc1->scale_super      ;scalep[1]=tc2->scale_super;
        scaleb[0]=tc1->scale_sub        ;scaleb[1]=tc2->scale_sub;
        framep[0]=tc1->frame_super      ;framep[1]=tc2->frame_super;
        frameb[0]=tc1->frame_sub        ;frameb[1]=tc2->frame_sub;
        delta[0] =tc1->delta            ;delta[1]=tc2->delta;
        
        // Calculate P for each frame for which threshold crossing location are within range
        // ... find valid startframe
        startframe=PArray->getfirstvalidframe();
        // ... find valid endframe
        endframe=PArray->getlastvalidframe()+1;
       
        // ... and calculate
        for(point=0;point <2; point++){
            for(runframe=startframe;runframe< endframe;runframe++){
               PArrayRaw[PArray->index(scale,runframe)]-=\
                   (1-delta[point])*fsa->getelement(scalep[point],runframe+framep[point])+\
                   delta[point]*fsa->getelement(scaleb[point],runframe+frameb[point]);    
            }
        }               
        
        if(normalizePas){
            for(runframe=startframe;runframe< endframe;runframe++){
                PArrayRaw[PArray->index(scale,runframe)]/=2;
                PArrayRaw[PArray->index(scale,runframe)]+=fsa->getelement(scale,runframe);
                        
                PArrayRaw[PArray->index(scale,runframe)]-=PMean[scale];
                PArrayRaw[PArray->index(scale,runframe)]/=PSigma[scale];
            }
                }else{
            for(runframe=startframe;runframe< endframe;runframe++){
                PArrayRaw[PArray->index(scale,runframe)]/=2;
                PArrayRaw[PArray->index(scale,runframe)]+=fsa->getelement(scale,runframe);
            }
        }        
    }
};



void pasCalculator::calcPMoments(bool bWhite,framescaleArray * fsa){
    // Calculate P scale by scale
    int scale=0;
    thresholdCrossing *tc1, *tc2;
    thresholdPairVector::iterator it;
    double PSquared;
    assert(normalizePas);
    int runframe;
    int startframe;
    int endframe;
    double PElement;
    
        for ( it=thresholdsPAxis.begin() ; it < thresholdsPAxis.end(); it++, scale++ ){
            tc1=it->tc1;
            tc2=it->tc2; 
            if(tc1->status==thresholdCrossing::found && tc2->status==thresholdCrossing::found){
                
                // Calculate PMean and PSigma over those frames for which threshold crossing location are within range.
                // ... find valid startframe
                startframe=PArray->getfirstvalidframe();
                // ... find valid endframe
                endframe=PArray->getlastvalidframe()+1;
            
                // ... and calculate
                PMean[scale]=0; 
                PSquared=0;
                
                if( bWhite){ // For white noise and normalized filters PMean is zero
                    for(runframe=startframe;runframe< endframe;runframe++){
                        PElement=PArray->getelement(scale,runframe);
                        PSquared+=PElement*PElement;    
                    }
                    PSigma[scale]=std::sqrt(PSquared/(endframe-startframe));
                }else{
                    for(runframe=startframe;runframe< endframe;runframe++){
                        PElement=PArray->getelement(scale,runframe);
                        PMean[scale]+=PElement; 
                        PSquared+=PElement*PElement;    
                    }
                    PMean[scale]/=endframe-startframe; 
                    PSigma[scale]=std::sqrt((PSquared/(endframe-startframe)-PMean[scale]*PMean[scale])); 
                }
            }
        }
};

void  pasCalculator::getPas (double *P ){
    if(isInitialized){
        std::memcpy(P,PArrayRaw,sizeof(double)*noofscales*noofframes);
    };
};


void  pasCalculator::getPasStats(double *Pm, double *Ps, int * tcSamplePoints, int * tcStatus, double * tcInterpolationDeltas, int * frameoffsets, int * scaleoffsets ){
    if(normalizePas){
        std::memcpy(Pm, PMean ,sizeof(double)*noofscales );
        std::memcpy(Ps, PSigma,sizeof(double)*noofscales );
    }
    
   // From thresholdPairVector thresholdsPAxis ,  thresholdPairVector thresholdsOrthoAxis get
    thresholdPairVector::iterator it;
    int scale=0;
    
    frameoffsets[0]=myMargins.firstframe_offset;
    frameoffsets[1]=myMargins.lastframe_offset;
    scaleoffsets[0]=myMargins.firstscale_offset;
    scaleoffsets[1]=myMargins.lastscale_offset;
    
    for ( it=thresholdsPAxis.begin() ; it < thresholdsPAxis.end(); it++, scale++ ){
        tcSamplePoints[scale*8]  =it->tc1->scale_super;
        tcSamplePoints[scale*8+1]=it->tc1->frame_super;
        tcSamplePoints[scale*8+2]=it->tc1->scale_sub;
        tcSamplePoints[scale*8+3]=it->tc1->frame_sub;
        
        tcSamplePoints[scale*8+4]=it->tc2->scale_super;
        tcSamplePoints[scale*8+5]=it->tc2->frame_super;
        tcSamplePoints[scale*8+6]=it->tc2->scale_sub;
        tcSamplePoints[scale*8+7]=it->tc2->frame_sub;
        
        tcStatus[scale*2]=it->tc1->status;
        tcStatus[scale*2+1]=it->tc2->status;
        tcInterpolationDeltas[scale*2]=it->tc1->delta;
        tcInterpolationDeltas[scale*2+1]=it->tc2->delta;
    }
    
    for ( it=thresholdsOrthoAxis.begin(); it < thresholdsOrthoAxis.end(); it++, scale++ ){
                
        tcSamplePoints[scale*8]  =it->tc1->scale_super;
        tcSamplePoints[scale*8+1]=it->tc1->frame_super;
        tcSamplePoints[scale*8+2]=it->tc1->scale_sub;
        tcSamplePoints[scale*8+3]=it->tc1->frame_sub;
        
        tcSamplePoints[scale*8+4]=it->tc2->scale_super;
        tcSamplePoints[scale*8+5]=it->tc2->frame_super;
        tcSamplePoints[scale*8+6]=it->tc2->scale_sub;
        tcSamplePoints[scale*8+7]=it->tc2->frame_sub;
        
        tcStatus[scale*2]=it->tc1->status;
        tcStatus[scale*2+1]=it->tc2->status;
        tcInterpolationDeltas[scale*2]=it->tc1->delta;
        tcInterpolationDeltas[scale*2+1]=it->tc2->delta;
        }
    
};

void  pasCalculator::setPasStats(double *Pm, double *Ps, int * tcSamplePoints, int * tcStatus, double * tcInterpolationDeltas, int * frameoffsets, int * scaleoffsets ){
    int scale=0;
    thresholdPair pb ;
    
    if(normalizePas){
        // Allocate PMean and PSigma matrices and initialize them for calculating 
        // unnormalized P values
        delete[] PMean;
        PMean=new double[noofscales];
        
        
        delete[] PSigma;
        PSigma=new double[noofscales];
        
        std::memcpy( PMean ,Pm, sizeof(double)*noofscales );
        std::memcpy( PSigma,Ps, sizeof(double)*noofscales );
    }
  
 
        myMargins.firstframe_offset=frameoffsets[0];
        myMargins.lastframe_offset=frameoffsets[1];
        myMargins.firstscale_offset=scaleoffsets[0];
        myMargins.lastscale_offset=scaleoffsets[1];
    
        for (scale=0 ; scale < noofscales; scale++ ){
        pb.tc1=new thresholdCrossing(\
             tcSamplePoints[scale*8],\
             tcSamplePoints[scale*8+1],\
             0,\
             tcSamplePoints[scale*8+2],\
             tcSamplePoints[scale*8+3],\
             0,\
             tcInterpolationDeltas[scale*2],\
             tcStatus[scale*2],\
             scale\
         );
         pb.tc2=new thresholdCrossing(\
             tcSamplePoints[scale*8+4],\
             tcSamplePoints[scale*8+5],\
             0,\
             tcSamplePoints[scale*8+6],\
             tcSamplePoints[scale*8+7],\
             0,\
             tcInterpolationDeltas[scale*2+1],\
             tcStatus[scale*2+1],\
             scale\
         );
        
        thresholdsPAxis.push_back(pb);
        }
    
        for (scale=0 ; scale < noofscales; scale++ ){
        pb.tc1=new thresholdCrossing(\
             tcSamplePoints[scale*8],\
             tcSamplePoints[scale*8+1],\
             0,\
             tcSamplePoints[scale*8+2],\
             tcSamplePoints[scale*8+3],\
             0,\
             tcInterpolationDeltas[scale*2],\
             tcStatus[scale*2],\
             scale\
         );
         
         pb.tc2=new thresholdCrossing(\
             tcSamplePoints[scale*8+4],\
             tcSamplePoints[scale*8+5],\
             0,\
             tcSamplePoints[scale*8+6],\
             tcSamplePoints[scale*8+7],\
             0,\
             tcInterpolationDeltas[scale*2+1],\
             tcStatus[scale*2+1],\
             scale\
         );
         
        thresholdsOrthoAxis.push_back(pb);
        }
};


struct pasCalculatorDeleter {        
    void operator()(std::pair<const char, pasCalculator * > & p){ 
        delete p.second;
        p.second = NULL;
    }
};

void pasCalculator::pasCalculatorMapCleanup(pasCalculatorMap & pMap){ 
        pasCalculatorDeleter myPasCalculatorDeleter;
        for_each(pMap.begin(),pMap.end(),myPasCalculatorDeleter);
};

void pasCalculator::setDimensions(int ns){
    noofscales=ns;
};

void pasCalculator::getDimensions(int & ns){
    ns= noofscales;
}
