import spidev
import time
import string
import site
import sys
import os
from gpiozero import CPUTemperature
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
    import CMD5 as CMD 
else:
    import CMD0 as CMD

#Initialize
if (sys.version_info < (3,0,0)):
    sys.stderr.write("This library only works for Python3")
    exit(1)
    
POWERbaseADDR=0

if (sys.base_prefix == sys.prefix):
    result = subprocess.run(['pip', 'show', 'Pi-Plates'], stdout=subprocess.PIPE)
    result=result.stdout.splitlines()
    result=str(result[7],'utf-8')
    k=result.find('/home')
    result=result[k:]
else:
    result=site.getsitepackages()[0]
helpPath=result+'/piplates/POWER24help.txt'
#helpPath='POWER24help.txt'       #for development only

POWERversion=2.0
# Version 1.0   -   initial release
# Version 2.0   -   Modified to support RPi5

DataGood=False
cpu = CPUTemperature()

GRN=0
RED=1

RMAX = 2000
MAXADDR=8

powerPresent = 0
powerType=24

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
# A2D Functions	     	                                              		   #
#==============================================================================#	
def getVin(addr=None):
    resp=ppCMD(0,0x30,0,0,2)
    value=(256*resp[0]+resp[1])
    value=round((value*2.4*2.5/4095),3)
    return value   

def getIin(addr=None):
    if(powerType==24):
        print ("This function is not supported by the POWERplate24")
        return
    else:
        resp=ppCMD(0,0x30,1,0,2)
        value=(256*resp[0]+resp[1])
        value=round((value*2.4*2.0/4095),3)
        return value     

def getHVin(addr=None):
    if(powerType==24):
        resp=ppCMD(0,0x30,1,0,2)
        value=(256*resp[0]+resp[1])
        value=round((value*2.4*12.4573/4095),3)
    else:
        print ("This function is only supported by the POWERplate24")
        value=0        
    return value   

def getCPUtemp(addr=None):
    return cpu.temperature

def getADC(addr,channel):
    resp=ppCMD(0,0x30,channel,0,2)
    value=(256*resp[0]+resp[1])
    return value

#==============================================================================#	
# RTC and Schedule Functions                                                   #
#==============================================================================#
def setRTC(addr,zone):
    zone=zone.lower()
    assert ((zone=='l') or (zone=='g')),"Invalid zone - must be 'l' for local or 'g' for Greenwich"
    if (zone=='l'):
        lTime=time.localtime()
    else:
        lTime=time.gmtime()
    resp=ppCMD(0,0xD1,lTime.tm_hour,0,0)
    resp=ppCMD(0,0xD0,lTime.tm_min,lTime.tm_sec,0)
    
def setWAKE(addr,hr,min,sec):
    resp=ppCMD(0,0xD3,hr,0,0)
    resp=ppCMD(0,0xD2,min,sec,0)
    
def enableWAKE(addr=None):
    resp=ppCMD(0,0xD5,1,0,0)

def disableWAKE(addr=None):
    resp=ppCMD(0,0xD5,0,0,0)

def getWAKESOURCE(addr=None):
    resp=ppCMD(0,0x57,0,0,1)
    return resp[0]
 
#===============================================================================#	
# LED Functions	                                                   		   		#
#===============================================================================#			
def setLED(addr,led):
    led=led.upper()
    assert (led=='RED' or led=='GREEN' or led=='GRN' or led=='YELLOW' or led=='YEL' or led=='OFF'),"Invalid LED argument"
    resp=ppCMD(0,0x61,0,0,0) 
    resp=ppCMD(0,0x61,1,0,0)
    if (led=='RED' or led=='RD'):
        resp=ppCMD(0,0x60,1,0,0)
    if (led=='GREEN' or led=='GRN'):
        resp=ppCMD(0,0x60,0,0,0)
    if (led=='YELLOW' or led=='YEL'):
        resp=ppCMD(0,0x60,0,0,0) 
        resp=ppCMD(0,0x60,1,0,0)        

# ledMODE command
# mode 0: auto: always off
# mode 1: auto: blink
# mode 2: auto: always on (default)
# mode 3: manual
def ledMODE(addr,mode):
    assert (mode>=0 and mode<=3),"Invalid mode value. Must be 0, 1, 2, or 3"
    resp=ppCMD(0,0x6F,mode,0,0)
  
def VerifyLED(led):
    assert (led>=0 and led<=1),"Invalid LED value. Must be 0 or 1"

#==============================================================================#	
# Switch and Fan Functions	                                                   #
#==============================================================================#   
def fanOFF(addr=None):
    resp=ppCMD(0,0xEE,0,0,0)
    
def fanON(addr=None):
    resp=ppCMD(0,0xEF,0,0,0)
    
def fanSTATE(addr=None):
    resp=ppCMD(0,0xED,0,0,1)
    return resp[0]

def getSWstate(addr=None):
    resp=ppCMD(0,0x50,0,0,1)
    return resp[0]    

def setSHUTDOWNdelay(addr,delay):
    assert (delay>=10 and delay<=240),"Invalid delay value. Must be between 10 and 240"
    resp=ppCMD(0,0x55,delay,0,0)

def enablePOWERSW(addr, bypass=None):
    if (getFWrev(addr)>=1.2):
        if (bypass==None):
            bypass=True
        else:
            assert(bypass==True or bypass==False), 'If used, bypass argument must be "True" or "False".'
    else:
        bypass=False
    if(bypass):
        bparg=1
    else:
        bparg=0   
    resp=ppCMD(0,0x53,bparg,0,0)

def disablePOWERSW(addr=None):
    resp=ppCMD(0,0x54,0,0,0)    

def powerOFF(addr=None):
    resp=ppCMD(0,0x56,0,0,0)
    
#==============================================================================#	
# POWER Status Functions - only for POWERplate24                               #
#==============================================================================# 
 
def statEnable(addr=None):	#POWERplate24 will pull down on STAT pin if an enabled event occurs
    if(powerType==24):
        resp=ppCMD(addr,0x04,0,0,0)
    else:
        print ("This function is only supported by the POWERplate24")       
	
def statDisable(addr=None):   #POWERplate24 will not assert STAT
    if(powerType==24):
        resp=ppCMD(addr,0x05,0,0,0)
    else:
        print ("This function is only supported by the POWERplate24") 
    
def getPOWchange(addr=None):	#read Power status change register in POWERplate24 - this clears stat change line and the register
    if(powerType==24):
        resp=ppCMD(addr,0x06,0,0,1)
        value=(resp[0])
    else:
        print ("This function is only supported by the POWERplate24")
        value=0
    return value 
    
def getPOWstatus(addr=None):	#read curent power status register in POWERplate24
    if(powerType==24):
        resp=ppCMD(addr,0x07,0,0,1)
        value=(resp[0])
    else:
        print ("This function is only supported by the POWERplate24")
        value=0
    return value 

def getSTATflag(addr=None):
    if(powerType==24):
        if (GPIO.input(ppINT)==1):
            value=False
        else:
            value=True
    else:
        print ("This function is only supported by the POWERplate24")
        value=0
    return value 
 
#==============================================================================#	
# LOW Level Functions	                                                       #
#==============================================================================#          
def VerifyAINchannel(ain):
    assert ((ain>=0) and (ain<=1)),"Analog input channel value out of range. Must be in the range of 0 to 1"    

def VerifyADDR(addr):
    assert (addr==0),"POWERplate address out of range"
    addr_str=str(addr)
    assert (powerPresent==1),"No POWERplate found"
    
def ppCMD(addr,cmd,param1,param2,bytes2return):
    return CMD.ppCMD2(addr,cmd,param1,param2,bytes2return)
 
def getID(addr):
    addr=0
    return CMD.getID2(addr)

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
    return POWER24version
    
def readFLASH(addr,flashadddr):
    global POWERbaseADDR
    p1=flashadddr>>8
    p2=flashadddr&0xFF
    resp=ppCMD(0,0xFE,p1,p2,1)
    return resp[0]


def getADDR():
    global POWERbaseADDR
    resp=ppCMD(0,0x00,0,0,1)
    #print resp, DataGood;
    if (CMD.DataGood):
        return resp[0]        
    else:
        return 8
    
def quietPoll():   
    global powerPresent, powerType
    rtn = getADDR()
    if (rtn==0):           
        powerPresent=1
        id=getID(0)
        if (id.find('24')>0):
            powerType=24      
        setRTC(0,'l')       

def RESET(addr):
    VerifyADDR(addr)
    resp=ppCMD(addr,0x0F,0,0,0)    
    time.sleep(1)
    quietPoll()

quietPoll()          