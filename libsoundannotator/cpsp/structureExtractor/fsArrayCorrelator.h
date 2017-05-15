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
#ifndef FSARRAYCORRELATOR_H
#define FSARRAYCORRELATOR_H

#include "thresholdCrossing.h"
#include "framescaleArray.h"

class fsArrayCorrelator{
    public:
        fsArrayCorrelator( int noofframes, int maxframedelay, int noofscales, double * fsa);
        ~fsArrayCorrelator();
         // Functions and variables for correlation calculations
        bool calcCorrelation(int framedelay,int scale,int xscale , double &xcorr);
        thresholdCrossing * scanLineFromOrigin(int scale,int dscale, int dframe, double * correlationMatrix);
        thresholdCrossing * scanLineFromOrigin(int scale,double dscale, double dframe,int (*pMap2IntFunction)(double), double * correlationMatrix);
        bool updateMatrixIfValid(double &prevxcorr, double &xcorr,int delay, int scale, int xscale, double * correlationMatrix);
		
    private:
        int maxframedelay;
        int noofdelays;
        int noofscales;
        int noofframes;
        double * means; 
        double * stddevs;
        double * squares;
        framescaleArray* fsArray;
        void initialize();
};

#endif // FSARRAYCORRELATOR_H

