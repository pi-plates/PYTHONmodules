import os
import sys
file_dir = os.path.dirname(__file__)
sys.path.append(file_dir)
from BASE import *

#==============================================================================#	
# SERVO Functions	                                                           #
#==============================================================================# 

SERVOlow=0.6
SERVOhigh=2.35

def setSERVO(addr,servo,angle):
    global SERVOlow
    global SERVOhigh
    VerifyADDR(addr)
    assert ((angle>=0) and (angle<=180)),"Angle value out of range. Must be between 0 and 180"
    servo -= 1
    #clockDec=1e-3*(1.0+angle/180.0)
    clockDec=1e-3*(SERVOlow+(SERVOhigh-SERVOlow)*(180-angle)/180.0)
    clockDec=int(clockDec*49e6/12.0)
    clockStart=2**16-clockDec
    hbyte=clockStart>>8
    lbyte=clockStart & 0xFF
    #print clockStart, hbyte, lbyte 
    ppCMD(addr,0x50+servo,hbyte,lbyte,0)
    
def setSERVO2(addr,servo,pw):
    VerifyADDR(addr)
    assert ((servo>=1) and (servo<=8)),"Servo number out of range. Must be between 1 and 8"
    if (pw>2.45):
        pw=2.45
    if (pw<0.5):
        pw=0.5
    servo -= 1
    clockDec=pw*1e-3
    clockDec=int(clockDec*49e6/12.0)
    clockStart=2**16-clockDec
    hbyte=clockStart>>8
    lbyte=clockStart & 0xFF
    #print clockStart, hbyte, lbyte 
    ppCMD(addr,0x50+servo,hbyte,lbyte,0)

def setSERVOlow(addr,value):
    global SERVOlow
    if (value>2.45):
        value=2.45
    if (value<0.5):
        value=0.5
    SERVOlow=value
    
def setSERVOhigh(addr,value):
    global SERVOhigh
    if (value>2.45):
        value=2.45
    if (value<0.5):
        value=0.5
    SERVOhigh=value    
    