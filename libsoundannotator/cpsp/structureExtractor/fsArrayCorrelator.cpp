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
#include "fsArrayCorrelator.h"
#include <limits>
#include <cmath>
#include <cassert>

fsArrayCorrelator::fsArrayCorrelator( int nframes, int mfd, int nscales, double * fsa){
    
    //assert(noofframes>=2); // To ensure that mean and stddev are defined
    fsArray=new framescaleArray(  nframes, nscales, fsa);
    noofscales=fsArray->noofscales;
    noofframes=fsArray->noofframes;
    maxframedelay=mfd;
    noofdelays=2*mfd+1;
    initialize();
};
        
fsArrayCorrelator::~fsArrayCorrelator(){
        delete[] means ; 
        delete[] squares; 
        delete[] stddevs; 
        delete fsArray;
};
        

void fsArrayCorrelator::initialize(){
    int scale, frame;
    int fsaIndex;
    double * fsa=fsArray->fsArray;
    double fsaElement;
    
    means       =       new double [noofscales]; 
    squares =   new double [noofscales]; 
    stddevs =   new double [noofscales];
    
    // Calculate the mean and standard deviation for each scale 
    //   initialize everything to zero
    for (scale=0;scale<noofscales;scale++) {
        means[scale]=0;
        squares[scale]=0;
        stddevs[scale]=0;
    }
    
    //  calculate the underlying sums
    fsaIndex=0;
    
    for ( scale=0;scale<noofscales;scale++) {
        for ( frame=0;frame<noofframes;frame++){
            fsaElement=fsa[fsaIndex];
            means[scale]    += fsaElement;
            squares[scale]  += fsaElement*fsaElement;        
            fsaIndex++;
        }
    }
    
    //  and determine means and standard deviations from the underlying sums 
    for ( scale=0;scale<noofscales;scale++){
        
        means[scale]/=noofframes;
        stddevs[scale]=squares[scale]-noofframes *means[scale]*means[scale];
        
        if(stddevs[scale] > noofframes*std::numeric_limits<double>::epsilon()){
            stddevs[scale]/=(noofframes-1);
            stddevs[scale]=sqrt(stddevs[scale]);
        }else{
            stddevs[scale]=0;
        }
    }
}


bool fsArrayCorrelator::calcCorrelation(int framedelay,int scale,int xscale, double &xcorr){
        xcorr=0;
        bool xcorrvalid=true;
        int samplecount=noofframes;
    
        int frame, xframe; //xframe should be read cross frame

        for (frame=0,xframe = frame + framedelay;frame<noofframes;frame++,xframe++) {
                if (xframe < 0 || xframe >= noofframes){
                        samplecount--;
                }else{
                        xcorr  += (fsArray->getelement(scale,frame)-means[scale] )*(fsArray->getelement(xscale,xframe)-means[xscale]);
                }
        }
        
        if(samplecount > 1){
            xcorr/=((samplecount-1)*stddevs[scale]*stddevs[xscale]);
        }else{
            xcorrvalid=false;
        }
        
        return xcorrvalid;
}



bool fsArrayCorrelator::updateMatrixIfValid(double &prevxcorr, double &xcorr,int delay, int scale, int xscale, double * correlationMatrix){
    /* A point isValid if it is within the range of delays and scales provided and its
    * predecessor (incoming xcorr) was above the threshold */
    bool ret=(xcorr > thresholdCrossing::threshold && xscale <noofscales && xscale >=0  );
  
    
    if(ret){
        prevxcorr=xcorr;
        xcorr=0;
        ret=calcCorrelation( delay, scale, xscale,xcorr);
        if( delay>=-maxframedelay && delay <= maxframedelay ){
            correlationMatrix[(scale*noofscales+xscale)*noofdelays+delay+maxframedelay]=xcorr;
        }
    }
    
    return ret;
};

thresholdCrossing *   fsArrayCorrelator::scanLineFromOrigin(int scale,int dscale, int dframe, double * correlationMatrix){
        int xscale=scale;
        int delay=0;
        double xcorr=1;
        double prevxcorr=0;
        double delta;
        int status;

        if(0==dscale && 0==dframe) return new thresholdCrossing(scale,0,0,scale,0,0,0,thresholdCrossing::illegalsearch, scale);//avoid infinite loop
        
        do{  
                xscale+=dscale;
                delay +=dframe;
        }while (updateMatrixIfValid(prevxcorr, xcorr,delay,  scale,  xscale, correlationMatrix) )  ; 
        
        if(xcorr <thresholdCrossing::threshold && xscale <noofscales && xscale >=0){        //Threshold found 0 < delta <=1
                delta=(thresholdCrossing::threshold-prevxcorr)/(xcorr-prevxcorr);
                status=thresholdCrossing::found;
        }else{                          //Threshold location out of scope
                delta=0;
                status=thresholdCrossing::notfound;
        }
    
        return new thresholdCrossing(xscale-dscale,delay-dframe,prevxcorr,xscale,delay,xcorr,delta,status,scale);
        
}

thresholdCrossing * fsArrayCorrelator::scanLineFromOrigin(int scale,double dscale, double dframe,  int (*pMap2Int)(double), double * correlationMatrix){
         int xscale=scale;
         int delay=0;
     int prevxscale=scale;
     int prevdelay=0;
         double xcorr=1;
         double prevxcorr=0;
         
         int step; 
         double delta;
         int status;
         assert(0!=dscale && 0!=dframe); // In these cases integer form of this function ought to be used.
        
         if(0==dscale || 0==dframe) return new thresholdCrossing(scale,0,0,scale,0,0,0,thresholdCrossing::illegalsearch,scale);
         
         step=1;
         
         if(std::abs(dscale) < std::abs(dframe)){
                if(dframe < 0) step=-1;
        do{  
                        delay +=step;
                        xscale=scale+pMap2Int(dscale/dframe*delay);
        }while (updateMatrixIfValid(prevxcorr, xcorr,delay,  scale,  xscale, correlationMatrix) )  ;         
        prevdelay=delay - step;
        prevxscale=scale+pMap2Int(dscale/dframe*prevdelay);
        }else{
                if(dscale < 0) step=-1;
        do{  
                        xscale+=step;
                        delay =pMap2Int(dframe/dscale*(xscale-scale));
        }while (updateMatrixIfValid(prevxcorr, xcorr,delay,  scale,  xscale, correlationMatrix) )  ; 
        
        prevxscale=xscale - step;
        prevdelay=pMap2Int(dframe/dscale*(prevxscale-scale));
        };
        
    
    
        if(xcorr <thresholdCrossing::threshold && xscale <noofscales && xscale >=0  ){       //Threshold found 0 < delta <=1
                
        delta=(thresholdCrossing::threshold-prevxcorr)/(xcorr-prevxcorr);
                status=thresholdCrossing::found;
        }else{                          //Threshold location out of scope
                delta=0;
                status=thresholdCrossing::notfound;
        }
        
        
        return new thresholdCrossing(prevxscale,prevdelay,prevxcorr,xscale,delay,xcorr,delta,status,scale);
}

