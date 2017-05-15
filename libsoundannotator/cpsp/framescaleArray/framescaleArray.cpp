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
#include "framescaleArray.h"
#include <cassert>
#include <iostream>

framescaleArray::framescaleArray(int nf, int ns, double * fsa) {
    noofframes=nf;
    noofscales=ns;
    fsArray=fsa;
	invalidindices=false;    
    setMargins(0,0,0,0);
};

    


bool framescaleArray::reset(int nf, int ns, double * fsa){
    if(ns!=noofscales) return false;
    noofframes=nf;
    fsArray=fsa;
    return true;
}

// Following code and calls to it can be removed later

bool  framescaleArray::checkbounds(int scale, int frame, std::string name){
    bool result=true;
    if(scale<0 || scale >=noofscales || frame <0 ||frame >=noofframes) {
       std::cout << "framescaleArray: "<< name <<" : " << \
           scale + frame*noofscales << " is out of bounds, scale: " << scale  << "frame" <<frame << \
           " noofscales: " << noofscales  << "noofframes" <<noofframes <<std::endl;
           result=false;
    }else if((scale<margin.firstscale_offset || scale >=noofscales-margin.lastscale_offset || frame <margin.firstframe_offset ||frame >=noofframes-margin.lastframe_offset )&& invalidindices==false) {
			std::cout <<  name << " : scale or frame is invalid, scale: " << scale  << "frame" <<frame <<std::endl;
			invalidindices=true;
            result=false;
    }
    
    return result;
}


void framescaleArray::setMargins(int ffo,int lfo,int fso,int lso){
    margin.firstframe_offset=ffo;
    margin.lastframe_offset=lfo;
    margin.firstscale_offset=fso;
    margin.lastscale_offset=lso;
};

void framescaleArray::setMargins(_margin M){
    margin=M;
};


int framescaleArray::getfirstvalidframe(){
    return margin.firstframe_offset;
};
int framescaleArray::getlastvalidframe(){
    return noofframes-margin.lastframe_offset-1;
};
int framescaleArray::getfirstvalidscale(){
    return margin.firstscale_offset;
};
int framescaleArray::getlastvalidscale(){
    return noofscales-margin.lastscale_offset-1;
};


bool framescaleArray::isValid(int scale){
    bool valid=false;
    
    if(scale >= getfirstvalidscale() && scale <= getlastvalidscale() ){
        valid=true;
    }
    
    return valid;
};

_margin  marginCalculator::calcMargins(_margin preMargin ){
    _margin outMargin;
    regionDescriptor rd;
    int scale=0;
    outMargin.firstframe_offset=-1;
	outMargin.firstscale_offset=-1;
	outMargin.lastframe_offset=-1;
	outMargin.lastscale_offset=-1;
    
    // Find valid scales
    while(outMargin.firstscale_offset==-1 && scale < noofscales) {
        rd=regionDescriptors[scale];
        if(rd.valid && scale >= preMargin.firstscale_offset+rd.low_scale_horizon ){
	         outMargin.firstscale_offset=preMargin.firstscale_offset+rd.low_scale_horizon;
        }
        scale++;
    }

    scale=noofscales-1;
    while(outMargin.lastscale_offset==-1 && scale>=0){
        rd=regionDescriptors[scale];
        if(rd.valid && scale < noofscales-preMargin.lastscale_offset-rd.high_scale_horizon ){
	         outMargin.lastscale_offset=preMargin.lastscale_offset+rd.high_scale_horizon;
        }
        scale--;
    }
    
    // ... alas no valid scales have been found
    if(outMargin.firstscale_offset==-1 || outMargin.lastscale_offset==-1 ){
	     outMargin.firstscale_offset=noofscales;
         outMargin.lastscale_offset=noofscales;
    }
     
    // Find frame offsets, loop is constructed in such fashion that only valid scales are used.
    for(scale=outMargin.firstscale_offset;scale < noofscales-outMargin.lastscale_offset; scale++){
        rd=regionDescriptors[scale];
        outMargin.firstframe_offset=std::max(outMargin.firstframe_offset, preMargin.firstframe_offset+rd.low_frame_horizon);
        outMargin.lastframe_offset =std::max(outMargin.lastframe_offset, preMargin.lastframe_offset+rd.high_frame_horizon);
    }
        
    assert(outMargin.lastscale_offset + outMargin.firstscale_offset < noofscales);
    return outMargin;
};

marginCalculator::marginCalculator(int ns){
    noofscales=ns;
    regionDescriptors = new  regionDescriptor[noofscales];
    for(int scale=0;scale< noofscales;scale++){
        regionDescriptors[scale].centerscale=scale;
        regionDescriptors[scale].low_scale_horizon=0;
        regionDescriptors[scale].high_scale_horizon=0;
        regionDescriptors[scale].low_frame_horizon=0;
        regionDescriptors[scale].high_frame_horizon=0;
        regionDescriptors[scale].valid=false;
    }
};

void marginCalculator::setRegionDescriptor(int scale,int lsh,int hsh ,int lfh,int hfh){
    assert(regionDescriptors[scale].centerscale==scale);
    regionDescriptors[scale].low_scale_horizon=lsh;
    regionDescriptors[scale].high_scale_horizon=hsh;
    regionDescriptors[scale].low_frame_horizon=lfh;
    regionDescriptors[scale].high_frame_horizon=hfh;
    regionDescriptors[scale].valid=true;
};

marginCalculator::~marginCalculator(){
    delete[] regionDescriptors;
};
