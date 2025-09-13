import spidev
import time
import site
import sys
import os
import threading
from six.moves import input as raw_input
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
    sys.stderr.write("This library requires Python3")
    exit(1)
    
DIGIbaseADDR=0x58
    
if (sys.base_prefix == sys.prefix):
    result = subprocess.run(['pip', 'show', 'Pi-Plates'], stdout=subprocess.PIPE)
    result=result.stdout.splitlines()
    result=str(result[7],'utf-8')
    k=result.find('/home')
    result=result[k:]
else:
    result=site.getsitepackages()[0]
helpPath=result+'/piplates/DIGIhelp.txt' 
#helpPath='DIGIhelp.txt'       #for development only

DIGIversion=2.1
# Version 1.0   -   initial release
# Version 2.0   -   Modified to support RPi5
# Version 2.1   -   Fixed bug in getFREQ

RMAX = 2000
MAXADDR=8
digisPresent = list(range(8))
DataGood=False
lock = threading.Lock()
lock.acquire()

#==============================================================================#
# HELP Functions                                                               #
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
    return DIGIversion

#===============================================================================#   
# Digital Input Functions                                                       #
#===============================================================================#
def getDINbit(addr,bit):
    VerifyADDR(addr)
    VerifyDINchannel(bit-1)
    resp=ppCMD(addr,0x20,bit-1,0,1)
    if resp[0] > 0:
        return 1
    else:
        return 0
        
def getDINall(addr):
    VerifyADDR(addr)
    resp=ppCMD(addr,0x25,0,0,1)
    return resp[0]

#==============================================================================#
# Event Functions                                                              #
#==============================================================================#
def enableDINevent(addr, bit, edge):  # enable DIN interrupt
    VerifyADDR(addr)
    VerifyDINchannel(bit-1)
    bit = bit-1
    if ((edge=='f') or (edge=='F')):
        resp=ppCMD(addr,0x21,bit,0,0)
    if ((edge=='r') or (edge=='R')):
        resp=ppCMD(addr,0x22,bit,0,0)
    if ((edge=='b') or (edge=='B')):
        resp=ppCMD(addr,0x23,bit,0,0)

def disableDINevent(addr,bit):    # disable DIN interrupt
    VerifyADDR(addr)
    VerifyDINchannel(bit-1)
    resp=ppCMD(addr,0x24,bit-1,0,0)    

def eventEnable(addr):    #DIGIplate will pull down on INT pin if an enabled event occurs
    VerifyADDR(addr)
    resp=ppCMD(addr,0x04,0,0,0)

def eventDisable(addr):   #DIGIplate will not assert interrupts
    VerifyADDR(addr)
    resp=ppCMD(addr,0x05,0,0,0)
    
def getEVENTS(addr):  #read INT flag register in DIGIplate - this clears interrupt line and the register
    VerifyADDR(addr)
    resp=ppCMD(addr,0x06,0,0,2)
    value=((resp[0]<<8) + resp[1])
    return value

def check4EVENTS():
    stat=CMD.getSRQ()
    return stat
    
#==============================================================================#    
# FREQ Functions                                                               #
#==============================================================================#      
def getFREQ(addr,chan):
    global DataGood
    VerifyADDR(addr)
    assert ((chan>=1) and (chan<=6)),"Frequency input channel value out of range. Must be in the range of 1 to 6"
    freq=0
    resp=ppCMD(addr,0xC0,0,chan-1,2) #get the upper 16 bits
    #print (1, DataGood, (resp[0]<<24)+(resp[1]<<16), resp[2])
    if(CMD.DataGood):
        counts=(resp[0]<<24)+(resp[1]<<16)
        resp=ppCMD(addr,0xC0,1,chan-1,2) #get the lower 16 bits
        #print (2, DataGood, (resp[0]<<8)+resp[1], resp[2])
        if (CMD.DataGood):
            counts=counts+(resp[0]<<8)+resp[1]
            if (counts>0):
                freq=1000000.0/counts
            else:
                freq=0
    return round(freq,3)

def getFREQall(addr):
    global DataGood
    VerifyADDR(addr)
    freqList=6*[0]
    for i in range(6):
        chan=i+1
        freq=0
        resp=ppCMD(addr,0xC0,0,chan-1,2) #get the upper 16 bits
        if(CMD.DataGood):
            counts=(resp[0]<<24)+(resp[1]<<16)
            resp=ppCMD(addr,0xC0,1,chan-1,2) #get the lower 16 bits
            #print (2, DataGood, (resp[0]<<8)+resp[1], resp[2])
            if (CMD.DataGood):
                counts=counts+(resp[0]<<8)+resp[1]
                if (counts>0):
                    freq=1000000.0/counts
                else:
                    freq=0
                freqList[i]=round(freq,3)
    return freqList    
    
    
#==============================================================================#    
# LED Functions                                                                #
#==============================================================================#   
def setLED(addr):
    VerifyADDR(addr)
    resp=ppCMD(addr,0x60,0,0,0)

def clrLED(addr):
    VerifyADDR(addr)
    resp=ppCMD(addr,0x61,0,0,0)

def toggleLED(addr):
    VerifyADDR(addr)
    resp=ppCMD(addr,0x62,0,0,0)
  
#==============================================================================#    
# SYSTEM Functions                                                             #
#==============================================================================#     
def getID(addr):
    global DIGIbaseADDR
    addr=addr+DIGIbaseADDR
    return CMD.getID2(addr)


def getHWrev(addr):
    global DIGIbaseADDR
    VerifyADDR(addr)
    resp=ppCMD(addr,0x02,0,0,1)
    rev = resp[0]
    whole=float(rev>>4)
    point = float(rev&0x0F)
    return whole+point/10.0  
    
def getFWrev(addr):
    global DIGIbaseADDR
    VerifyADDR(addr)
    resp=ppCMD(addr,0x03,0,0,1)
    rev = resp[0]
    whole=float(rev>>4)
    point = float(rev&0x0F)
    return whole+point/10.0

def getVersion():
    return DIGIversion
        
#==============================================================================#    
# LOW Level Functions                                                          #
#==============================================================================#          
def VerifyDINchannel(din):
    assert ((din>=0) and (din<=7)),"Digital input channel value out of range. Must be in the range of 1 to 8"
    
def VerifyADDR(addr):
    assert ((addr>=0) and (addr<MAXADDR)),"DIGIplate address out of range"
    addr_str=str(addr)
    assert (digisPresent[addr]==1),"No DIGIplate found at address "+addr_str


def ppCMD(addr,cmd,param1,param2,bytes2return):
    global DIGIbaseADDR
    return CMD.ppCMD2(addr+DIGIbaseADDR,cmd,param1,param2,bytes2return)

def setINT(addr):
    VerifyADDR(addr)
    resp=ppCMD(addr,0xF4,0,0,0)

def clrINT(addr):
    VerifyADDR(addr)
    resp=ppCMD(addr,0xF5,0,0,0)
    
def getADDR(addr):
    global DIGIbaseADDR
    #resp = []
    resp=ppCMD(addr,0x00,0,0,1)
    #print(resp)
    if (CMD.DataGood):
        return resp[0]-DIGIbaseADDR
    else:
        return 8
    
def quietPoll():   
    global digisPresent
    ppFoundCount=0
    for i in range (0,8):
        digisPresent[i]=0
        rtn = getADDR(i)
        if (rtn==i):           
            digisPresent[i]=1
            ppFoundCount += 1

def RESET(addr):
    VerifyADDR(addr)
    resp=ppCMD(addr,0x0F,0,0,0)    
    time.sleep(.10)

quietPoll()    
