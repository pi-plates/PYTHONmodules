import os
import sys
import time
file_dir = os.path.dirname(__file__)
sys.path.append(file_dir)
from BASE import *


t=time.time()
bTime = [[t for x in range(8)] for y in range(8)]
bLast = [[0 for x in range(8)] for y in range(8)]
BTHROTTLE=0.05

def getBUTTON(addr,chan):
    VerifyADDR(addr)
    VerifyCHAN(chan)
    chan = chan-1
    if ((time.time()-bTime[addr][chan]) >= BTHROTTLE):
        bTime[addr][chan]=time.time()
        res=ppCMD(addr,0x2A,chan,0,1)
        bLast[addr][chan]=res[0]
    return bLast[addr][chan]
    
        
    
