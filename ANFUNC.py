import os
import sys
import time
import subprocess

file_dir = os.path.dirname(__file__)
sys.path.append(file_dir)

command = ["cat", "/proc/cpuinfo"]
output = subprocess.check_output(command)
for line in output.decode().splitlines():
    if "Model" in line:
        model = line.split(":")[1].strip()
        break    
#print(model)
if model.find("Raspberry Pi 5") != -1:
    from BASE5 import * 
else:
    from BASE0 import *


t=time.time()
mTime = [[t for x in range(4)] for y in range(8)]
mLast = [[0 for x in range(4)] for y in range(8)]
MTHROTTLE=0.05

def getMOTION(addr,chan):
    VerifyADDR(addr)
    assert ((chan>=1) and (chan<=4)),"Motion sensor value out of range. Must have a value of 1 to 4"
    #VerifyCHAN(chan)
    chan = chan - 1
    if ((time.time()-mTime[addr][chan]) >= MTHROTTLE):
        mTime[addr][chan]=time.time()
        resp=ppCMD(addr,0x30,chan,0,2)
        val=(256*resp[0]+resp[1])
        val=(val*5.10*2.4/4095)
        if (val>=2.5):
            mLast[addr][chan]=1
        else:
            mLast[addr][chan]=0
    return mLast[addr][chan]
    
def getPOT(addr,chan,range=None):
    VerifyADDR(addr)
    assert ((chan>=1) and (chan<=4)),"Pot channel out of range. Must have a value of 1 to 4"
    MAX=5.0
    if (range != None):
        assert((range>0.0) and (range<=12.0)),"The range argument must be between 0 and 12 volts."
        MAX=range
    resp=ppCMD(addr,0x30,chan-1,0,2)
    val=(256*resp[0]+resp[1])
    val=(val*5.10*2.4/4095)
    arg=round((100*val/MAX),3)
    if (arg>100.0):
        arg=100.0
    return arg
    
    