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
#ifndef FRAMESCALEARRAY_H
#define FRAMESCALEARRAY_H

#include <string>

// The regiondescriptors indicate roughly from which area in the incoming 
// representation values are used to define 
struct regionDescriptor{
    int centerscale;
    int low_scale_horizon;
    int high_scale_horizon;
    int low_frame_horizon;
    int high_frame_horizon;
    bool valid;
};

        
struct _margin{
	int firstframe_offset;
	int lastframe_offset;
	int firstscale_offset;
	int lastscale_offset;
};


class marginCalculator{
    public:
        marginCalculator(int noofscales);
        ~marginCalculator();
        _margin calcMargins(_margin inMargin);
        void setRegionDescriptor(int scale,int lso,int hso ,int ffo,int lfo);
    
    private:
        int noofscales;
        regionDescriptor *regionDescriptors;
};


class framescaleArray {
    public:
    
        double * fsArray;
        framescaleArray(int nf, int ns, double * fsa);
        int noofframes;
        int noofscales;
    
        
        
        bool reset(int nf, int ns, double * fsa);  
        
        /* inline double getelement(int scale, int frame){
            bool validindex;
            std::string functionname ("getelement");


            validindex=checkbounds(scale,frame,functionname);
            
            if(validindex){
                return fsArray[scale*noofframes + frame];
            }           
            return 0;
        }
        
        inline int index(int scale, int frame){
            bool validindex;
            std::string functionname ("index");
            validindex=checkbounds(scale,frame,functionname);
            
            if(validindex){
                return scale*noofframes + frame;
            }
            return 0;            
        }*/
        
        inline double getelement(int scale, int frame){
            return fsArray[scale*noofframes + frame];
        }
        
        inline int index(int scale, int frame){
                return scale*noofframes + frame;
        }
        
        bool invalidindices;
        bool checkbounds(int scale, int frame, std::string name);
        void setMargins(int ffo,int lfo,int fso,int lso);
        void setMargins(_margin M);
        _margin margin;
        
         
        int getfirstvalidframe();
        int getlastvalidframe();
        int getfirstvalidscale();
        int getlastvalidscale();
        bool isValid(int scale);
        
};




#endif // FRAMESCALEARRAY_H
