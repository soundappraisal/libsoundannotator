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
#include "thresholdCrossing.h"
#include <cmath>

double thresholdCrossing::threshold=0.2;

// Copy constructor
thresholdCrossing::thresholdCrossing( thresholdCrossing* tc){
    scale_center=tc->scale_center;
    scale_super=tc->scale_super;
    frame_super=tc->frame_super;
    xcorr_super=tc->xcorr_super;
    scale_sub=tc->scale_sub;
    frame_sub=tc->frame_sub;
    xcorr_sub= tc->xcorr_sub;
    delta=tc->delta;
    status=tc->status ;
};   
                              
// Rescaled Copy constructor
thresholdCrossing::thresholdCrossing( thresholdCrossing* tc, double factor ){
     scale_center=tc->scale_center;
     xcorr_super=tc->xcorr_super;
     xcorr_sub= tc->xcorr_sub;
     
     delta=tc->delta;
     status=tc->status ;
    
    frame_super=iroundaway(factor*tc->frame_super);
    frame_sub=iroundaway(factor*tc->frame_sub);
   
    scale_super=iroundaway(factor*(tc->scale_super-tc->scale_center))+tc->scale_center;
    scale_sub  =iroundaway(factor*(tc->scale_sub-tc->scale_center))+tc->scale_center;
    
};    

 
thresholdCrossing* thresholdCrossing::merge(thresholdCrossing* tc1, thresholdCrossing* tc2){
	thresholdCrossing* tcout;
	
	// Check if 
	if(tc1->status!=thresholdCrossing::found){
		tcout=new thresholdCrossing(tc2);
		return tcout;
	}
	
	if(tc2->status!=thresholdCrossing::found){
		tcout=new thresholdCrossing(tc1);
		return tcout;
	}
	
	// OK tc1 and tc2 are valid, so we can merge them
	tcout=new thresholdCrossing(tc1);
	if(tc2->xcorr_super < tc1->xcorr_super){
		tcout->xcorr_super=tc2->xcorr_super;
		tcout->scale_super=tc2->scale_super;
		tcout->frame_super=tc2->frame_super;
	}
	
	if(tc2->xcorr_sub > tc1->xcorr_sub){
		tcout->xcorr_sub=tc2->xcorr_sub;
		tcout->scale_sub=tc2->scale_sub;
		tcout->frame_sub=tc2->frame_sub;
	}
	
	tcout->delta=(thresholdCrossing::threshold-tcout->xcorr_super)/(tcout->xcorr_sub-tcout->xcorr_super);
	return tcout;
};

int thresholdCrossing::iroundaway(double x){
    return (int) (x > 0.0) ?  std::ceil(x ) : std::floor(x) ;
}


int thresholdCrossing::ifloor(double arg){return (int) std::floor(arg);};
int thresholdCrossing::iceil(double arg){return (int) std::ceil(arg);};
