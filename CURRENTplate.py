import spidev
import time
import site
import sys
import threading
import subprocess
import os

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
    
CURRENTbaseADDR=0x50

if (sys.base_prefix == sys.prefix):
    result = subprocess.run(['pip', 'show', 'Pi-Plates'], stdout=subprocess.PIPE)
    result=result.stdout.splitlines()
    result=str(result[7],'utf-8')
    k=result.find('/home')
    result=result[k:]
else:
    result=site.getsitepackages()[0]
helpPath=result+'/piplates/CURRENThelp.txt'

#helpPath='CURRENThelp.txt'       #for development only
version=2.0
# Version 1.0   -   initial release
# Version 2.0   -   Modified to support RPi5

RMAX = 2000
MAXADDR=8
CURRENTPresent = list(range(8))
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
                        raw_input('press \"Enter\" for more...')
                else:
                    Count=100
                    valid=False
        f.close()
    except IOError:
        print ("No help file found.")

def getSWrev():
    return version

#==============================================================================#
# Current Read Functions                                                       #
#==============================================================================#
def getI(addr,channel):
    VerifyADDR(addr)
    VerifyIchannel(channel)
    resp=ppCMD(addr,0x30,channel-1,0,2)
    value=float(256*resp[0]+resp[1])
    value=round((value*24.0/65536.0),4)
    return value

def getIall(addr):
    value=list(range(8))
    VerifyADDR(addr)    
    resp=ppCMD(addr,0x31,0,0,16)
    for i in range (0,8):
        value[i]=float(256*resp[2*i]+resp[2*i+1])
        value[i]=round((value[i]*24.0/65536.0),4)
    return value 


#==============================================================================#
# Unused Precision Functions - analysis showed no clear improvement            #
#==============================================================================#
def initI(addr,channel):
    VerifyADDR(addr)
    VerifyIchannel(channel) 
    ppCMD(addr,0x32,channel-1,0,0)

def initIall(addr):
    VerifyADDR(addr)    
    ppCMD(addr,0x33,0,0,0)   
    
def pullI(addr, channel):
    VerifyADDR(addr)
    VerifyIchannel(channel) 
    resp=ppCMD(addr,0x34,channel-1,0,2)
    value=float(256*resp[0]+resp[1])
    value=round((value*24.0/65536.0),4)
    return value
    
def pullIall(addr):
    value=list(range(8))
    VerifyADDR(addr)    
    resp=ppCMD(addr,0x35,0,0,16)
    for i in range (0,8):
        value[i]=float(256*resp[2*i]+resp[2*i+1])
        value[i]=round((value[i]*24.0/65536.0),4)
    return value 
    
def setFREQ(addr,freq):
    VerifyADDR(addr)
    assert (freq==50 or freq==60), "AC line frequency argument can only be for or 60."
    ppCMD(addr,0x3F,freq,0,0)

#==============================================================================#
# LED Functions                                                                #
#==============================================================================#
def setLED(addr):
    VerifyADDR(addr)
    ppCMD(addr,0x60,0,0,0)

def clrLED(addr):
    VerifyADDR(addr)
    ppCMD(addr,0x61,0,0,0)

def toggleLED(addr):
    VerifyADDR(addr)
    ppCMD(addr,0x62,0,0,0)

#==============================================================================#    
# Interrupt Functions                                                          #
#==============================================================================#    
def intEnable(addr):    #CURRENT will pull down on SRQ pin if an enabled event occurs
    VerifyADDR(addr)
    ppCMD(addr,0x04,0,0,0)

def intDisable(addr):   #CURRENT will not assert SRQ
    VerifyADDR(addr)
    ppCMD(addr,0x05,0,0,0)
    
def getINTflags(addr):  #read SRQ flag register in CURRENT - this clears interrupt line and the register
    VerifyADDR(addr)
    resp=ppCMD(addr,0x06,0,0,1)
    value=(resp[0])
    return value

    
#==============================================================================#    
# Flash Memory Functions - used for calibration constants                      #
#==============================================================================#
def CalGetByte(addr,ptr):
    VerifyADDR(addr)
    assert ((ptr>=0) and (ptr<=255)),"Calibration pointer is out of range. Must be in the range of 0 to 255" 
    resp=ppCMD(addr,0xFD,2,ptr,1)
    return resp[0]
    
def CalPutByte(addr,data):
    VerifyADDR(addr)
    assert ((data>=0) and (data<=255)),"Calibration value is out of range. Must be in the range of 0 to 255"
    ppCMD(addr,0xFD,1,data,0)
    
def CalEraseBlock(addr):
    VerifyADDR(addr)
    ppCMD(addr,0xFD,0,0,0)    
    
#==============================================================================#    
# SYSTEM Functions                                                             #
#==============================================================================#     
def getID(addr):
    global CURRENTbaseADDR
    VerifyADDR(addr)
    addr=addr+CURRENTbaseADDR
    return CMD.getID2(addr)

def getHWrev(addr):
    global CURRENTbaseADDR
    VerifyADDR(addr)
    resp=ppCMD(addr,0x02,0,0,1)
    rev = resp[0]
    whole=float(rev>>4)
    point = float(rev&0x0F)
    return whole+point/10.0  
    
def getFWrev(addr):
    global CURRENTbaseADDR
    VerifyADDR(addr)
    resp=ppCMD(addr,0x03,0,0,1)
    rev = resp[0]
    whole=float(rev>>4)
    point = float(rev&0x0F)
    return whole+point/10.0

def getVersion():
    return version      

def setINT(addr):
    VerifyADDR(addr)
    ppCMD(addr,0xF4,0,0,0)

def clrINT(addr):
    VerifyADDR(addr)
    ppCMD(addr,0xF5,0,0,0)
        
#==============================================================================#    
# LOW Level Functions                                                          #
#==============================================================================#          
def VerifyIchannel(Iin):
    assert ((Iin>=1) and (Iin<=8)),"4-20mA input channel value out of range. Must be in the range of 1 to 8" 

def VerifyADDR(addr):
    assert ((addr>=0) and (addr<MAXADDR)),"CURRENTplate address out of range"
    addr_str=str(addr)
    assert (CURRENTPresent[addr]==1),"No CURRENTplate found at address "+addr_str


def ppCMD(addr,cmd,param1,param2,bytes2return):
    global CURRENTbaseADDR
    return CMD.ppCMD2(addr+CURRENTbaseADDR,cmd,param1,param2,bytes2return)    
    
def getADDR(addr):
    global CURRENTbaseADDR
    resp=ppCMD(addr,0x00,0,0,1)
    if (CMD.DataGood):
        return resp[0]-CURRENTbaseADDR
    else:
        return 8
    
def quietPoll():   
    global CURRENTPresent
    global DataGood
    ppFoundCount=0
    for i in range (0,8):
        CURRENTPresent[i]=0
        rtn = getADDR(i)
        if (rtn==i):           
            CURRENTPresent[i]=1
            ppFoundCount += 1

def RESET(addr):
    VerifyADDR(addr)
    ppCMD(addr,0x0F,0,0,0)    
    time.sleep(1.1)

quietPoll()    
