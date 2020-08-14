import spidev
import time
import string
import site
import sys
from gpiozero import CPUTemperature
import RPi.GPIO as GPIO
GPIO.setwarnings(False)

#Initialize
if (sys.version_info < (3,0,0)):
    sys.stderr.write("This library only works for Python3")
    exit(1)
    
GPIO.setmode(GPIO.BCM)
POWERbaseADDR=0
ppFRAME = 25
ppINT = 22
ppACK = 23
ppSW = 24
GPIO.setup(ppFRAME,GPIO.OUT)
GPIO.output(ppFRAME,False)  #Initialize FRAME signal
time.sleep(.001)            #let Pi-Plate reset SPI engine if necessary
GPIO.setup(ppINT, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(ppACK, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(ppSW, GPIO.IN, pull_up_down=GPIO.PUD_UP)
spi = spidev.SpiDev()
spi.open(0,1)	
localPath=site.getsitepackages()[0]
#helpPath=localPath+'/piplates/POWERhelp.txt'
helpPath='POWERhelp.txt'       #for development only
POWERversion=1.0
DataGood=False
cpu = CPUTemperature()

GRN=0
RED=1

RMAX = 2000
MAXADDR=8

powerPresent = 0

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
# A2D Functions	     	                                              		   #
#==============================================================================#	
def getVin(addr=None):
    resp=ppCMD(0,0x30,0,0,2)
    value=(256*resp[0]+resp[1])
    value=round((value*2.4*2.5/4095),3)
    return value   

def getIin(addr=None):
    resp=ppCMD(0,0x30,1,0,2)
    value=(256*resp[0]+resp[1])
    value=round((value*2.4*2.0/4095),3)
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
    if (led=='GREEN' or led=='GR'):
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

def enablePOWERSW(addr=None):
    resp=ppCMD(0,0x53,0,0,0)

def disablePOWERSW(addr=None):
    resp=ppCMD(0,0x54,0,0,0)    

def powerOFF(addr=None):
    resp=ppCMD(0,0x56,0,0,0)
    

 
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
    global POWERbaseADDR
    global DataGood
    DataGood=True
    arg = list(range(4))
    resp = []
    arg[0]=0;
    arg[1]=cmd;
    arg[2]=param1;
    arg[3]=param2;
    GPIO.output(ppFRAME,True)
    null=spi.xfer(arg,1000000,1)
    DataGood=True
    t0=time.time()
    wait=True
    while(wait):
        if (GPIO.input(ppACK)!=1):
            wait=False
        if ((time.time()-t0)>0.05):   #timeout
            wait=False
            DataGood=False    
    if (bytes2return>0) and DataGood:
        t0=time.time()
        wait=True
        while(wait):
            if (GPIO.input(ppACK)!=1):              
                wait=False
            if ((time.time()-t0)>0.08):   #timeout
                wait=False
                DataGood=False
        if (DataGood==True):
            #time.sleep(.0001)
            for i in range(0,bytes2return+1):	
                dummy=spi.xfer([00],1000000,5)
                resp.append(dummy[0])
            csum=0;
            for i in range(0,bytes2return):
                csum+=resp[i]
            if ((~resp[bytes2return]& 0xFF) != (csum & 0xFF)):
                DataGood=False
    #time.sleep(.001)
    GPIO.output(ppFRAME,False)
    #time.sleep(.001)
    return resp
 
def getID(addr=None):
    id=""
    arg = list(range(4))
    resp = []
    arg[0]=0;
    arg[1]=0x1;
    arg[2]=0;
    arg[3]=0;
    ppFRAME = 25
    GPIO.output(ppFRAME,True)
    null=spi.xfer(arg,500000,50)
    DataGood=True
    t0=time.time()
    wait=True
    while(wait):
        if (GPIO.input(ppACK)!=1):              
            wait=False
        if ((time.time()-t0)>0.05):   #timeout
            wait=False
            DataGood=False
    if (DataGood==True):
        count=0 
        csum=0
        go=True
        while (go): 
            dummy=spi.xfer([00],500000,40)
            if (dummy[0] != 0):
                num = dummy[0]
                csum += num
                id = id + chr(num)
                #print count, num
                count += 1
            else:
                dummy=spi.xfer([00],500000,40)  
                checkSum=dummy[0]                
                go=False 
            if (count>25):
                go=False
                DataGood=False
        #print checkSum, ~checkSum & 0xFF, csum & 0xFF
        if ((~checkSum & 0xFF) != (csum & 0xFF)):
            DataGood=False
    GPIO.output(ppFRAME,False)
    return id
    
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
    if (DataGood):
        return resp[0]
    else:
        return 8
    
def quietPoll():   
    global powerPresent
    rtn = getADDR()
    if (rtn==0):           
        powerPresent=1   
        setRTC(0,'l')       

def RESET(addr):
    VerifyADDR(addr)
    resp=ppCMD(addr,0x0F,0,0,0)    
    time.sleep(1)
    quietPoll()

quietPoll()            