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
#ifndef THRESHOLDCROSSING_H
#define THRESHOLDCROSSING_H
#include <vector>

class thresholdCrossing {
    public:
        thresholdCrossing( int sp, int fp, double xp, int sb, int fb, double xb, double d, int s, int ctr ): \
                            scale_center(ctr), scale_super(sp),frame_super(fp), xcorr_super(xp),\
                            scale_sub(sb), frame_sub(fb), xcorr_sub(xb), \
                            delta(d), status(s){
                            };
        thresholdCrossing( thresholdCrossing* tc); 
        thresholdCrossing( thresholdCrossing* tc, double factor); 
        
        // center scale
        int scale_center;
                        
        // Last superthreshold point in line scan
        int scale_super;
        int frame_super;
        double xcorr_super;
        
        // First subthreshold point in line scan
        int scale_sub;
        int frame_sub;
        double xcorr_sub;
        
        // Best estimate for real location of threshold (threshold)  on the line starting from the last superthreshold point in the correlation matrix (cm)to the first subthreshold point.
        double delta;     // delta=threshold-cm(scale_super,frame_super)/(cm(scale_sub,frame_sub)-cm(scale_super,frame_super))
        //std::vector <double> lineDirection;
    
        static int iroundaway( double x); // round away from zero
        static int ifloor(double arg);
        static int iceil(double arg);
        
        static thresholdCrossing* merge (thresholdCrossing*, thresholdCrossing*);
        static double threshold;
        
        // Line scan mechanisms need to return a value even if the scan ends prematurely on the edge of the TS plane or the scan is ill posed, e.g. zero increment
        int status;
        
        // Status values
        static int const found=1;
		static int const notfound=2;
		static int const illegalsearch=3;
};

// derived data types



#endif //THRESHOLDCROSSING_H
