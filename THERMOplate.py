import spidev
import time
import string
import site
import sys
import math
from numbers import Number
import RPi.GPIO as GPIO
from six.moves import input as raw_input
GPIO.setwarnings(False)

#Initialize
if (sys.version_info < (2,7,0)):
    sys.stderr.write("You need at least python 2.7.0 to use this library")
    exit(1)
    
GPIO.setmode(GPIO.BCM)
THERMObaseADDR=40
ppFRAME = 25
ppINT = 22
ppACK = 23
GPIO.setup(ppFRAME,GPIO.OUT)
GPIO.output(ppFRAME,False)  #Initialize FRAME signal
time.sleep(.001)            #let Pi-Plate reset SPI engine if necessary
GPIO.setup(ppINT, GPIO.IN, pull_up_down=GPIO.PUD_UP)    #Initialize SRQ input and ACK
GPIO.setup(ppACK, GPIO.IN, pull_up_down=GPIO.PUD_UP)
spi = spidev.SpiDev()
spi.open(0,1)	
localPath=site.getsitepackages()[0]
helpPath=localPath+'/piplates/THERMOhelp.txt'
#helpPath='THERMOhelp.txt'       #for development only
THERMOversion=1.3
#1.0 - initial release
#1.1 - added line frequency options
#1.2 - added data smoothing options
#1.3 - fixed coefficients in type K conversion polynomial for T>500C. 

DataGood=False
#tType='k'   #Default thermocouple is type K

RMAX = 2000
MAXADDR=8
kTc=[[0 for z in range(3)] for x in range(10)]    #Type K thermocouple coefficients. Found at: https://www.keysight.com/upload/cmc_upload/All/5306OSKR-MXD-5501-040107_2.htm?&amp&cc=HK&lc=eng
#kTc[n]=[c0, c1, c2, c3, c4, c5, c6, c7, c8, c9]
kTc[0]=[0,2.5173462E01,-1.1662878,-1.0833638,-8.9773540E-01,-3.7342377E-01,-8.6632643E-02,-1.0450598E-02,-5.1920577E-04,0]
kTc[1]=[0,2.508355E01,7.860106E-02,-2.503131E-01,8.315270E-02,-1.228034E-02,9.804036E-04,-4.413030E-05,1.0577340E-06,-1.052755E-08]
kTc[2]=[-1.318058E02,4.830222E01,-1.646031,5.464731E-02,-9.650715E-04,8.802193E-06,-3.110810E-08,0,0,0]
# Voltage:	            -5.891 mV to 0 mV   0 mV to 20.644 mV   20.644 to 54.886mV
# Temperature:	            -200C to 0C	        0C to 500C	       500C to 1372C
# Coefficient Index:              0                1                    3

#Coefficients to convert temperature to Type K voltage (in millivolts)
kTcj=[-1.7600413686E-02, 3.8921204975E-02, 1.8558770032E-05, -9.9457592874E-08, 3.1840945719E-10, -5.6072844889E-13, 5.6075059059E-16, -3.2020720003E-19, 9.7151147152E-23, -1.2104721275E-26]

jTc=[[0 for z in range(3)] for x in range(9)]    #Type J thermocouple coefficients. Found at: https://www.keysight.com/upload/cmc_upload/All/5306OSKR-MXD-5501-040106_2.htm
#jTc[n]=[c0, c1, c2, c3, c4, c5, c6, c7, c8]
jTc[0]=[0,1.9528268E1,-1.2286185,-1.0752178,-5.9086933E-01,-1.7256713E-01,-2.8131513E-02,-2.3963370E-03,-8.3823321E-05]
jTc[1]=[0,1.978425E01,-2.001204E-01,1.036969E-02,-2.549687E-04,3.585153E-06,-5.344285E-08,5.099890E-10,0]
jTc[2]=[-3.1135818702E03,3.00543684E02,-9.94773230,1.70276630E-01,-1.43033468E-03,4.73886084E-06,0,0,0]
# Voltage:	            -8.095 mV to 0 mV   0 mV to 42.919 mV   42.919 to 54.00mV
# Temperature:	            -210C to 0C	        0C to 760C	       760C to 934C
# Coefficient Index:              0                1                    3

#Coefficients to convert temperature to Type J voltage (in millivolts)
jTcj=[0, 5.0381187815E-02, 3.0475836930E-05, -8.5681065720E-08, 1.3228195295E-10, -1.7052958337E-13, 2.0948090697E-16, -1.2538395336E-19, 1.5631725697E-23]


#Global Declarations
THERMOsPresent = list(range(8))
calScale=[[0 for z in range(8)] for x in range(8)]   #24 bit floating point slope calibration values
calOffset=[[0 for z in range(8)] for x in range(8)]  #24 bit floating point offset calibration values
calBias=[0,0,0,0,0,0,0,0]
calSet=list(range(8))
tempScale='c'

tType=[['k' for z in range(8)] for x in range(8)] #Default thermocouple is type K

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
 
def getTEMP(addr,channel,scale=None):
    global tempScale
    VerifyADDR(addr)
    assert ((channel>=1) and (channel<=12)),"Channel value out of range. Must be a value between 1 and 12"
    if scale is None:
        scal=tempScale
    else:
        scal=scale.lower()
        assert ((scal=='c') or (scal=='f') or (scal=='k')), "Temperature scale must be 'c', 'f', or 'k'."
    channel-=1;
    Tvals=[[0],[0]]
    resp=ppCMD(addr,0x70,channel,0,4)   #initiate measurement
    Tvals[0]=resp[0]*256+resp[1]        #T channel data
    Tvals[1]=resp[2]*256+resp[3]        #Cold junction value
    if channel>7:
        Temp=Tvals[0]
        if (Temp>0x8000):
            Temp = Temp^0xFFFF
            Temp = -(Temp+1)
        Temp = Temp/16.0
        if (scal=='k'):
            Temp = Temp + 273.15
        if (scal=='f'):
            Temp = Temp*1.8+32.0
    else:
        CJtemp=Tvals[1]*2400.0/65535.0  #convert cold junction reading to voltage
        CJtemp=(10.888-math.sqrt((10.888**2.0)+4*0.00347*(1777.3-CJtemp)))/(2*(-0.00347))+30.0  #convert cold junction voltage to temperature
        Vcj=0
        if (tType[addr][channel]=='k'):
            for i in range(10):
                Vcj+=kTcj[i]*(CJtemp**i)     #Convert cold junction temperature to Type K voltage
            #print Vcj
            #Convert thermocouple A2D measurement to voltage and apply calibration values
            Vmeas=((Tvals[0]*2.4/65535.0)-calOffset[addr][channel])/calScale[addr][channel]*1000   # convert thermocouple A/D value to a voltage (in millivolts)
            Vhot=Vmeas+Vcj-calBias[addr]*1000.0 #Add cold junction voltage and subtract Vbias from measured voltage

            k=1
            if (Vhot<0):
                k=0
            if (Vhot>20.644):
                k=2
            Temp=0
            for i in range(10):             #convert adjusted measured thermocouple voltage to temperature
                Temp+=kTc[k][i]*(Vhot**i) 
        else:
            for i in range(9):
                Vcj+=jTcj[i]*(CJtemp**i)     #Convert cold junction temperature to Type J voltage
            #Convert thermocouple A2D measurement to voltage and apply calibration values
            Vmeas=((Tvals[0]*2.4/65535.0)-calOffset[addr][channel])/calScale[addr][channel]*1000   # convert thermocouple A/D value to a voltage (in millivolts)
            Vhot=Vmeas+Vcj-calBias[addr]*1000.0 #Add cold junction voltage and subtract Vbias from measured voltage
            #print Vhot, Vmeas, Vcj, calBias[addr]
            k=1
            if (Vhot<0):
                k=0
            if (Vhot>42.919):
                k=2
            Temp=0
            
            for i in range(9):             #convert adjusted measured thermocouple voltage to temperature
                Temp+=jTc[k][i]*(Vhot**i)    
                #print k, jTc[k][i], Temp
        if scal!='c':
            if scal=='f':
                Temp=Temp*1.8+32.0
            else:
                Temp+=273.15
    Temp=round(Temp,3)
    return Temp

def getCOLD(addr,scale=None):
    global tempScale
    VerifyADDR(addr)
    if scale is None:
        scal=tempScale
    else:
        scal=scale.lower()
        assert ((scal=='c') or (scal=='f') or (scal=='k')), "Temperature scale must be 'c', 'f', or 'k'."
    channel=0;
    Tvals=[[0],[0]]
    resp=ppCMD(addr,0x70,channel,0,4)   #initiate measurement
    Tvals[1]=resp[2]*256+resp[3]        #Cold junction value - discard thermocouple measurement
    CJtemp=Tvals[1]*2400.0/65535.0      #convert cold junction reading to voltage
    CJtemp=(10.888-math.sqrt((10.888**2.0)+4*0.00347*(1777.3-CJtemp)))/(2*(-0.00347))+30.0  #convert cold junction voltage to temperature
    if scal!='c':
        if scal=='f':
            CJtemp=CJtemp*1.8+32.0
        else:
            CJtemp+=273.15
    CJtemp=round(CJtemp,3)
    return CJtemp

def getRAW(addr,channel):
    global tType
    VerifyADDR(addr)
    assert ((channel>=1) and (channel<=8)),"Channel value out of range. Must be a value between 1 and 8"
    channel-=1
    Tvals=[[0],[0]]
    resp=ppCMD(addr,0x70,channel,0,4) #initiate measurement
    Tvals[0]=resp[0]*256+resp[1]        #T channel data
    Tvals[1]=resp[2]*256+resp[3]        #Cold junction value    
    Vmeas=((Tvals[0]*2.4/65535.0)-calOffset[addr][channel])/calScale[addr][channel]*1000   # convert thermocouple A/D value to a voltage (in millivolts)
    Vraw=Vmeas-calBias[addr]*1000.0 #subtract Vbias from measured voltage   
    #print Tvals[0]*2.4/65535.0, Vmeas, calBias[addr]*1000.0
    return Vraw
    
def setSCALE(scale):
    global tempScale
    scal=scale.lower()
    assert ((scal=='c') or (scal=='f') or (scal=='k')), "Temperature scale must be 'c', 'f', or 'k'."
    tempScale=scal
    
def getSCALE():
    global tempScale
    return tempScale
    
def setTYPE(addr,chan,type):
    VerifyADDR(addr)
    assert ((chan>=1) and (chan<=8)),"Thermocouple channel value out of range. Must be a value between 1 and 8"
    type=type.lower()
    assert ((type=='k') or (type=='j')), "Thermocouple type must be 'k' or 'j'"
    tType[addr][chan-1]=type 
    
def getTYPE(addr,chan):
    VerifyADDR(addr)
    assert ((chan>=1) and (chan<=8)),"Thermocouple channel value out of range. Must be a value between 1 and 8"
    return tType[addr][chan-1]
    
    
def setLINEFREQ(addr,freq):
    VerifyADDR(addr)
    assert ((freq==50) or (freq==60)),"Frequency value out of range. Must be a either 50 or 60"
    resp=ppCMD(addr,0x73,freq,0,0)
    
def setSMOOTH(addr):
    VerifyADDR(addr)
    resp=ppCMD(addr,0x74,1,0,0)
    
def clrSMOOTH(addr):
    VerifyADDR(addr)
    resp=ppCMD(addr,0x74,0,0,0)    

#===============================================================================#	
# Interrupt Functions	                                                   		    #
#===============================================================================#	
def setINTchannel(addr, channel):	# enable interrupt at end of temperature measurement
    VerifyADDR(addr)
    assert ((channel>=1) and (channel<=12)),"Channel value out of range. Must be a value between 1 and 12"	
    channel-=1;
    resp=ppCMD(addr,0x71,channel,0,0)

def intEnable(addr):	#THERMOplate will pull down on INT pin if an enabled event occurs
    VerifyADDR(addr)
    resp=ppCMD(addr,0x04,0,0,0)
	
def intDisable(addr):   #THERMOplate will not assert interrupts
    VerifyADDR(addr)
    resp=ppCMD(addr,0x05,0,0,0)
    
def getINTflags(addr):	#read INT flag register in THERMOplate - this clears interrupt line and the register
    VerifyADDR(addr)
    resp=ppCMD(addr,0x06,0,0,1)
    return resp[0]
    
#===============================================================================#	
# LED Functions	                                                   		   		#
#===============================================================================#			
def setLED(addr):
    VerifyADDR(addr)
    resp=ppCMD(addr,0x60,0,0,0)

def clrLED(addr):
    VerifyADDR(addr)
    resp=ppCMD(addr,0x61,0,0,0)

def toggleLED(addr):
    VerifyADDR(addr)
    resp=ppCMD(addr,0x62,0,0,0)	

def getLED(addr):
    VerifyADDR(addr)
    resp=ppCMD(addr,0x63,0,0,1)
    return resp[0]	

        
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
    return THERMOversion   

def setINT(addr):
    VerifyADDR(addr)
    resp=ppCMD(addr,0xF4,0,0,0)

def clrINT(addr):
    VerifyADDR(addr)
    resp=ppCMD(addr,0xF5,0,0,0)
	
def getID(addr):
    global THERMObaseADDR
    VerifyADDR(addr)
    addr=addr+THERMObaseADDR
    id=""
    arg = list(range(4))
    resp = []
    arg[0]=addr;
    arg[1]=0x1;
    arg[2]=0;
    arg[3]=0;
    DataGood=True
    t0=time.time()
    wait=True
    while(wait):
        if (GPIO.input(ppACK)==1):              
            wait=False
        if ((time.time()-t0)>0.05):   #timeout
            wait=False
            DataGood=False
    if (DataGood==True): 
        ppFRAME = 25
        GPIO.output(ppFRAME,True)
        null=spi.xfer(arg,500000,50)
        #DataGood=True
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
                    count += 1
                else:
                    dummy=spi.xfer([00],500000,40)  
                    checkSum=dummy[0]                
                    go=False 
                if (count>25):
                    go=False
                    DataGood=False
            if ((~checkSum & 0xFF) != (csum & 0xFF)):
                DataGood=False
        GPIO.output(ppFRAME,False)
    return id   
 
 
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
def VerifyADDR(addr):
    assert ((addr>=0) and (addr<MAXADDR)),"THERMOplate address out of range"
    addr_str=str(addr)
    assert (THERMOsPresent[addr]==1),"No THERMOplate found at address "+addr_str
    
def ppCMD(addr,cmd,param1,param2,bytes2return):
    global THERMObaseADDR
    global DataGood
    DataGood=True
    arg = list(range(4))
    resp = []
    arg[0]=addr+THERMObaseADDR;
    arg[1]=cmd;
    arg[2]=param1;
    arg[3]=param2;
    DataGood=True
    t0=time.time()
    wait=True    
    while(wait):
        if (GPIO.input(ppACK)==1):              
            wait=False
        if ((time.time()-t0)>0.05):   #timeout
            wait=False
            DataGood=False
    if (DataGood==True):
        ppFRAME = 25    
        GPIO.output(ppFRAME,True)
        null=spi.xfer(arg,500000,5)
        #DataGood=True
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
                for i in range(0,bytes2return+1):	
                    dummy=spi.xfer([00],500000,5)
                    resp.append(dummy[0])
                csum=0;
                for i in range(0,bytes2return):
                    csum+=resp[i]
                if ((~resp[bytes2return]& 0xFF) != (csum & 0xFF)):
                    DataGood=False
        GPIO.output(ppFRAME,False)
    return resp

def verifyTC(addr,channel):
    VerifyADDR(addr)
    assert ((channel>=0) and (channel<=7)),"Channel value out of range. Must be a value between 1 and 13"
    scal=scale.lower()
    Tvals=[[0],[0]]
    resp=ppCMD(addr,0x70,channel,0,4)   #initiate measurement
    Tvals[0]=resp[0]*256+resp[1]        #T channel data
    Tvals[1]=resp[2]*256+resp[3]        #Cold junction value
    #Convert thermocouple measurement to voltage and apply calibration
    Vmeas=((calScale[addr][channel]*Tvals[0]*2.4/65535.0)/37.5-(0.01*calOffset[addr][channel]))*1000   # convert thermocouple A/D value to a voltage (in millivolts)
    return Vmeas
    
def getADDR(addr):
    global THERMObaseADDR
    resp=ppCMD(addr,0x00,0,0,1)
    if (DataGood):
        return resp[0]-THERMObaseADDR
    else:
        return 8
    
def quietPoll():   
    global THERMOsPresent
    ppFoundCount=0
    for i in range (0,8):
        THERMOsPresent[i]=0
        rtn = getADDR(i)
        if (rtn==i):           
            THERMOsPresent[i]=1
            ppFoundCount += 1
            getCalVals(i)
            #RESET(i)

#Function to convert from binary 32bit number to floating point            
def Binary2Cal(valList):
    polarity=1
    expsign=1
    val=valList[0]
    for i in range(3):
        val = val << 8
        val += valList[i+1]
    if (val & (2**31)) != 0:
        polarity = -1
    exp=((val>>24)&0x7F)-64
    if (exp<0):
        expsign=-1
    val=val&((2**24)-1)
    frac=float(val)/float(((2**24)-1))*expsign
    CalVal=math.pow(10,exp+frac)*polarity
    return CalVal                     
            
# Function to pull calibration data from flash memory
# data consists of 17 signed 32 bit floating point numbers stored as:
# |sign|7 bit exponent (-64 to 63)|24 bit mantissa normalized to (2^24-1)|
# Data is saved as Bias Voltage, offset0, slope0, offset1, slope1 ...offset7, slope7      
def getCalVals(addr):
    global calScale
    global calOffset
    global calBias
    values=list(range(4))
    for j in range(4):
        values[j]=CalGetByte(addr,j)    #get bias voltage
    calBias[addr]=Binary2Cal(values)
    for i in range(8):
        for j in range(4):
            values[j]=CalGetByte(addr,8*i+j+4)
        calOffset[addr][i]=Binary2Cal(values)
        for j in range(4,8):
            values[j-4]=CalGetByte(addr,8*i+j+4)          
        calScale[addr][i]=Binary2Cal(values)        
    
def RESET(addr):
    VerifyADDR(addr)
    resp=ppCMD(addr,0x0F,0,0,0)
    time.sleep(.10)

quietPoll()