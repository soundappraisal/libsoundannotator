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
#ifndef PATCHEXTRACTOR_H
#define PATCHEXTRACTOR_H

#include "framescaleArray.h"

class patchExtractor {
    public:
        
        patchExtractor();
        ~patchExtractor();
        int setTimeScaleData(int noofRows,int noofCols, int *textures, int *patches); // M stands for Matlab, in anticipation of P for Python
        void copyTimeScaleData(int *textures, int *patches);
        
        int getSimplePatchDescriptors(int noofRows, int noofCols, int * pPatchDescriptors);
        
        int getNoOfPatches(){return noPatches;};
        int getNoOfCols(){return noofCols;};
        int getNoOfRows(){return noofRows;};
        void getInColCount(int componentNo, int * ColCountVector);
        int getColsInPatch(int patchNo);
        void getInRowCount(int componentNo, int * RowCountVector);
        int getRowsInPatch(int patchNo);
        int getMasks(int patchNo, int noofRows, int noofCols, int *masks);   
        int calcInPatchMeans(int noofRows, int noofCols, double * TF_Observable);
        void getInColDist(int componentNo, double * ColDistVector);
        void getInRowDist(int componentNo, double * RowDistVector);
        int calcJoinMatrix(int noofContiguous, int * TexturesBefore, int * texturesAfter, int * PatchNumbersBefore , int * PatchNumbersAfter, int * JoinMatrix );
        bool simpleDescriptorsAllocated;
        
    private:
        int FindRoot (int k, int *par);
        int Link (int p, int q, int *par);
        int ConnectedComponentLabeling(int noofContiguous, int noofMajors, int **im); 
        int calcSimplePatchDescriptors(); 
        void clearSimplePatchDescriptors(); 
        int ** ppTSPatched;
        bool ppTSPatchedSet;
        int noofCols, noofRows;
        int noPatches;
        int * textureType, *lowerCol, *upperCol, *lowerRow, * upperRow , *fullCount;

        int ** InRowCounts, **InColCounts;
        double ** InRowDist, **InColDist;
        bool inPatchMeansSet;
        void clearInPatchMeans();
        bool isPatchInLinks(int patch, int lastvalidLink,int ** links);
        void JoinLink (int lowPatch, int highPatch, int lastvalidPatchNo,int *joinMatrix) ;
};
#endif
