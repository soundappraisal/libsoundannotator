'''
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
'''
import structureExtractor
import numpy as np
import matplotlib.pyplot as plt


myExtractor=structureExtractor.structureExtractor()


ns=7
md=24
nf=1000
myarray=np.ones([ns,nf],'double')
#myarray[:,np.random.permutation(ns)] +=1
myarray[1,:] =np.random.randn(1,nf)+2
#myarray=np.random.randn(ns,nf)

myExtractor.initialize(myarray,md,True)


#corr=np.random.randn(2*md+1,ns*ns)
corr=np.zeros((ns*ns, 2*md+1),'double')
try:
    myExtractor.get_correlations(corr,True)
except ValueError as e:
    print(e)

fig=plt.gcf()
cax=plt.imshow(corr[0:nf,0:-1], interpolation='nearest')

#cax=plt.imshow(myarray, interpolation='nearest')
colorlims=[-0.8,0.8]
plt.clim(colorlims)
plt.title("Correlations")
cbar = fig.colorbar(cax, ticks=colorlims)
#cbar.ax.set_yticklabels(['-1', '0', '1'])# vertically oriented colorbar
plt.show()



print('calc pas')
ts1=np.random.randn(ns,743)
p1=np.zeros((ns,743),order='C')
try:
    myExtractor.calc_pattern(ts1,p1,'f')
except ValueError as e:
    print(e)

#fig2=plt.gcf()
#cax=plt.imshow(p1, interpolation='nearest')
#plt.clim()
#plt.title("Correlations")
##cbar = fig.colorbar(cax, ticks=[-1, 0, 1])
##cbar.ax.set_yticklabels(['< -1', '0', '> 1'])# vertically oriented colorbar
#plt.show()

    
print('calc tract')
ts1=np.random.randn(ns,743)
p1=np.zeros((ns,743),order='C')
tr1=np.zeros((ns,743),order='C')
try:
    myExtractor.calc_tract(ts1,tr1,p1,'f')
except ValueError as e:
    print(e)

fig=plt.gcf()
cax=plt.imshow(tr1, interpolation='nearest')
plt.clim()
plt.title("Correlations")
#cbar = fig.colorbar(cax, ticks=[-1, 0, 1])
#cbar.ax.set_yticklabels(['< -1', '0', '> 1'])# vertically oriented colorbar
plt.show()

a=np.zeros((ns ),order='C')
b=np.zeros((ns ),order='C')
c=np.zeros((2*ns,8),dtype='int32',order='C')
d=np.zeros((2*ns,2),dtype='int32',order='C')
e=np.zeros((2*ns,2),order='C')

print('get_pattern_stats')
myExtractor.get_pattern_stats(a,b,c,d,e,'f')

c=np.zeros((ns ),order='C')
d=np.zeros((ns ),order='C')
e=np.zeros((ns,3*ns),dtype='int32',order='C')
print('get_tract_stats')
myExtractor.get_tract_stats(c,d,e,'f')
# Add colorbar, make sure to specify tick locations to match desired ticklabels

