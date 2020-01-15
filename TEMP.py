import os
import sys
import time
file_dir = os.path.dirname(__file__)
sys.path.append(file_dir)
from BASE import *

tempScale='f'

tempt=time.time()
tempTime = [[tempt for x in range(8)] for y in range(8)]
tempLast = [[0 for x in range(8)] for y in range(8)]
TEMPTHROTTLE=1.0

def getTEMP(addr,chan,scale=None):
    global tempScale
    VerifyADDR(addr)	
    assert ((chan>=1) and (chan<=8)),"channel number out of range. Must be between 1 and 8"    
    chan = chan-1
    if scale is None:
        scal=tempScale
    else:
        scal=scale.lower()
        assert ((scal=='c') or (scal=='f') or (scal=='k')), "Temperature scale must be 'c', 'f', or 'k'."
    if ((time.time()-tempTime[addr][chan]) >= TEMPTHROTTLE):
        tempTime[addr][chan]=time.time()
        resp=ppCMD(addr,0x71,chan,0,2)

    #resp=ppCMD(addr,0x71,chan-1,0,2)   #get data
    
        Temp=resp[0]*256+resp[1]
        if (Temp>0x8000):
            Temp = Temp^0xFFFF
            Temp = -(Temp+1)
        Temp = round((Temp/16.0),4)
        tempLast[addr][chan]=Temp       #save last temp read in Celcius units
    Temp=tempLast[addr][chan]
    if (scal=='k'):
        Temp = Temp + 273
    if (scal=='f'):
        Temp = round((Temp*1.8+32.2),4)
    #return Temp
    return Temp
    
def setSCALE(scale):
    global tempScale
    scal=scale.lower()
    assert ((scal=='c') or (scal=='f') or (scal=='k')), "Temperature scale must be 'c', 'f', or 'k'."
    tempScale=scal
    
def getSCALE():
    global tempScale
    return tempScale