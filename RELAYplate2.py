import spidev
import time
import string
import site
import sys
import os
import threading
from numbers import Number
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
from six.moves import input as raw_input

#Initialize
if (sys.version_info < (3,0,0)):
    sys.stderr.write("This library requires Python3")
    exit(1)
    
RELAY2baseADDR=0x48	
    
if (sys.base_prefix == sys.prefix):
    result = subprocess.run(['pip', 'show', 'Pi-Plates'], stdout=subprocess.PIPE)
    result=result.stdout.splitlines()
    result=str(result[7],'utf-8')
    k=result.find('/home')
    result=result[k:]
else:
    result=site.getsitepackages()[0]
helpPath=result+'/piplates/RELAY2help.txt' 
#helpPath='RELAY2help.txt'       #for development only

RP2version=2.0
# Version 1.0   -   initial release
# Version 2.0   -   Modified to support RPi5

RMAX = 2000
MAXADDR=8
relaysPresent = list(range(8))
DataGood=False
lock = threading.Lock()
lock.acquire()

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

def getSWrev():
    return RP2version


#==============================================================================#
# RELAY Functions	                                                           #
#==============================================================================#
def relayON(addr,relay):
    VerifyADDR(addr)
    VerifyRELAY(relay)
    ppCMDr(addr,0x10,relay-1,0,0)

def relayOFF(addr,relay):
    VerifyADDR(addr)
    VerifyRELAY(relay)
    ppCMDr(addr,0x11,relay-1,0,0)
    
def relayTOGGLE(addr,relay):
    VerifyADDR(addr)
    VerifyRELAY(relay)
    ppCMDr(addr,0x12,relay-1,0,0)   

def relayALL(addr,relays):
    VerifyADDR(addr)
    assert ((relays>=0) and (relays<=255)),"Argument out of range. Must be between 0 and 255"
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
    global RELAY2baseADDR
    addr=addr+RELAY2baseADDR
    return CMD.getID2(addr)

def getHWrev(addr):
    global RELAY2baseADDR
    VerifyADDR(addr)
    resp=ppCMDr(addr,0x02,0,0,1)
    rev = resp[0]
    whole=float(rev>>4)
    point = float(rev&0x0F)
    return whole+point/10.0	 
    
def getFWrev(addr):
    global RELAY2baseADDR
    VerifyADDR(addr)
    resp=ppCMDr(addr,0x03,0,0,1)
    rev = resp[0]
    whole=float(rev>>4)
    point = float(rev&0x0F)
    return whole+point/10.0

def getVersion():
    return RP2version      
        
#==============================================================================#	
# LOW Level Functions	                                                       #
#==============================================================================#          
def VerifyRELAY(relay):
    assert ((relay>=1) and (relay<=8)),"Relay number out of range. Must be between 1 and 8"

def VerifyADDR(addr):
    assert ((addr>=0) and (addr<MAXADDR)),"RELAY2plate address out of range"
    addr_str=str(addr)
    assert (relaysPresent[addr]==1),"No RELAY2plate found at address "+addr_str

def ppCMDr(addr,cmd,param1,param2,bytes2return):
    global RELAY2baseADDR
    return CMD.ppCMD2(addr+RELAY2baseADDR,cmd,param1,param2,bytes2return)

#def ppCMDr(addr,cmd,param1,param2,bytes2return,slow=None):
    
def getADDR(addr):
    global RELAY2baseADDR
    resp=ppCMDr(addr,0x00,0,0,1)
    if (CMD.DataGood):
        return resp[0]-RELAY2baseADDR
    else:
        return 8
    
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
