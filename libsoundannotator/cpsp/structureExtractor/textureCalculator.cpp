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
#include "textureCalculator.h"
#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <cstring>
#include <cassert>

textureCalculator::textureCalculator( pasCalculator * pas){
        pasCalc=pas;
        
        noofscales= pas->noofscales;
        noofframes= 0;
        BMean=new double[1];
        BSigma=new double[1];
        areaSize=new int[noofscales];
        isInitialized=false;
        BBlocksAllocated=false;
        makeBBlockVector(0.7, 2.0);
        setMargins(pas->getMargins());
        normalizeTexture=pas->isNormalized();
        initialize();        
}

textureCalculator::~textureCalculator(){
    
    delete[] BMean;
    delete[] BSigma;
    delete[] areaSize;
    if(isInitialized){ 
        delete BArray;
        delete[] BArrayRaw;
        isInitialized=false;
    }
    
    if(BBlocksAllocated){ 
        deleteBBlocks(BBlocks);
        BBlocksAllocated=false;
   }
}


textureCalculator::textureCalculator(pasCalculator * pas, double *Bm, double *Bs,\
                                    int *_areaSizes, int *contextAreas,\
                                    int * frameoffsets, int * scaleoffsets,\
                                    int ns, bool nt){ 
    
    BInterval   * Bint;
    BBlock      * BBl;
    pasCalc=pas;
    noofscales=ns;
    normalizeTexture=nt;
    assert(noofscales==pas->noofscales);
    noofframes= 0;
    BMean=new double[1];
    BSigma=new double[1];
    
    areaSize=new int[noofscales];
    std::memcpy(areaSize,_areaSizes,sizeof(int)*noofscales );
    
    isInitialized=false;
      
    BBlocks = new BBlockVector();
    BBlocksAllocated=true;
    
    int scale, runscale;
   
    myMargins.firstframe_offset=frameoffsets[0];
    myMargins.lastframe_offset=frameoffsets[1];
    myMargins.firstscale_offset=scaleoffsets[0];
    myMargins.lastscale_offset=scaleoffsets[1];
   
   
    bool blockempty;
    for( scale=0;scale<noofscales;scale++){   
        // Create a instance of BBl  
        blockempty=true;
        BBl=new BBlock();
        for(runscale=0;runscale<noofscales;runscale++){
                      
            Bint=new BInterval();
            Bint->scale=scale;
            assert(runscale==contextAreas[scale*3*noofscales+runscale+2*noofscales]);
            Bint->runscale=runscale;
            Bint->startFrame=contextAreas[scale*3*noofscales+runscale] ;
            Bint->endFrame=contextAreas[scale*3*noofscales+runscale+1*noofscales];
            if(Bint->startFrame != Bint->endFrame){
                BBl->push_back(Bint);
                blockempty=false;
            }else{
                delete Bint;
            }
        } 
        
        if(!blockempty){
            BBlocks->push_back(BBl);}
        else
            delete BBl;
    }
     

    
    if(normalizeTexture){
        delete[] BMean;
        BMean=new double[noofscales];
            
            
        delete[] BSigma;
        BSigma=new double[noofscales];
       
        std::memcpy( BMean, Bm,sizeof(double)*noofscales );
        std::memcpy( BSigma, Bs, sizeof(double)*noofscales );
    }
 
};

void textureCalculator::initialize(){
    framescaleArray * PArray;
    BBlockVector::iterator contextArea;

    if(normalizeTexture){
        // Allocate B matrix
        PArray=pasCalc->PArray;
        noofscales= PArray->noofscales;
        noofframes= PArray->noofframes;

        if(isInitialized){
            delete BArray;
            delete BArrayRaw;
        }

        BArrayRaw=new double[noofframes*noofscales];
        for(int k=0;k<noofframes*noofscales;k++){ BArrayRaw[k]=0;}
        BArray=new framescaleArray(PArray->noofframes,PArray->noofscales, BArrayRaw);
        BArray->setMargins(myMargins);
        isInitialized=true;

        // Allocate BMean and BSigma matrices and initialize them for calculating 
        // unnormalized B values
        delete[] BMean;
        BMean=new double[noofscales];
        for(int k=0;k<noofscales;k++){ BMean[k]=0;}


        delete[] BSigma;
        BSigma=new double[noofscales];
        for(int k=0;k<noofscales;k++){ BSigma[k]=1;} 

        // Calculate B scale by scale

        for ( contextArea = BBlocks->begin() ; contextArea < BBlocks->end() ; contextArea++ ){
            calcB4contextArea(PArray, *contextArea);
            calcBMoments(*contextArea);
        }
     }
};


void textureCalculator::calcTexture(framescaleArray * fsa){
    noofframes=fsa->noofframes; 
    assert(noofscales == fsa->noofscales);
    
    BBlockVector::iterator contextArea;
    if(isInitialized){
        delete BArray;
        delete BArrayRaw; 
    }
    
    // Allocate B matrix
    BArrayRaw=new double[noofframes*noofscales];
    for(int k=0;k<noofframes*noofscales;k++){ BArrayRaw[k]=0;}
                                    
    BArray=new framescaleArray(fsa->noofframes,fsa->noofscales, BArrayRaw);
    BArray->setMargins( myMargins );
    isInitialized=true;
    
    // Calculate B scale by scale
    for ( contextArea = BBlocks->begin() ; contextArea < BBlocks->end() ; contextArea++ ){
        
        calcB4contextArea(fsa, *contextArea);
    } 
   
};

void textureCalculator::calcB4contextArea(framescaleArray * PArray, BBlock * contextArea){
    BBlock::iterator currentBInterval;
    int  startFrame=std::max(0,BArray->getfirstvalidframe());
    int  endFrame=std::min(noofframes,BArray->getlastvalidframe());
    double P;
    int centerframe, runframe;

    // Get an arbitrary valid iterator from the contextArea
    if(contextArea->begin()==contextArea->end() ){
        return;
    }

    currentBInterval=contextArea->begin();
    int   scale;
    scale = (*currentBInterval)->scale;
    
    // Check whether the scale is valid
    if(!BArray->isValid(scale)){
        return;
    }
    
    startFrame=BArray->getfirstvalidframe();
    endFrame=BArray->getlastvalidframe();
    
    // Calculate full value for first contextArea
    centerframe=startFrame;    
    for(currentBInterval=contextArea->begin();currentBInterval != contextArea->end(); currentBInterval++){
        for(runframe= centerframe+(*currentBInterval)->startFrame; runframe <=centerframe+(*currentBInterval)->endFrame  ;runframe++){
            P=PArray->getelement((*currentBInterval)->runscale,runframe);
            BArrayRaw[BArray->index(scale,centerframe)]+=P*P;
        }
    }

    // Update value for new contextArea
    for( centerframe=startFrame+1;centerframe<endFrame+1;centerframe++){
        BArrayRaw[BArray->index(scale,centerframe)]=BArray->getelement(scale,centerframe-1);
        for(currentBInterval=contextArea->begin();currentBInterval < contextArea->end(); currentBInterval++){
                runframe= centerframe+(*currentBInterval)->startFrame-1;
                P=PArray->getelement((*currentBInterval)->runscale,runframe);
                BArrayRaw[BArray->index(scale,centerframe)]-=P*P;

                runframe= centerframe+(*currentBInterval)->endFrame;
                P=PArray->getelement((*currentBInterval)->runscale,runframe);
                BArrayRaw[BArray->index(scale,centerframe)]+=P*P;
        }
    }  

    // Normalize
    if(normalizeTexture){
        for( centerframe=startFrame;centerframe<endFrame+1;centerframe++){
            BArrayRaw[BArray->index(scale,centerframe)]/=areaSize[ scale ];
            BArrayRaw[BArray->index(scale,centerframe)]-=BMean[ scale ];
            BArrayRaw[BArray->index(scale,centerframe)]/=BSigma[ scale ];
        }
    }else{
        for( centerframe=startFrame;centerframe<endFrame+1;centerframe++){
            BArrayRaw[BArray->index(scale,centerframe)]/=areaSize[ scale ];
        }
    }
};

void textureCalculator::calcBMoments(BBlock * contextArea){
    BBlock::iterator currentBInterval;
    double BSquared;
    double BElement;
    int scale;
    int  startFrame;
    int  endFrame;
    assert(normalizeTexture);
    assert(contextArea->begin() != contextArea->end()); // Empty context area's should have been removed before calling this function
    
    currentBInterval=contextArea->begin();
    scale=(*currentBInterval)->scale;
    
    // Check whether the scale is valid
    if(! BArray->isValid(scale)){return;}
    startFrame=BArray->getfirstvalidframe();
    endFrame=BArray->getlastvalidframe();
    
    // ... and calculate
    BMean[scale]=0; 
    BSquared=0;
   
    for(int runframe=startFrame;runframe<= endFrame;runframe++){
        BElement=BArray->getelement(scale,runframe);
        BMean[scale]+=BElement; 
        BSquared+=BElement*BElement;    
    }
  
    BMean[scale]/=endFrame-startFrame+1; 
    BSigma[scale]=std::sqrt((BSquared/(endFrame-startFrame+1)-BMean[scale]*BMean[scale])); 
};


struct BIntervalDeleter {        
    void operator()(BInterval*& BInt){ // important to take pointer by reference!
        delete BInt;
        BInt = NULL;
    }
};

struct BBlockDeleter {        
    void operator()(BBlock *& BBl){ // important to take pointer by reference!
        BIntervalDeleter myBIntervalDeleter;
        for_each(BBl->begin(),BBl->end(),myBIntervalDeleter);
        delete BBl;
        BBl=NULL;
    }
};


void  textureCalculator::deleteBBlocks(BBlockVector * BBV){
    BBlockDeleter myBBlockDeleter;
    for_each(BBV->begin(),BBV->end(),myBBlockDeleter);
    delete BBV;
    
    
}

void  textureCalculator::cleanupBBlocks(){
    BBlockVector * BBV2 = new  BBlockVector();
    BBlockVector::iterator BBIt;
    BBlock::iterator currentBInt;
    
    BInterval   * BInt;
    BBlock      * BBl;
    
    bool  newBBlockNeeded=false;
    
    
    BBl=new BBlock();
    
    for(BBIt=BBlocks->begin();BBIt!=BBlocks->end();BBIt++){
       
        
        for(currentBInt=(*BBIt)->begin();currentBInt!=(*BBIt)->end();currentBInt++){
            BInt=(*currentBInt);
            if(BInt->startFrame!=BInt->endFrame){
                newBBlockNeeded=true;
                BBl->push_back(BInt);
            }else{
               delete BInt;
            }
        }
        
        if(newBBlockNeeded==true){
             BBV2->push_back(BBl);
             BBl=new BBlock();
             newBBlockNeeded=false;
        }
        
        delete (*BBIt);
    }
    
    delete BBlocks;
    delete BBl;
    
    BBlocks=BBV2;
}


/* */


void  textureCalculator::makeBBlockVector(double PAxisFactor, double OrthoAxisFactor){
    BInterval   * Bint;
    BBlock      * BBl;
   
    bool runscalesValid=true;
    
    if(BBlocksAllocated) deleteBBlocks(BBlocks);
    BBlocks = new BBlockVector();
    BBlocksAllocated=true;
    
    int scale, runscale;
    thresholdCrossing  * TC[4], * TCtemp; // First in first quadrant etc.
    
    for( scale=0;scale<noofscales;scale++){   
        // Create a instance of BBl  
        BBl=new BBlock();
        for(runscale=0;runscale<noofscales;runscale++){
            Bint=new BInterval();
            Bint->scale=scale;
            Bint->runscale=runscale;
            Bint->startFrame=0;
            Bint->endFrame=0;
            BBl->push_back(Bint);
        } 
        BBlocks->push_back(BBl);
    } 
    

    for( scale=0;scale<noofscales;scale++){ //scale=0;scale<noofscales;scale++
        
        // Get vectors and move to correct quadrant
        TC[0]=new thresholdCrossing(pasCalc->thresholdsPAxis.at(scale).tc1,PAxisFactor); 
        TC[1]=new thresholdCrossing(pasCalc->thresholdsPAxis.at(scale).tc2,PAxisFactor);
        TC[2]=new thresholdCrossing(pasCalc->thresholdsOrthoAxis.at(scale).tc1, OrthoAxisFactor);
        TC[3]=new thresholdCrossing(pasCalc->thresholdsOrthoAxis.at(scale).tc2, OrthoAxisFactor);
       
        for( int dummy=0; dummy <4; dummy ++){
            if(TC[dummy]->scale_sub -scale>= 0  && TC[dummy]->frame_sub >0){
                    //swap to correct location
                    TCtemp=TC[0];
                    TC[0]=TC[dummy];
                    TC[dummy]=TCtemp;
            }
            if(TC[dummy]->scale_sub -scale> 0  && TC[dummy]->frame_sub <=0){
                    //swap to correct location
                    TCtemp=TC[1];
                    TC[1]=TC[dummy];
                    TC[dummy]=TCtemp;
            }
            if(TC[dummy]->scale_sub-scale <= 0  && TC[dummy]->frame_sub <0){
                    //swap to correct location
                    TCtemp=TC[2];
                    TC[2]=TC[dummy];
                    TC[dummy]=TCtemp;
            }
            if(TC[dummy]->scale_sub-scale < 0  && TC[dummy]->frame_sub >=0){
                    //swap to correct location
                    TCtemp=TC[3];
                    TC[3]=TC[dummy];
                    TC[dummy]=TCtemp;
            }
        }
        
         
        // .. and find the boundaries of the blocks
        runscalesValid=true;
        findBlockBoundary(scale, TC[0],TC[1], 'h',runscalesValid);
        findBlockBoundary(scale, TC[1],TC[0], 'l',runscalesValid);
        findBlockBoundary(scale, TC[1],TC[2], 'l',runscalesValid);
        findBlockBoundary(scale, TC[2],TC[1], 'l',runscalesValid);
        findBlockBoundary(scale, TC[2],TC[3], 'l',runscalesValid);
        findBlockBoundary(scale, TC[3],TC[2], 'h',runscalesValid);
        findBlockBoundary(scale, TC[3],TC[0], 'h',runscalesValid);
        findBlockBoundary(scale, TC[0],TC[3], 'h',runscalesValid);
        
        if(!runscalesValid){
            resetBlockBoundary(scale);
        } 
        
        for( int dummy=0; dummy <4; dummy ++){
                    TCtemp=TC[dummy];
                    delete TCtemp;
        }
        
    }
    
    cleanupBBlocks();
  

}
/* */
void  textureCalculator::findBlockBoundary(int scale, thresholdCrossing  * tcBase, thresholdCrossing  * tcSlope , char boundaryType, bool &runscalesValid){
    BInterval   * Bint;
    BBlock  *    BBl=BBlocks->at(scale);
    double c,boundaryFrameRaw;
    int increment;
    int runscale;
    
    if(tcBase->status != thresholdCrossing::found || tcSlope->status != thresholdCrossing::found || runscalesValid==false){
        runscalesValid=false;
        return;
    }
    
    double dscale=tcSlope->scale_sub-scale;
    if( dscale !=0 ){
        if(dscale > 0){ increment=1; }else{ increment=-1;}
        
        for(runscale=tcBase->scale_sub,c=0; c < 1 && runscalesValid;runscale+=increment){ //runscale < noofscales && runscale >=0 &&
            c=(runscale-tcBase->scale_sub)/(dscale);
            
            boundaryFrameRaw=tcBase->frame_sub+c*tcSlope->frame_sub;
            if(0 <= runscale && runscale < noofscales){
                Bint=BBl->at(runscale);
                if(boundaryType=='h'){
                   Bint->endFrame= thresholdCrossing::iceil(boundaryFrameRaw);
                }else{
                   Bint->startFrame=thresholdCrossing::ifloor(boundaryFrameRaw);
                }
            }else{
                runscalesValid=false;
            }
            
        }
    }
    //At zero slope the boundary points are included in the other lines
};

/* */
void  textureCalculator::resetBlockBoundary(int scale){
    BBlock  *    BBl=BBlocks->at(scale);
    BBlock::iterator Bint2;
    BInterval   * Bint;
    for(Bint2=BBl->begin();Bint2!=BBl->end();Bint2++){
         Bint=(*Bint2);
         Bint->startFrame=0;
         Bint->endFrame=0;
    }
};


void  textureCalculator::getTexture(double *B ){
    if(isInitialized){
        std::memcpy(B,BArrayRaw,sizeof(double)*noofscales*noofframes);
    }
};


void  textureCalculator::getTextureStats(double *Bm, double *Bs,\
                        int *_areaSizes, int *contextAreas,\
                        int * frameoffsets, int * scaleoffsets){ 
    BBlock::iterator currentBInterval;
    BBlockVector::iterator contextArea;
    
    for(int i=0; i<3*noofscales*noofscales; i++) contextAreas[i]=0;
    
    std::memcpy(_areaSizes,areaSize,sizeof(int)*noofscales );
    
    frameoffsets[0]=myMargins.firstframe_offset;
    frameoffsets[1]=myMargins.lastframe_offset;
    scaleoffsets[0]=myMargins.firstscale_offset;
    scaleoffsets[1]=myMargins.lastscale_offset;
    
    for ( contextArea = BBlocks->begin() ; contextArea < BBlocks->end() ; contextArea++ ){
        for(currentBInterval=(*contextArea)->begin();currentBInterval < (*contextArea)->end(); currentBInterval++){
            contextAreas[(*currentBInterval)->scale*3*noofscales+(*currentBInterval)->runscale]  =(*currentBInterval)->startFrame;
            contextAreas[(*currentBInterval)->scale*3*noofscales+(*currentBInterval)->runscale+1*noofscales]=(*currentBInterval)->endFrame;
            contextAreas[(*currentBInterval)->scale*3*noofscales+(*currentBInterval)->runscale+2*noofscales]=(*currentBInterval)->runscale;
        }
    }
    
   if(normalizeTexture){
        std::memcpy(Bm, BMean ,sizeof(double)*noofscales );
        std::memcpy(Bs, BSigma,sizeof(double)*noofscales );
    }
};

void  textureCalculator::setMargins(_margin InMargin){
    BBlockVector::iterator contextArea;
    BBlock::iterator currentBInterval;
    
    marginCalculator * myMarginCalculator;
    myMarginCalculator = new marginCalculator(noofscales);
    
    int low_scale_horizon;
    int high_scale_horizon;
    int low_frame_horizon;
    int high_frame_horizon;

    int startFrame, endFrame;
    int scale, runscale;

    for(scale=0;scale<noofscales;scale++){
        areaSize[scale]=0;
    }
    
    for ( contextArea = BBlocks->begin() ; contextArea != BBlocks->end() ; contextArea++ ){       
        low_scale_horizon=0;
        high_scale_horizon=0;
        low_frame_horizon=0;
        high_frame_horizon=0;
        
        for(currentBInterval=(*contextArea)->begin();currentBInterval != (*contextArea)->end(); currentBInterval++){    
            startFrame=(*currentBInterval)->startFrame;
            endFrame=(*currentBInterval)->endFrame;
            areaSize[(*currentBInterval)->scale]+= endFrame-startFrame+1;
          
            low_frame_horizon =std::min(low_frame_horizon, startFrame); 
            high_frame_horizon=std::max(high_frame_horizon, endFrame);
            
            scale=(*currentBInterval)->scale;
            runscale=(*currentBInterval)->runscale;
            low_scale_horizon=std::min(low_scale_horizon,runscale-scale);
            high_scale_horizon=std::max(high_scale_horizon,runscale-scale);
        }
        
        low_scale_horizon = std::abs(low_scale_horizon);
        high_scale_horizon= std::abs(high_scale_horizon);
        low_frame_horizon = std::abs(low_frame_horizon);
        high_frame_horizon= std::abs(high_frame_horizon);
        
        myMarginCalculator->setRegionDescriptor(scale,\
                    low_scale_horizon,high_scale_horizon,\
                    low_frame_horizon,high_frame_horizon);
    }  
   
    myMargins= myMarginCalculator->calcMargins(InMargin);
    delete myMarginCalculator;
};

struct textureCalculatorDeleter {        
    void operator()(std::pair<const char, textureCalculator * > & p){ 
        delete p.second;
        p.second = NULL;
    }
};


void textureCalculator::textureCalculatorMapCleanup(textureCalculatorMap & texMap){ 
        textureCalculatorDeleter myTextureCalculatorDeleter;
        for_each(texMap.begin(),texMap.end(),myTextureCalculatorDeleter);
};
