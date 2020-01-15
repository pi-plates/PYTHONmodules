#import spidev
import time
import string
import site
import sys
import math
from numbers import Number
import os

file_dir = os.path.dirname(__file__)
sys.path.append(file_dir)

from BASE import *
from A2D import *
from LED import *
from RELAY import *
from DIO import *
from PWM import *
from SERVO import *
from RANGE import *
from TEMP import *
from METER import *
from ANFUNC import *
from BUTTON import *

#Initialize
if (sys.version_info < (3,0,0)):
    sys.stderr.write("This library is only compatible with Python 3.")
    exit(1)  

localPath=site.getsitepackages()[0]
helpPath=localPath+'/piplates/TINKERhelp.txt'
#helpPath='TINKERhelp.txt'       #for development only
TINKERversion=1.0
#DataGood=False

dModes=['din','dout','button','pwm','range','temp','servo','rgbled','motion']
pcaRequired=[0,0,0,1,0,0,0,0,0]
chanModes=['din','din','din','din','din','din','din','din']
pcaMap=[0,1,2,3,4,5,6,6]

#RMAX = 2000

def CLOSE():
	spi.close()
	GPIO.cleanup()

def Help():
	help()

def HELP():
	help()	
	
def help():
    valid=True
    try:    
        f=open(helpPath,'r')
        while(valid):
            Count=0
            while (Count<20):
                s=f.readline()
                if (len(s)!=0):
                    print (s[:len(s)-1])
                    Count = Count + 1
                    if (Count==20):
                        Input=input('press \"Enter\" for more...')                        
                else:
                    Count=100
                    valid=False
        f.close()
    except IOError:
        print ("Can't find help file.")

#==============================================================================#	
# setMODE - configure digital channels. Uses command in 0x9X range 	           #
# Valid modes are:
#    DIN
#    DOUT
#    BUTTON
#    PWM
#    RANGE
#    TEMP
#    SERVO
#    RGBLED
#==============================================================================# 
def setMODE(addr, chan, mode):
    modeCount=9
    selMode=modeCount
    VerifyADDR(addr)
    if (mode != 'range'):
        VerifyCHAN(chan)
        chan-=1
    else:
        channelpair=chan
        assert ((channelpair==12) or (channelpair==34) or (channelpair==56) or (channelpair==78)),"Invalid channel pair argument. Valid values are 12, 34, 56, and 78"      
        chan=(channelpair>>1)//10
    mode=mode.lower()
    if(mode=='led'):
        mode='pwm'
    for i in range(modeCount):
        if (mode==dModes[i]):
            selMode=i
    assert (selMode!=9), mode+' is not a valid mode.'
    if (pcaRequired[selMode]==1):
        assert (pcaMap[chan]!=6), 'This channel can not support '+mode+' mode.'
    # if (mode=='range'):
        # chan=(chan>>1)<<1  #convert odd number channel selection for rangefinder to lower even number.
    resp=ppCMD(addr,0x90,chan,selMode,0)
    
def setDEFAULTS(addr):   #Use this function to set all the ports back to inputs 
    VerifyADDR(addr) 
    for i in range(8):
        resp=ppCMD(addr,0x90,i,0,0)
   
#==============================================================================#	
# System Functions	                                                           #
#==============================================================================#
def getFWrev(addr):
    VerifyADDR(addr)
    resp=ppCMD(addr,0x03,0,0,1)
    rev = resp[0]
    whole=float(rev>>4)
    point = float(rev&0x0F)
    return whole+point/10.0
	
def getHWrev(addr):
    VerifyADDR(addr)
    resp=ppCMD(addr,0x02,0,0,1)
    rev = resp[0]
    whole=float(rev>>4)
    point = float(rev&0x0F)
    return whole+point/10.0	

def getVersion():
    return TINKERversion   

def setINT(addr):
    VerifyADDR(addr)
    resp=ppCMD(addr,0xF4,0,0,0)

def clrINT(addr):
    VerifyADDR(addr)
    resp=ppCMD(addr,0xF5,0,0,0)

quietPoll()
