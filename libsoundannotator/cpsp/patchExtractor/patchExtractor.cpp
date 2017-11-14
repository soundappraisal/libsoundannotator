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
// Adapted for C++; Ronald van Elburg 
// 
// Includes original code for labelling algoritm provided by Arnold Meijster
//
// Background information:
// A. Meijster: Efficient Sequential and Parallel Algorithms for Morphological Image Processing 
//             Phd. Thesis, University of Groningen, the Netherlands, 2004.
//

#include "patchExtractor.h"
#include <assert.h>

#define inDomain(i,j) ((0<=(i)) && (0<=(j)) && ((i)<noofRows) && ((j)<noofCols))

patchExtractor::patchExtractor(){
    ppTSPatchedSet=false;
    noPatches=0;
    textureType=new int[1];
    simpleDescriptorsAllocated=false;
    
    inPatchMeansSet=false;
}

patchExtractor::~patchExtractor(){
    clearSimplePatchDescriptors();  
    clearInPatchMeans();
    delete [] textureType;

    if(ppTSPatchedSet)
        delete[] ppTSPatched;
}

// Start labelling algorithm
int patchExtractor::FindRoot (int k, int *par) {
  int h, r;
  r = k;
  while (par[r]!=r) r=par[r];
  while (k!=r) {
    h = par[k];
    par[k] = r;
    k = h;
  }
  return r;
}

int patchExtractor::Link (int p, int q, int *par) {
  int rp, rq;
  rp = FindRoot (p, par);
  rq = FindRoot (q, par);
  if (rp<rq) {
    par[rq] = rp;
    return rp;
  }
  par[rp] = rq;
  return rq;
}

// patches should be matrix of the same size as textures, to which it is allowed to write. 
int patchExtractor::setTimeScaleData(int noofRows, int noofCols, int *textures, int *patches) {
    patchExtractor::noofCols=noofCols;
    patchExtractor::noofRows=noofRows;

    
    // Clean up memory structures associated with old time-scale data
    clearSimplePatchDescriptors();  
    clearInPatchMeans();
    
    // Copy new time scale data to output and create supporting
    // internal variable int **ppTSPatched which provides access 
    // to the same output data
    copyTimeScaleData( textures,  patches);
    
    // Find Patches in the time-scale data and replace data in patches
    // (or equivalently ppTSPatched) with connected component number.
    noPatches=ConnectedComponentLabeling(noofCols, noofRows, ppTSPatched);
    
    return noPatches;
}

// patches should be matrix of the same size as textures, to which it is allowed to write. 
void patchExtractor::copyTimeScaleData(int *textures, int *patches) {
    int noofCols = patchExtractor::noofCols;
    int noofRows = patchExtractor::noofRows;
    
    if(ppTSPatchedSet){
        delete[] ppTSPatched;
        ppTSPatchedSet=false;
    }
    
    ppTSPatched=new int *[noofRows]; 
    ppTSPatchedSet=true;
    
    ppTSPatched[0]= patches;
    for (int i=1; i<noofRows; ++i) {
        ppTSPatched[i] = &ppTSPatched[i-1][noofCols];
    }

    int k=0;                            
    for (int j=0;j<noofRows;++j) {
        for (int i=0;i<noofCols;++i) {
           ppTSPatched[j][i]=textures[k]; 
           k++;
        }
    }
}



int patchExtractor::ConnectedComponentLabeling(int noofCols, int noofRows, int **im) {
    int i, j, k;
    int *par;
    par = new int [noofCols*noofRows];
    
    /* pass 1 */
    k=0;
    for (i=0; i<noofRows; ++i) {
        for (j=0; j<noofCols; ++j,++k) {
            par[k] = k; 
            if (inDomain(i,j-1) && (im[i][j-1] == im[i][j]))
                Link(par[k], par[k-1], par);
            if (inDomain(i-1,j) && (im[i-1][j] == im[i][j]))
                Link(par[k], par[k-noofCols], par);
        }
    }
    /* pass 2 (resolving) */
    noPatches = 0;
    for (k=0; k<noofCols*noofRows; ++k){
        if (par[k] == k)
          par[k] = noPatches++;
        else
          par[k] = par[par[k]];
    }
    
    /* Copy calculated labels to provided timescale matrix (im),
    and create an array (textureType) containing all timescale values found
    in the input*/
    k = 0;
    delete[] textureType;
    textureType = new int[noPatches];
    for (i=0; i<noofRows; ++i){
        for (j=0; j<noofCols; ++j, ++k){
            textureType[par[k]]=im[i][j];
            im[i][j] = par[k];
        }
    }
    delete[] par;
    /* return number of labels */
    return noPatches;
}

int patchExtractor::getMasks(int patchNo, int noRows, int noCols,  int *masks){

    if(!ppTSPatchedSet || patchExtractor::noofRows!=noRows || patchExtractor::noofCols!=noCols || patchNo >= noPatches || patchNo <0){
        return -1;
    };

    for (int i=0; i<noofCols; ++i){
        for (int j=0; j<noofRows; ++j){
            if(patchNo==ppTSPatched[j][i]){
                masks[i+j*noofCols]=1;
            }
        }
    }
    
    return 1;
}



/* 
    Calculate simple patch descriptors.
        lowerCol[component]: lowest column index at which component is present 
        upperCol[component]: highest column index at which component is present
        lowerRow[component]: lowest row index at which component is present 
        upperRow[component]: highest row index at which component is present 
        fullcount[component]: total number of timescale pixels at which component is present
        InRowCounts[currentPatch]: pointer to array with length noofRows containing for each 
                                    row the number of colums at which the patch is present
        InColCounts[currentPatch]: pointer to array with length noofCols containing for each 
                                    column the number of rows at which the patch is present
        
    During connected component calculation we also stored the textureType for each component in 
        textureType[component]
*/

int patchExtractor::calcSimplePatchDescriptors() {
    // Allocate arrays for storing simple patch descriptors:    
    lowerCol =   new int[noPatches];
    upperCol =   new int[noPatches];
    lowerRow =   new int[noPatches];
    upperRow =   new int[noPatches];
    fullCount =  new int[noPatches];
    //  ... and array with pointers to vectors with counts: 
    InRowCounts= new int *[noPatches];
    InColCounts= new int *[noPatches];
    // ... and flag that we did:
    simpleDescriptorsAllocated=true;
    
    // Initialize arrays and pointers to vectors with counts:
    for (int i=0;i<noPatches;++i){
        lowerCol[i]=noofCols+1;
        upperCol[i]=-1;
        lowerRow[i]=noofRows+1;
        upperRow[i]=-1;
        fullCount[i]=0;
        InRowCounts[i]=new int [noofRows];
        InColCounts[i]=new int [noofCols];
        for (int j=0; j<noofCols; ++j){
            InColCounts[i][j]=0;
        }
        for (int j=0; j<noofRows; ++j){
            InRowCounts[i][j]=0;
        }
        
    }
     
    // Now process the whole patch matrix to update 
    // simple patch descriptors.
    int currentPatch;   
    for (int i=0; i<noofCols; ++i){
        for (int j=0; j<noofRows; ++j){
            currentPatch= ppTSPatched[j][i];   // Row major only         
            if( lowerCol[currentPatch] > i ) lowerCol[currentPatch]  = i;
            if( upperCol[currentPatch] < i ) upperCol[currentPatch]  = i;
            if( lowerRow[currentPatch] > j ) lowerRow[currentPatch]  = j;
            if( upperRow[currentPatch] < j ) upperRow[currentPatch]  = j;
            InRowCounts[currentPatch][j]++;
            InColCounts[currentPatch][i]++;
            fullCount[currentPatch]++;
        }
    }
    
    return 1;
}


void patchExtractor::clearSimplePatchDescriptors(){
    if(simpleDescriptorsAllocated==true){
        delete [] lowerCol;
        delete [] upperCol;
        delete [] lowerRow;
        delete [] upperRow;
        delete [] fullCount;
        for (int i=0;i<noPatches;++i){
            delete [] InRowCounts[i];
            delete [] InColCounts[i];
        }
        delete [] InRowCounts;
        delete [] InColCounts;
        simpleDescriptorsAllocated=false;
    }   
}

int patchExtractor::getSimplePatchDescriptors(int noRows,  int noCols, int * pPatchDescriptors){
    int k=0;
    
    
    assert(noCols==noPatches);
    assert(noRows==6);
    calcSimplePatchDescriptors();
    
    for (int i=0;i<noPatches;++i){
        pPatchDescriptors[k]=textureType[i];k++;
    }
    
    for (int i=0;i<noPatches;++i){
        pPatchDescriptors[k]=lowerCol[i];k++;
    }
    
    for (int i=0;i<noPatches;++i){
        pPatchDescriptors[k]=upperCol[i];k++;
    }
    
    for (int i=0;i<noPatches;++i){
        pPatchDescriptors[k]=lowerRow[i];k++;
    }
    
    for (int i=0;i<noPatches;++i){
        pPatchDescriptors[k]=upperRow[i];k++;   
    }
    
    for (int i=0;i<noPatches;++i){
        pPatchDescriptors[k]=fullCount[i];k++;  
    }
    
    return 1;
    
}


void patchExtractor::getInColCount(int patchNo, int * ColCountVector){
    int i,j;
    j=0;
    for(i=lowerCol[patchNo];i<=upperCol[patchNo];i++){
        ColCountVector[j]=InColCounts[patchNo][i];
        j++;
    }
}

int patchExtractor::getColsInPatch(int patchNo){
    return upperCol[patchNo]-lowerCol[patchNo]+1;
}

void patchExtractor::getInRowCount(int patchNo, int * RowCountVector){      
    int i,j;
    j=0;
    for(i=lowerRow[patchNo];i<=upperRow[patchNo];i++){
        RowCountVector[j]=InRowCounts[patchNo][i];
        j++;
    }
}

int patchExtractor::getRowsInPatch(int patchNo){
    return upperRow[patchNo]-lowerRow[patchNo]+1;
}



// TF_Observable should be a matrix of the same size as the timescale representation used to calculate the patches.
int patchExtractor::calcInPatchMeans(int noRows, int noCols, double * TF_Observable) {
    int i,j;
    int patchNo;
    double ** pTF_Observable;

    if(!ppTSPatchedSet ||patchExtractor::noofRows!=noRows || patchExtractor::noofCols!=noCols || !simpleDescriptorsAllocated){
        return -1;
    }
    
    // Build 2D matrix 
    pTF_Observable=new double *[noRows]; 
    pTF_Observable[0]= TF_Observable;
    for (i=1; i<noRows; ++i) {
        pTF_Observable[i] = &pTF_Observable[i-1][noCols];
    }
    
    clearInPatchMeans();
    // Allocate and initialize memory
    InRowDist=new double *[noPatches];
    InColDist=new double *[noPatches];
    for (patchNo=0;patchNo<noPatches;++patchNo){
        InRowDist[patchNo]=new double [noRows];
        InColDist[patchNo]=new double [noCols];
        for (j=0; j<noCols; ++j){
            InColDist[patchNo][j]=0;
        }
        for (j=0; j<noRows; ++j){
            InRowDist[patchNo][j]=0;
        }
        
    }
    
    inPatchMeansSet=true; //Here all the necessary memory is allocated
    
   
    // Calculate total of observable in column or row   
    for (j=0; j<noRows; ++j){
        for (i=0; i<noCols; ++i){
            patchNo=ppTSPatched[j][i];
            InColDist[patchNo][i]+=pTF_Observable[j][i];
            InRowDist[patchNo][j]+=pTF_Observable[j][i];
        }
    }
   
    for (patchNo=0;patchNo<noPatches;++patchNo){
        for (j=0; j<noCols; ++j){
            if(InColCounts[patchNo][j]>0) InColDist[patchNo][j]/=InColCounts[patchNo][j];
        }
        for (j=0; j<noRows; ++j){
            if(InRowCounts[patchNo][j]>0) InRowDist[patchNo][j]/=InRowCounts[patchNo][j];
        }
    }
        
    delete[] pTF_Observable;
    return noPatches;
}

void patchExtractor::clearInPatchMeans(){
    if(inPatchMeansSet==true){
        for (int patchNo=0;patchNo<noPatches;++patchNo){
            delete[] InRowDist[patchNo];
            delete[] InColDist[patchNo];
        }
        delete [] InRowDist;
        delete [] InColDist;
        inPatchMeansSet=false;
    }
}

void patchExtractor::getInColDist(int componentNo, double * ColDistVector){
	int i,j;
	j=0;
	for(i=lowerCol[componentNo];i<=upperCol[componentNo];i++){
		ColDistVector[j]=InColDist[componentNo][i];
		j++;
	}
}

void patchExtractor::getInRowDist(int componentNo, double * RowDistVector){	
	int i,j;
	j=0;
	for(i=lowerRow[componentNo];i<=upperRow[componentNo];i++){
		RowDistVector[j]=InRowDist[componentNo][i];
		j++;
	}
}




int patchExtractor::calcJoinMatrix(int noRows, int * texturesBefore, int * texturesAfter, int * patchNumbersBefore , int * patchNumbersAfter, int * joinMatrix ){
    int i,j;
    int  validPatchCount;
    int  lastvalidLink;
//     int lastvalidJoin;
    bool bInsert;
    int *patchNoList, **links;
    patchNoList =new int[2*noRows];
    links = new int* [noRows];
    for(i=0;i< noRows;i++)
        links[i]=new int[2];
//     
// 	// Create unsorted list in which each patchnumber only appears once.
	for(i=0;i<noRows;i++){
		patchNoList[i]=patchNumbersBefore[i];
		patchNoList[i+noRows]=patchNumbersAfter[i];
	}
    validPatchCount=1;
    
    
    // Go through timescale points at the seam  and check whether the patches they belong to are in the 
    // valid patch list, if not add them to the valid patch list.
    for(i=1;i<2*noRows;i++){
        if(patchNoList[i-1]!=patchNoList[i]){
            bInsert=true;
            
            // Some patches can for example have holes at the boundary,
            // after a change we should therefore check whether we didn't 
            // see the patch before.
            for(j=0;j<validPatchCount && bInsert;j++){
                if(patchNoList[i]==patchNoList[j]){ bInsert=false;}
            }
            
            // Unseen patches are moved to the end of the list of patches
            // seen, this is done in place.
            if(bInsert==true){                
                patchNoList[validPatchCount]=patchNoList[i];
                validPatchCount++;
            }
        }
    }
    
    
    // Find patches that need to be joined and add them to a list of links.
    // Patches before the seam should be joined with patches after if the
    // texture value on both sides of the seam is equal. 
    lastvalidLink=-1;
    i=0;
    while(i<noRows){
        if (texturesBefore[i]==texturesAfter[i]){
            bInsert=true;
            
            // Check if patches were linked already, no need to provide links twice ...
            // for(j=0;j<=lastvalidLink && bInsert;j++){
            //     if(links[j][0]==patchNumbersBefore[i] && links[j][1]==patchNumbersAfter[i]){ bInsert=false;}
            // }
            // The code above commented out because it in all likelihood gives very small performance gains
            
            // ... if not add them to the list of links
            if(bInsert==true){
               lastvalidLink++;
               links[lastvalidLink][0]=patchNumbersBefore[i];
               links[lastvalidLink][1]=patchNumbersAfter[i];
            }
            
            i++;
            // If patchNumbers on both sides of the seam do not change jump to  next row immediately.
            while( i<noRows && patchNumbersBefore[i-1]==patchNumbersBefore[i] && patchNumbersAfter[i-1]==patchNumbersAfter[i]){i++;}
        }else{
            i++;
        }
    }
    
    // Copy patchnumbers existing at the seam to the join matrix
    for(i=0;i<validPatchCount;i++){
        joinMatrix[2*i]=patchNoList[i];
        joinMatrix[2*i+1]=patchNoList[i];
    }
    
    
   // Use links to replace patchnumbers in join matrix 
    for(i=0;i<=lastvalidLink;i++){
       JoinLink(links[i][0],links[i][1],validPatchCount, joinMatrix);
    }
    
    // Cleanup
    delete[] patchNoList;
    
    for(i=0;i< noRows;i++)
        delete[] links[i];
    delete[] links;
    
    return validPatchCount;
}

// At the start of the join process patch numbers before the seam should 
// be lower than after.
void patchExtractor::JoinLink (int lowPatch, int highPatch, int validPatchCount,int *joinMatrix) {
    int i,j;

    // Find entries in join matrix to which we need to apply the link.
    for(i=0;i<validPatchCount;i++){
        if(highPatch==joinMatrix[2*i]){ 
            // We found the high patch. 
            
            if(lowPatch > joinMatrix[2*i+1]){
                // If the lowpatch happens to be 
                // higher than the replacement value of the high patch, i.e. the 
                // high patch appeared in an earlier link, we set the replacement 
                // value of the low patch to the replacement value of the high patch.
                for(j=0;j<validPatchCount;j++){
                    if(lowPatch==joinMatrix[2*j]){
                        joinMatrix[2*j+1]=joinMatrix[2*i+1];
                        j=validPatchCount; 
                    }
                }
            }else{
                // If the low patch happens to be lower than the 
                // replacement value of the high patch we set all occurences of 
                // the high patch replacement value to low patch.
                for(j=0;j<validPatchCount;j++){
                    if(joinMatrix[2*i+1]==joinMatrix[2*j+1]){
                        joinMatrix[2*j+1]=lowPatch;
                    }
                }
            }

            i=validPatchCount;
        }    
    }
}
