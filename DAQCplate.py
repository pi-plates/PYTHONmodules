import spidev
import time
import string
import site
import sys
import RPi.GPIO as GPIO
from six.moves import input as raw_input
GPIO.setwarnings(False)

#Initialize
if (sys.version_info < (2,7,0)):
    sys.stderr.write("You need at least python 2.7.0 to use this module")
    exit(1)
    
GPIO.setmode(GPIO.BCM)
GPIObaseADDR=8
ppFRAME = 25
ppINT = 22
GPIO.setup(ppFRAME,GPIO.OUT)
GPIO.output(ppFRAME,False)  #Initialize FRAME signal
GPIO.setup(ppINT, GPIO.IN, pull_up_down=GPIO.PUD_UP)    #reserve interrupt input
spi = spidev.SpiDev()
spi.open(0,1)	
localPath=site.getsitepackages()[0]
helpPath=localPath+'/piplates/DAQChelp.txt'
#helpPath='DAQChelp.txt'
DAQCversion=1.5
#Version 1.5 - fixed read issues with getaADCall and getID
#Version 1.4 - added Python 3 compatibility
daqcsPresent = list(range(8))
Vcc=list(range(8))
MAXADDR=8
	
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
                        Input=raw_input('press \"Enter\" for more...')                        
                else:
                    Count=100
                    valid=False
        f.close()
    except IOError:
        print ("Can't find help file.")



#===============================================================================#	
# ADC Functions	     	                                              			#
#===============================================================================#	
def getADC(addr,channel):
    VerifyADDR(addr)
    VerifyAINchannel(channel)
	
    resp=ppCMD(addr,0x30,channel,0,2)
    value=(256*resp[0]+resp[1])
    value=round(value*4.096/1024,3)
    if (channel==8):
        value=value*2.0
    return value

def getADCall(addr):
    value=range(8)
    VerifyADDR(addr)    
    #resp=ppCMD(addr,0x31,0,0,16)
    for i in range (0,8):
        resp=ppCMD(addr,0x30,i,0,2)
        value[i]=(256*resp[0]+resp[1])
        value[i]=round(value[i]*4.096/1024,3)        
        # value[i]=(256*resp[2*i]+resp[2*i+1])
        # value[i]=round(value[i]*4.096/1024,3)
    return value    
    
#===============================================================================#	
# Digital Input Functions	                                                   	#
#===============================================================================#
def getDINbit(addr,bit):
    VerifyADDR(addr)
    VerifyDINchannel(bit)
    resp=ppCMD(addr,0x20,bit,0,1)
    if resp[0] > 0:
        return 1
    else:
        return 0
		
def getDINall(addr):
    VerifyADDR(addr)
    resp=ppCMD(addr,0x25,0,0,1)
    return resp[0]

def enableDINint(addr, bit, edge):	# enable DIN interrupt
    VerifyADDR(addr)
    VerifyDINchannel(bit)	
    if ((edge=='f') or (edge=='F')):
        resp=ppCMD(addr,0x21,bit,0,0)		
    if ((edge=='r') or (edge=='R')):
        resp=ppCMD(addr,0x22,bit,0,0)
    if ((edge=='b') or (edge=='B')):
        resp=ppCMD(addr,0x23,bit,0,0)		
		
def disableDINint(addr,bit):	# disable DIN interrupt
    VerifyADDR(addr)
    VerifyDINchannel(bit)
    resp=ppCMD(addr,0x24,bit,0,0)
	
def getTEMP(addr,channel,scale):
    VerifyADDR(addr)
    assert ((channel>=0) and (channel<=7)),"Channel value out of range. Must be a value between 0 and 7"
    scal=scale.lower()
    assert ((scal=='c') or (scal=='f') or (scal=='k')), "Temperature scale must be 'c', 'f', or 'k'."
    resp=ppCMD(addr,0x70,channel,0,0)   #initiate measurement
    time.sleep(1)
    resp=ppCMD(addr,0x71,channel,0,2)   #get data
    Temp=resp[0]*256+resp[1]
    if (Temp>0x8000):
        Temp = Temp^0xFFFF
        Temp = -(Temp+1)
    Temp = round((Temp/16.0),4)
    if (scal=='k'):
        Temp = Temp + 273
    if (scal=='f'):
        Temp = round((Temp*1.8+32.2),4)
    return Temp
    
    
#===============================================================================#	
# Hybrid Functions	                                                   	#
#===============================================================================#    
def getRANGE(addr,channel,units):
    VerifyADDR(addr)
    assert ((channel>=0) and (channel<=6)),"Channel value out of range. Must be a value between 0 and 6"
    uni=units.lower()
    assert ((uni=='c') or (uni=='i')), "ERROR: incorrect units parameter. Must be 'c' or 'i'."
    resp=ppCMD(addr,0x80,channel,0,0)   #initiate measurement
    time.sleep(.07)
    resp=ppCMD(addr,0x81,channel,0,2)   #get data
    Range=resp[0]*256+resp[1]
    assert (Range!=0), "ERROR: sensor failure"
    if (uni=='c'):
        Range = Range/58.326
    if (uni=='i'):
        Range = Range/148.148
    Range=round(Range,2)
    return Range
    
#===============================================================================#	
# LED Functions	                                                   		   		#
#===============================================================================#			
def setLED(addr,led):
    VerifyADDR(addr)
    VerifyLED(led)
    resp=ppCMD(addr,0x60,led,0,0)

def clrLED(addr,led):
    VerifyADDR(addr)
    VerifyLED(led)
    resp=ppCMD(addr,0x61,led,0,0)

def toggleLED(addr,led):
    VerifyADDR(addr)
    VerifyLED(led)
    resp=ppCMD(addr,0x62,led,0,0)	

def getLED(addr,led):
    VerifyADDR(addr)
    VerifyLED(led)
    resp=ppCMD(addr,0x63,led,0,1)
    return resp[0]	

def VerifyLED(led):
    assert (led>=0 and led<=1),"Invalid LED value. Must be 0 or 1"
    
#==============================================================================#	
# Switch Functions	                                                   #
#==============================================================================#		
def getSWstate(addr):
    VerifyADDR(addr)
    resp=ppCMD(addr,0x50,0,0,1)
    return resp[0]

def enableSWint(addr):
    VerifyADDR(addr)
    resp=ppCMD(addr,0x51,0,0,0)

def disableSWint(addr):
    VerifyADDR(addr)
    resp=ppCMD(addr,0x52,0,0,0)		
	
def enableSWpower(addr):
    VerifyADDR(addr)
    resp=ppCMD(addr,0x53,0,0,0)

def disableSWpower(addr):
    VerifyADDR(addr)
    resp=ppCMD(addr,0x54,0,0,0)
		
		
#==============================================================================#	
# Digital Output Functions	                                                   #
#==============================================================================#	
def setDOUTbit(addr,bit):
    VerifyADDR(addr)
    VerifyDOUTchannel(bit)
    resp=ppCMD(addr,0x10,bit,0,0)

	
def clrDOUTbit(addr,bit):
    VerifyADDR(addr)
    VerifyDOUTchannel(bit)
    resp=ppCMD(addr,0x11,bit,0,0)		

def toggleDOUTbit(addr,bit):
    VerifyADDR(addr)
    VerifyDOUTchannel(bit)
    resp=ppCMD(addr,0x12,bit,0,0)		
	
def setDOUTall(addr,byte):
    VerifyADDR(addr)
    assert ((byte>=0) and (byte<=127)),"Digital output value out of range. Must be in the range of 0 to 127"
    resp=ppCMD(addr,0x13,byte,0,0)			

def getDOUTbyte(addr):
    VerifyADDR(addr)
    resp=ppCMD(addr,0x14,0,0,1)
    return resp


#==============================================================================#	
# PWM and DAC Output Functions	                                                   #
#==============================================================================#	
def setPWM(addr,channel,value):
    VerifyADDR(addr)
    assert (value<=1023 and value>=0), "ERROR: PWM argument out of range - must be between 0 and 1023"
    assert (channel==0 or channel==1), "Error: PWM channel must be 0 or 1"
    hibyte = value>>8
    lobyte = value - (hibyte<<8)
    resp=ppCMD(addr,0x40+channel,hibyte,lobyte,0)

def getPWM(addr,channel):
    VerifyADDR(addr)
    assert (channel==0 or channel==1), "Error: PWM channel must be 0 or 1"
    ## Return PWM set value
    resp=ppCMD(addr,0x40+channel+2,0,0,2)
    value=(256*resp[0]+resp[1])
    return value	
	
def setDAC(addr,channel,value):
    global Vcc
    VerifyADDR(addr)
    assert (value>=0 and value<=4.095), "ERROR: PWM argument out of range - must be between 0 and 4.095 volts"
    assert (channel==0 or channel==1), "Error: DAC channel must be 0 or 1"
    value = int(value/Vcc[addr]*1024)
    hibyte = value>>8
    lobyte = value - (hibyte<<8)
    resp=ppCMD(addr,0x40+channel,hibyte,lobyte,0)

	
def getDAC(addr,channel):
    global Vcc
    VerifyADDR(addr)
    assert (channel==0 or channel==1), "Error: DAC channel must be 0 or 1"
    ## Return DAC value
    resp=ppCMD(addr,0x40+channel+2,0,0,2)
    value=(256*resp[0]+resp[1])
    value=value*Vcc[addr]/1023
    return value

def calDAC(addr):
    global Vcc
    VerifyADDR(addr)
    Vcc[addr] = getADC(addr,8)   
        
#==============================================================================#	
# Interrupt Control Functions	                                               #
#==============================================================================#	
def intEnable(addr):	#DAQC will pull down on INT pin if an enabled event occurs
    VerifyADDR(addr)
    resp=ppCMD(addr,0x04,0,0,0)
	
def intDisable(addr):
    VerifyADDR(addr)
    resp=ppCMD(addr,0x05,0,0,0)
	
def getINTflags(addr):	#read INT flag registers in DAQC
    VerifyADDR(addr)
    resp=ppCMD(addr,0x06,0,0,2)
    value=(256*resp[0]+resp[1])
    return value
		
#==============================================================================#	
# System Functions	                                                   		   #
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
    return DAQCversion    
    
def getADDR(addr):
    assert ((addr>=0) and (addr<MAXADDR)),"DAQCplate address must be in the range of 0 to 7"
    resp=ppCMD(addr,0x00,0,0,1)
    return resp[0]
	
def getID(addr):
    global GPIObaseADDR
    VerifyADDR(addr)
    addr=addr+GPIObaseADDR
    id=""
    arg = list(range(4))
    resp = []
    arg[0]=addr;
    arg[1]=0x1;
    arg[2]=0;
    arg[3]=0;
    ppFRAME = 25
    GPIO.output(ppFRAME,True)
    #null = spi.writebytes(arg)
    null=spi.xfer(arg,300000,60)
    count=0
#    time.sleep(.0001)
    while (count<20): 
        dummy=spi.xfer([00],300000,20)
#        time.sleep(.0001)
        if (dummy[0] != 0):
            num = dummy[0]
            id = id + chr(num)
            count = count + 1
        else:
            count=20
    GPIO.output(ppFRAME,False)
    return id	
	
def getPROGdata(addr,paddr):	#read a byte of data from program memory
    VerifyADDR(addr)
    resp=ppCMD(addr,0xF0,paddr>>8,paddr&0xFF,2)
    value=(256*resp[0]+resp[1])
    return hex(value)	

def Poll():
    ppFoundCount=0
    for i in range (0,8):
        rtn = getADDR(i)
        if ((rtn-8)==i):
            print ("DAQCplate found at address",rtn-8)
            ppFoundCount += 1
    if (ppFoundCount == 0):
        print ("No DAQCplates found")

def VerifyDINchannel(din):
    assert ((din>=0) and (din<=7)),"Digital input channel value out of range. Must be in the range of 0 to 7"

def VerifyAINchannel(ain):
    assert ((ain>=0) and (ain<=8)),"Analog input channel value out of range. Must be in the range of 0 to 8"    
   
def VerifyDOUTchannel(dout):
    assert ((dout>=0) and (dout<=6)),"Digital output channel value out of range. Must be in the range of 0 to 6"
   
def VerifyADDR(addr):
    assert ((addr>=0) and (addr<MAXADDR)),"DAQCplate address must be in the range of 0 to 7"
    addr_str=str(addr)
    assert (daqcsPresent[addr]==1),"No DAQCplate found at address "+addr_str
	
def ppCMD(addr,cmd,param1,param2,bytes2return):
    global GPIObaseADDR
    arg = list(range(4))
    resp = []
    arg[0]=addr+GPIObaseADDR;
    arg[1]=cmd;
    arg[2]=param1;
    arg[3]=param2;
    #    time.sleep(.0005)
    GPIO.output(ppFRAME,True)
    null=spi.xfer(arg,300000,40)
    #null = spi.writebytes(arg)   
    if bytes2return>0:
        time.sleep(.0001)        
        for i in range(0,bytes2return):	
            dummy=spi.xfer([00],500000,20)
            resp.append(dummy[0])        
    GPIO.output(ppFRAME,False)
    time.sleep(.0003)
    return resp	
	

def Init():	
    global daqcsPresent
    global Vcc
    for i in range (0,8):
        daqcsPresent[i]=0
        Vcc[i]=10000
        rtn = getADDR(i)
        if ((rtn-8)==i):
            daqcsPresent[i]=1
            ok=0
            while(ok==0):              
                Vcc[i] = getADC(i,8)
                if Vcc[i]>3.0:
                    ok=1
            setDOUTall(i,0)
            setPWM(i,0,0)
            setPWM(i,1,0)

    
Init()
