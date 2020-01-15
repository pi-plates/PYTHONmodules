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
DAQC2baseADDR=32
ppFRAME = 25
ppINT = 22
ppACK = 23
GPIO.setup(ppFRAME,GPIO.OUT)
GPIO.output(ppFRAME,False)  #Initialize FRAME signal
time.sleep(.001)            #let Pi-Plate reset SPI engine if necessary
GPIO.setup(ppINT, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(ppACK, GPIO.IN, pull_up_down=GPIO.PUD_UP)
spi = spidev.SpiDev()
spi.open(0,1)	
localPath=site.getsitepackages()[0]
helpPath=localPath+'/piplates/DAQC2help.txt'
#helpPath='DAQC2help.txt'       #for development only
DAQC2version=1.0
DataGood=False

RMAX = 2000
MAXADDR=8

daqc2sPresent = list(range(8))
calScale=[[0 for z in range(8)] for x in range(8)]   #16 bit signed slope calibration values - range is +/-4%
calOffset=[[0 for z in range(8)] for x in range(8)]  #16 bit signed offset calibration values - range is +/-0.1
calDAC=[[0 for z in range(8)] for x in range(8)] #16 bit signed DAC calibration values - range is +/-4%
calSet=list(range(8))
PWMvals=[[0,0],[0,0],[0,0],[0,0],[0,0],[0,0],[0,0],[0,0]]

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

#==============================================================================#	
# A2D Functions	     	                                              		   #
#==============================================================================#	
def getADC(addr,channel):
    VerifyADDR(addr)
    VerifyAINchannel(channel)
	
    resp=ppCMD(addr,0x30,channel,0,2)
    value=(256*resp[0]+resp[1])
    if (channel==8):
        value=value*5.0*2.4/65536
    else:
        value=(value*24.0/65536)-12.0
        value=round(value*calScale[addr][channel]+calOffset[addr][channel],3)
    return value

def getADCall(addr):
    value=list(range(8))
    VerifyADDR(addr)    
    resp=ppCMD(addr,0x31,0,0,16)
    for i in range (0,8):
        value[i]=(256*resp[2*i]+resp[2*i+1])
        value[i]=(value[i]*24.0/65536)-12.0
        value[i]=round(value[i]*calScale[addr][i]+calOffset[addr][i],3)
    return value    
            
#==============================================================================#	
# DAC Output Functions	                                                       #
#==============================================================================#	
def setDAC(addr,channel,value):
    VerifyADDR(addr)
    assert (value>=0 and value<=4.095), "ERROR: DAC argument out of range - must be between 0 and 4.095 volts"
    assert (channel>=0 or channel<=3), "Error: DAC channel must be in the range of 0 to 3"
    value = int(value*calDAC[addr][channel]*1000)
    if (value>4095):
        value=4095
    hibyte = value>>8
    lobyte = value - (hibyte<<8)
    resp=ppCMD(addr,0x40+channel,hibyte,lobyte,0)
	
def getDAC(addr,channel):
    global Vcc
    VerifyADDR(addr)
    assert (channel>=0 or channel<=3), "Error: DAC channel must be in the range of 0 to 3"
    ## Return DAC value
    resp=ppCMD(addr,0x40+channel+4,0,0,2)
    value=(256*resp[0]+resp[1])
    value=value/1000.0
    return value
            
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
    assert ((byte>=0) and (byte<=255)),"Digital output value out of range. Must be in the range of 0 to 255"
    resp=ppCMD(addr,0x13,byte,0,0)			

def getDOUTbyte(addr):
    VerifyADDR(addr)
    resp=ppCMD(addr,0x14,0,0,1)
    return resp        

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

#===============================================================================#	
# Interrupt Functions	                                                   		    #
#===============================================================================#	
def intEnable(addr):	#DAQC2 will pull down on INT pin if an enabled event occurs
    VerifyADDR(addr)
    resp=ppCMD(addr,0x04,0,0,0)
	
def intDisable(addr):   #DAQC2 will not assert interrupts
    VerifyADDR(addr)
    resp=ppCMD(addr,0x05,0,0,0)
    
def getINTflags(addr):	#read INT flag register in DAQC2 - this clears interrupt line and the register
    VerifyADDR(addr)
    resp=ppCMD(addr,0x06,0,0,2)
    value=(256*resp[0]+resp[1])
    return value
    
#===============================================================================#	
# LED Functions	                                                                #
# Valid led values are: off, red, yellow, green, cyan, blue, magenta, and white.#
#===============================================================================#			
LEDcolors=['off','red','green','yellow','blue','magenta','cyan','white']

def setLED(addr,led):
    VerifyADDR(addr)
    value=VerifyLED(led)
    resp=ppCMD(addr,0x60,value,0,0)

def getLED(addr):
    VerifyADDR(addr)
    resp=ppCMD(addr,0x63,0,0,1)
    return LEDcolors[resp[0]]

def VerifyLED(led):
    flag=False
    for i in range(8):
        if (led == LEDcolors[i]):
            flag=True
            value=i
    assert (flag),"-"+led + "- is not a valid LED color"
    return value
#==============================================================================#	
# Oscilloscope Functions                                                       #
#==============================================================================#   
# Shadow Registers with Defaults
#cCount=1
C1state=1
C2state=0
sRate=9
trace1=list(range(1024))
trace2=list(range(1024))
OSCtriggerChan=0   
OSCtriggerType=0
OSCtriggerEdge=0
OSCtriggerLevel=0 

def startOSC(addr):
    VerifyADDR(addr)
    #cmd = 1
    resp=ppCMD(addr,0xA1,0,0,0)
    
def stopOSC(addr):
    VerifyADDR(addr)
    #cmd = 0
    resp=ppCMD(addr,0xA0,0,0,0)
    
def runOSC(addr):
    VerifyADDR(addr)
    #cmd = 5
    resp=ppCMD(addr,0xA5,0,0,0)    
      
def setOSCchannel(addr, C1, C2):
    global C1state, C2state
    #cmd=2
    VerifyADDR(addr) 
    assert (C1==1 or C1==0),"Invalid Channel One State. Must be 0 or 1"
    assert (C2==1 or C2==0),"Invalid Channel Two State. Must be 0 or 1"
    C1state=C1
    C2state=C2  
    #assert (channelCount>=1 and channelCount<=2),"Invalid Channel Count. Must be between 1 and 2"
    #cCount=channelCount
    #resp=ppCMD(addr,0xA2,channelCount-1,0,0)
    resp=ppCMD(addr,0xA2,C1,C2,0)
    
def setOSCsweep(addr,rate):
    global sRate
    VerifyADDR(addr) 
    #cmd=3
    #rate is in range of 0 to 12
    # the following values are used by the microprocessor
    #rates: samples/sec    time/div     Timer Relod Value
    # 0:    100             1sec              0x15A0
    # 1:    200             500msec           0x8AD0
    # 2:    500             200msec           0xD120
    # 3:    1000            100msec           0xE890
    # 4:    2000            50msec            0xF448
    # 5:    5000            20msec            0xFB50 
    # 6:    10,000          10msec            0xFDA8            
    # 7:    20,000          5msec             0xFED4
    # 8:    50,000          2msec             0xFF88
    # 9:    100,000         1msec             0xFFC4
    # 10:   200,000         500usec           0xFFE2
    # 11:   500,000         200usec           0xFFF4
    # 12:   1,000,000       100usec           0xFFFA           
    # note that #12 is only valid for a single channel input
    assert ((rate>=0) and (rate<=12)),"Sweep rate value out of range. Must be in the range of 0 to 12"
    sRate=rate
    resp=ppCMD(addr,0xA3,rate,0,0)			


def getOSCtraces(addr):  
    global C1state, C2state
    cCount=C1state+C2state
    VerifyADDR(addr)
    resp=ppCMD(addr,0xA4,0,0,cCount*2048)
    if (cCount==2):
        for i in range(1024):
            trace1[i]=resp[4*i]*256+resp[4*i+1]
            trace2[i]=resp[4*i+2]*256+resp[4*i+3]
    else:
        if(C1state):
            for i in range(1024):
                trace1[i]=resp[2*i]*256+resp[2*i+1]
        else:
            for i in range(1024):
                trace2[i]=resp[2*i]*256+resp[2*i+1]            
    
    
def setOSCtrigger(addr,channel,type,edge,level):    
#channels: 1 or 2    0 or 1
#type: normal or auto   0 or 1
#edge: rising or falling 0 or 1
#level: 12 bit value in range of +/-12V (0 to 4095)
    options=0
    VerifyADDR(addr)
    assert (channel>=1 and channel<=2),"Invalid Channel value. Must be between 1 and 2"
    option=128*(channel-1)
    type = type.lower()
    assert (type=='auto' or type=='normal'),"Invalid trigger type. Must be 'Auto' or 'Normal'"
    if (type=='normal'):
        option += 64
    edge = edge.lower() 
    assert (edge=='rising' or edge=='falling'),"Invalid trigger edge. Must be 'rising' or 'falling'"
    if (edge=='falling'):
        option += 32
    assert (level>=0 and level <=4095),"Invalid trigger level. Must be between 0 and 4095"     
    resp=ppCMD(addr,0xA6,option+(level>>8),level&0xFF,0)
        
def setOSCtrigpos(addr,position):    # not used at this time
#position: 10 bit value in range of 0 to 999
    VerifyADDR(addr)
    assert (position>=0 and position <=999),"Invalid position. Must be between 0 and 999" 
    #Assuming a circular buffer with 64 blocks of data then tell DAQC2 how many blocks to
    #capture after after the trigger is detected. 
    bCount=int((1000-position)/1000*32+0.5)
    resp=ppCMD(addr,0xA8,bCount,0,0)
    
def setOSCvertical(sensitivity):
#set vertical scale of display
#sensitivity values are:
# 0:  10mV/div
# 1:  20mV/div
# 2:  50mV/div
# 3:  100mV/div
# 4:  200mV/div
# 5:  500mV/div
# 6:  1V/div
# 7:  2V/div
# 8:  5V/div
    assert ((sensitivity>=0) and (sensitivity<=8)),"Vertical sensitivity value out of range. Must be in the range of 0 to 8"

def zoomOSChorizontal(scale):
#set horizontal zoom
    assert ((scale>=1) and (scale<=10)),"Horizontal value out of range. Must be in the range of 1 to 10"
    
def setOSCoffset(offset):
#function to move trace up and down on screen
    assert ((offset>=-10) and (offset<=10)),"Offset value out of range. Must be in the range of -10 to 10"

def trigOSCnow(addr):
    VerifyADDR(addr)
    resp=ppCMD(addr,0xA7,0,0,0)
     
#==============================================================================#	
# Function Generator                                                           #
#==============================================================================#     
def fgON(addr,chan):
    VerifyADDR(addr)
    VerifyFGchannel(chan)
    resp=ppCMD(addr,0x91,chan-1,0,0)

def fgOFF(addr,chan):
    VerifyADDR(addr)
    VerifyFGchannel(chan)
    resp=ppCMD(addr,0x90,chan-1,0,0)    
    
def fgFREQ(addr,chan,freq):
    VerifyADDR(addr)
    VerifyFGchannel(chan)
    assert ((freq>=10) and (freq<=20000)),"Function Generator frequency value out of range. Must be in the range of 10 to 20,000"    
    # SAMPLE_RATE_DAC 100000L        // DAC sampling rate in Hz
    # PHASE_PRECISION 65536          // Range of phase accumulator
    # FREQUENCY       FREQ           // Frequency of output in Hz
    # PHASE_ADD = FREQUENCY * PHASE_PRECISION / SAMPLE_RATE_DAC
    phase_adder=int(freq*65536/100000+0.5)
    resp=ppCMD(addr,0x92+chan-1,phase_adder>>8,phase_adder&0xFF,0) 
  
def fgTYPE(addr,chan,type):
    VerifyADDR(addr)
    VerifyFGchannel(chan)
    assert ((type>=1) and (type<=7)),"Function Generator output type is out of range. Must be in the range of 1 to 7"    
    #types:
    #   1)  sine
    #   2)  triangle
    #   3)  square
    #   4)  sawtooth rising
    #   5)  sawtooth falling
    #   6)  noise
    #   7)  sinc
    resp=ppCMD(addr,0x96,chan-1,type-1,0)
    
def fgLEVEL(addr,chan,level):
    VerifyADDR(addr)
    VerifyFGchannel(chan)
    assert ((level>=1) and (level<=4)),"Function Generator output level is out of range. Must be in the range of 1 to 4"    
    resp=ppCMD(addr,0x97,chan-1,level,0)

#==============================================================================#	
# Stepper Motor Functions                                                      #
#==============================================================================#    
def motorENABLE(addr):
    VerifyADDR(addr)
    resp=ppCMD(addr,0xB1,0,0,0)
    
def motorDISABLE(addr):
    VerifyADDR(addr) 
    resp=ppCMD(addr,0xB0,0,0,0)    

def motorMOVE(addr,motor,steps):
    VerifyADDR(addr)
    assert ((motor>=1) and (motor<=2)),"Motor number is out of range. Must be 1 or 2" 
    assert ((steps>=-16383) and (steps<=16383)),"Step count is out of range. Must be between -16383 and 16383"
    if (steps<0):
        stepSign=1
    else:
        stepSign=0
    steps=abs(steps)
    param1=((motor-1)<<7) + (stepSign<<6) + (steps>>8)       
    param2= steps & 0xFF
    resp=ppCMD(addr,0xB4,param1,param2,0)
    
def motorJOG(addr,motor):
    VerifyADDR(addr)
    assert ((motor>=1) and (motor<=2)),"Motor number is out of range. Must be 1 or 2"
    resp=ppCMD(addr,0xB5,motor-1,0,0)
 
def motorSTOP(addr,motor):
    VerifyADDR(addr)
    assert ((motor>=1) and (motor<=2)),"Motor number is out of range. Must be 1 or 2"
    resp=ppCMD(addr,0xB6,motor-1,0,0)
 
def motorDIR(addr,motor,dir):
    VerifyADDR(addr)
    assert ((motor>=1) and (motor<=2)),"Motor number is out of range. Must be 1 or 2"   
    dir=dir.lower()
    assert ((dir=='ccw') or (dir=='cw')), "Direction must be either clockwise (cw) or counter-clockwise (ccw)"
    if (dir=='cw'):
        param2=0
    else:
        param2=1
    resp=ppCMD(addr,0xB3,motor-1,param2,0)

def motorRATE(addr,motor,rate,stepsize):
    VerifyADDR(addr)
    assert ((motor>=1) and (motor<=2)),"Motor number is out of range. Must be 1 or 2"
    stepsize=stepsize.lower()  
    assert ((stepsize=='w') or (stepsize=='h')),"Stepsize must be either whole (w) or half (h)"
    assert ((rate>=1) and (rate<=500)),"Rate must be greater than 1 and less than 500 steps/sec"    
    rateInc=int(rate*(2**13)/1000.0+0.5)     #convert step rate to an accumulator increment
    param1=((motor-1)<<7)+(rateInc>>8)
    if (stepsize=='h'):
        param1 |= 0x40
    param2=rateInc&0xFF
    #print motor, rate, stepsize, rateInc, param1, param2
    resp=ppCMD(addr,0xB2,param1,param2,0)

def motorOFF(addr,motor):
    VerifyADDR(addr)
    assert ((motor>=1) and (motor<=2)),"Motor number is out of range. Must be 1 or 2" 
    resp=ppCMD(addr,0xBA,motor-1,0,0)

def motorINTenable(addr,motor):
    VerifyADDR(addr)
    assert ((motor>=1) and (motor<=2)),"Motor number is out of range. Must be 1 or 2" 
    resp=ppCMD(addr,0xB7,motor-1,0,0)
 
def motorINTdisable(addr,motor):
    VerifyADDR(addr)
    assert ((motor>=1) and (motor<=2)),"Motor number is out of range. Must be 1 or 2" 
    resp=ppCMD(addr,0xB8,motor-1,0,0)
 
#==============================================================================#	
# PWM and Frequency Counter Functions	                                       #
#==============================================================================# 
def getFREQ(addr):
    VerifyADDR(addr)
    freq=0
    resp=ppCMD(addr,0xC0,0,0,2) #get the upper 16 bits
    if(DataGood):
        counts=(resp[0]<<24)+(resp[1]<<16)
        resp=ppCMD(addr,0xC0,1,0,2) #get the lower 16 bits
        if (DataGood):
            counts=counts+(resp[0]<<8)+resp[1]
            if (counts>0):
                freq=6000000.0/counts
    return round(freq,2)
    
def setPWM(addr,chan,dutyCycle):
    global PWMvals
    VerifyADDR(addr)
    assert ((chan>=0) and (chan<=1)),"PWM Channel number is out of range. Must be 0 or 1"
    assert ((dutyCycle>=0)and(dutyCycle<=100)), "Duty Cycle must be a value between 0 and 100"
    registerVal=int(dutyCycle*1023/100+0.5)
    param1=((chan)<<7)+(registerVal>>8)
    param2=registerVal&0xFF
    resp=ppCMD(addr,0xC1,param1,param2,0)
    PWMvals[addr][chan]=dutyCycle
    
def getPWM(addr,chan):
    global PWMvals
    VerifyADDR(addr)
    assert ((chan>=0) and (chan<=1)),"PWM Channel number is out of range. Must be 0 or 1"
    return PWMvals[addr][chan]
      
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
    return DAQC2version   

def setINT(addr):
    VerifyADDR(addr)
    resp=ppCMD(addr,0xF4,0,0,0)

def clrINT(addr):
    VerifyADDR(addr)
    resp=ppCMD(addr,0xF5,0,0,0)
	
def getID(addr):
    global DAQC2baseADDR
    VerifyADDR(addr)
    addr=addr+DAQC2baseADDR
    id=""
    arg = list(range(4))
    resp = []
    arg[0]=addr;
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

def getMode(addr):
    VerifyADDR(addr)
    resp=ppCMD(addr,0x08,0,0,1)
    return resp[0]

    
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
    resp=ppCMD(addr,0xFD,1,data,0)
    
def CalEraseBlock(addr):
    VerifyADDR(addr)
    resp=ppCMD(addr,0xFD,0,0,0)
    
#==============================================================================#	
# LOW Level Functions	                                                       #
#==============================================================================#          
def VerifyAINchannel(ain):
    assert ((ain>=0) and (ain<=8)),"Analog input channel value out of range. Must be in the range of 0 to 8"    


def VerifyADDR(addr):
    assert ((addr>=0) and (addr<MAXADDR)),"DAQC2plate address out of range"
    addr_str=str(addr)
    assert (daqc2sPresent[addr]==1),"No DAQC2plate found at address "+addr_str

def VerifyDOUTchannel(dout):
    assert ((dout>=0) and (dout<=7)),"Digital output channel value out of range. Must be in the range of 0 to 7"
    
def VerifyDINchannel(din):
    assert ((din>=0) and (din<=7)),"Digital input channel value out of range. Must be in the range of 0 to 7"

def VerifyFGchannel(chan):
    assert ((chan>=1) and (chan<=4)),"Function Generator channel value out of range. Must be in the range of 1 to 4"
    
def ppCMD(addr,cmd,param1,param2,bytes2return):
    global DAQC2baseADDR
    global DataGood
    DataGood=True
    arg = list(range(4))
    resp = []
    arg[0]=addr+DAQC2baseADDR;
    arg[1]=cmd;
    arg[2]=param1;
    arg[3]=param2;
    GPIO.output(ppFRAME,True)
    null=spi.xfer(arg,500000,5)
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
                dummy=spi.xfer([00],500000,5)
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
    
def getADDR(addr):
    global DAQC2baseADDR
    resp=ppCMD(addr,0x00,0,0,1)
    #print resp, DataGood;
    if (DataGood):
        return resp[0]-DAQC2baseADDR
    else:
        return 8
    
def quietPoll():   
    global daqc2sPresent
    ppFoundCount=0
    for i in range (0,8):
        daqc2sPresent[i]=0
        rtn = getADDR(i)
        if (rtn==i):           
            daqc2sPresent[i]=1
            ppFoundCount += 1
            getCalVals(i)
            #RESET(i)


# Function to pull calibration data from flash memory
# data consists of 16 signed integers with each integer pair stored as:
# slope0,offset0,DACslope0,slope1,offset1,DACslope1,...slope7,offset,DACslope7    
# note that DACslope4 thru 7 are simply placeholders    
def getCalVals(addr):
    global calScale
    global calOffset
    values=list(range(6))
    for i in range(8):
        for j in range(6):
            values[j]=CalGetByte(addr,6*i+j)
        cSign=values[0]&0x80
        calScale[addr][i]=0.04*((values[0]&0x7F)*256+values[1])/32767   #16 bit signed slope calibration values - range is +/-4%
        if (cSign != 0):
            calScale[addr][i] *= -1
        calScale[addr][i]+=1    
        cSign=values[2]&0x80
        calOffset[addr][i]=0.2*((values[2]&0x7F)*256+values[3])/32767   #16 bit signed offset calibration values - range is +/- 0.1
        if (cSign != 0):
            calOffset[addr][i] *= -1
        cSign=values[4]&0x80
        calDAC[addr][i]=0.04*((values[4]&0x7F)*256+values[5])/32767  #16 bit signed DAC calibration values - range is +/-4%
        if (cSign != 0):
            calDAC[addr][i] *= -1
        calDAC[addr][i] += 1            

def RESET(addr):
    VerifyADDR(addr)
    resp=ppCMD(addr,0x0F,0,0,0)    
    time.sleep(.10)

quietPoll()    
