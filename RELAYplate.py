import spidev
import time
import string
import site
import sys
from numbers import Number
import RPi.GPIO as GPIO
from six.moves import input as raw_input

GPIO.setwarnings(False)

#Initialize
if (sys.version_info < (2,7,0)):
    sys.stderr.write("You need at least python 2.7.0 to use this library")
    exit(1)
    
GPIO.setmode(GPIO.BCM)
RELAYbaseADDR=24
ppFRAME = 25
ppINT = 22
GPIO.setup(ppFRAME,GPIO.OUT)
GPIO.output(ppFRAME,False)  #Initialize FRAME signal
time.sleep(.001)            #let Pi-Plate reset SPI engine if necessary
GPIO.setup(ppINT, GPIO.IN, pull_up_down=GPIO.PUD_UP)
spi = spidev.SpiDev()
spi.open(0,1)	
localPath=site.getsitepackages()[0]
helpPath=localPath+'/piplates/RELAYhelp.txt'
#helpPath='RELAYhelp.txt'       #for development only
RPversion=1.1
# Version 1.0   -   initial release
# Version 1.1 - adjusted timing on command functions to compensate for RPi SPI changes

RMAX = 2000
MAXADDR=8
relaysPresent = list(range(8))

#==============================================================================#
# HELP Functions	                                                           #
#==============================================================================#
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
                        Input=raw_input('press \"Enter\" for more...')                        
                else:
                    Count=100
                    valid=False
        f.close()
    except IOError:
        print ("Can't find help file.")

def getPMrev():
    return RPversion


#==============================================================================#
# RELAY Functions	                                                           #
#==============================================================================#
def relayON(addr,relay):
    VerifyADDR(addr)
    VerifyRELAY(relay)
    ppCMDr(addr,0x10,relay,0,0)

def relayOFF(addr,relay):
    VerifyADDR(addr)
    VerifyRELAY(relay)
    ppCMDr(addr,0x11,relay,0,0)
    
def relayTOGGLE(addr,relay):
    VerifyADDR(addr)
    VerifyRELAY(relay)
    ppCMDr(addr,0x12,relay,0,0)   

def relayALL(addr,relays):
    VerifyADDR(addr)
    assert ((relays>=0) and (relays<=127)),"Argument out of range. Must be between 0 and 127"
    ppCMDr(addr,0x13,relays,0,0)     
 
def relaySTATE(addr):
    VerifyADDR(addr)
    resp=ppCMDr(addr,0x14,0,0,1) 
    return resp[0]

#==============================================================================#	
# LED Functions	                                                               #
#==============================================================================#   
def setLED(addr):
    VerifyADDR(addr)
    resp=ppCMDr(addr,0x60,0,0,0)

def clrLED(addr):
    VerifyADDR(addr)
    resp=ppCMDr(addr,0x61,0,0,0)

def toggleLED(addr):
    VerifyADDR(addr)
    resp=ppCMDr(addr,0x62,0,0,0)
    
#==============================================================================#	
# SYSTEM Functions	                                                           #
#==============================================================================#     
def getID(addr):
    global RELAYbaseADDR
    VerifyADDR(addr)   
    addr=addr+RELAYbaseADDR
    id=""
    arg = list(range(4))
    resp = []
    arg[0]=addr;
    arg[1]=0x1;
    arg[2]=0;
    arg[3]=0;
    ppFRAME = 25
    GPIO.output(ppFRAME,True)
    null=spi.xfer(arg,300000,60)
    #null = spi.writebytes(arg)
    count=0
#    time.sleep(.01)
    while (count<20): 
        dummy=spi.xfer([00],500000,20)
        if (dummy[0] != 0):
            num = dummy[0]
            id = id + chr(num)
            count = count + 1
        else:
            count=20
    GPIO.output(ppFRAME,False)
    return id

def getHWrev(addr):
    global RELAYbaseADDR
    VerifyADDR(addr)
    resp=ppCMDr(addr,0x02,0,0,1)
    rev = resp[0]
    whole=float(rev>>4)
    point = float(rev&0x0F)
    return whole+point/10.0	 
    
def getFWrev(addr):
    global RELAYbaseADDR
    VerifyADDR(addr)
    resp=ppCMDr(addr,0x03,0,0,1)
    rev = resp[0]
    whole=float(rev>>4)
    point = float(rev&0x0F)
    return whole+point/10.0

def getVersion():
    return RPversion      
        
#==============================================================================#	
# LOW Level Functions	                                                       #
#==============================================================================#          
def VerifyRELAY(relay):
    assert ((relay>=1) and (relay<=7)),"Relay number out of range. Must be between 1 and 7"

def VerifyADDR(addr):
    assert ((addr>=0) and (addr<MAXADDR)),"RELAYplate address out of range"
    addr_str=str(addr)
    assert (relaysPresent[addr]==1),"No RELAYplate found at address "+addr_str

def ppCMDr(addr,cmd,param1,param2,bytes2return):
    global RELAYbaseADDR
    arg = list(range(4))
    resp = []
    arg[0]=addr+RELAYbaseADDR;
    arg[1]=cmd;
    arg[2]=param1;
    arg[3]=param2;
    GPIO.output(ppFRAME,True)
    null=spi.xfer(arg,300000,60)
    #null = spi.writebytes(arg)
    if bytes2return>0:
        time.sleep(.0001)
        for i in range(0,bytes2return):	
            dummy=spi.xfer([00],500000,20)
            resp.append(dummy[0])
    time.sleep(.001)
    GPIO.output(ppFRAME,False)
    time.sleep(.001)
    return resp    
    
def getADDR(addr):
    global RELAYbaseADDR
    resp = []
    resp=ppCMDr(addr,0x00,0,0,1)
    return resp[0]-RELAYbaseADDR

    
def quietPoll():   
    global relaysPresent
    ppFoundCount=0
    for i in range (0,8):
        relaysPresent[i]=0
        rtn = getADDR(i)
        if (rtn==i):           
            relaysPresent[i]=1
            ppFoundCount += 1
            #RESET(i)

def RESET(addr):
    VerifyADDR(addr)
    resp=ppCMDr(addr,0x0F,0,0,0)    
    time.sleep(.10)

quietPoll()    
