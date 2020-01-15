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
MOTORbaseADDR=16
ppFRAME = 25
ppINT = 22
GPIO.setup(ppFRAME,GPIO.OUT)
GPIO.setup(ppINT, GPIO.IN, pull_up_down=GPIO.PUD_UP)
spi = spidev.SpiDev()
spi.open(0,1)	
localPath=site.getsitepackages()[0]
helpPath=localPath+'/piplates/MOTORhelp.txt'
#helpPath='MOTORhelp.txt'
MPversion=1.4
# Version 1.4 - made help() function compatible with Python 2 and 3. Fixed getID function
# Version 1.3 - adjusted timing on command functions to compensate for RPi SPI changes
RMAX = 2000
MAXADDR=8
motorsPresent = list(range(8))

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
                    print(s[:len(s)-1])
                    Count = Count + 1
                    if (Count==20):
                        Input=raw_input('press \"Enter\" for more...')                        
                else:
                    Count=100
                    valid=False
        f.close()
    except IOError:
        print ("Can't open help file.")

def Version():
    print('MOTORplate Python Module Version '+str(MPversion))

    
#==============================================================================#	
# Stepper Motor Functions	                                                   #
#==============================================================================#    
def stepperCONFIG(addr,motor,dir,resolution,rate,acceleration):
    if (addr>=MAXADDR):
        return "ERROR: address out of range - must be less than", MAXADDR-1
    motor=motor.lower()
    if ((motor!='a') and (motor!='b')):
        return "ERROR: incorrect stepper motor selection"   
    dir=dir.lower()
    if ((dir!='ccw') and (dir!='cw')):
        return "ERROR: incorrect direction parameter" 
    resolution=parseRES(resolution)
    if ((resolution>3) or (resolution<0)):
        return "ERROR: incorrect resolution value"
    if ((rate>RMAX) or (rate<1)):
        return "ERROR: incorrect rate value" 
    if ((acceleration>10) or (acceleration<0)):
        return "ERROR: incorrect acceleration time"         
    ## Param1:|0|DIR|RES1|RES2|NA|RATE10|RATE9|RATE8|        
    param1=0
    if dir=='cw':
        param1=0x40
    param1=param1+(resolution<<4)
    param1=param1+(rate>>8)
    ## Param2:|RATE7-RATE0|     
    param2=rate & 0x00FF
    cmd=0x10
    if (motor=='b'):
        cmd=0x11
    ppCMDm(addr,cmd,param1,param2,0)  
    time.sleep(.001)   ##Allow uP on board time to process 
    ## Send 2nd set of parameters but with same command numbers 
    ## to add acceleration increment. This is a 15 bit number with the upper
    ## 5 bits being the integer value and the lower 10 bits being the fractional
    ## part
    if (acceleration==0):
        increment=0
    else:
        increment=int(1024*rate/(acceleration*RMAX)+0.5)
    ## Param1:|1|ACC14|ACC13|ACC12|ACC11|ACC10|ACC9|ACC10| 
    param1=0x80+(increment>>8)
    param2=increment & 0x00FF
    cmd=0x10
    if (motor=='b'):
        cmd=0x11
    ppCMDm(addr,cmd,param1,param2,0) 
    time.sleep(.0001)   ##Allow uP on board time to process 
    
    
def stepperMOVE(addr,motor,steps):
    if (addr>=MAXADDR):
        return "ERROR: address out of range - must be less than", MAXADDR-1        
    motor=motor.lower()
    if ((motor!='a') and (motor!='b')):
        return "ERROR: incorrect motor selection"  
    if (steps>65535):
        return "ERROR: step count greater than 65,535"
    cmd=0x12
    if (motor=='b'):
        cmd=0x13    
    param1 = steps>>8
    param2 = steps&0xFF
    ppCMDm(addr,cmd,param1,param2,0)
#    time.sleep(.001)   ##Allow uP on board time to process 
    
    
def stepperJOG(addr,motor):
    if (addr>=MAXADDR):
        return "ERROR: address out of range - must be less than", MAXADDR-1
    motor=motor.lower()
    if ((motor!='a') and (motor!='b')):
        return "ERROR: incorrect motor selection"   
    cmd=0x14
    if (motor=='b'):
        cmd=0x15  
    ppCMDm(addr,cmd,0,0,0)
#    time.sleep(.001)   ##Allow uP on board time to process 
    
 
def stepperSTOP(addr,motor):
    if (addr>=MAXADDR):
        return "ERROR: address out of range - must be less than", MAXADDR-1
    motor=motor.lower()
    if ((motor!='a') and (motor!='b')):
        return "ERROR: incorrect motor selection" 
    cmd=0x16
    if (motor=='b'):
        cmd=0x17  
    ppCMDm(addr,cmd,0,0,0)

def stepperRATE(addr,motor,rate):    ## function to change step rate of jogging or stopped stepper
    if (addr>=MAXADDR):
        return "ERROR: address out of range - must be less than", MAXADDR-1
    motor=motor.lower()
    if ((motor!='a') and (motor!='b')):
        return "ERROR: incorrect motor selection" 
    if ((rate>RMAX) or (rate<1)):
        return "ERROR: incorrect rate value" 
    ## Param1:|0|0|0|0|0|RATE10|RATE9|RATE8|
    param1=(rate>>8)
    ## Param2:|RATE7-RATE0|     
    param2=rate & 0x00FF       
    cmd=0x18
    if (motor=='b'):
        cmd=0x19  
    ppCMDm(addr,cmd,param1,param2,0)
#    time.sleep(.001)   ##Allow uP on board time to process 
   
def stepperOFF(addr,motor):
    if (addr>=MAXADDR):
        return "ERROR: address out of range - must be less than", MAXADDR-1
    motor=motor.lower()
    if ((motor!='a') and (motor!='b')):
        return "ERROR: incorrect motor selection" 
    cmd=0x1E
    if (motor=='b'):
        cmd=0x1F  
    ppCMDm(addr,cmd,0,0,0)
   
def parseRES(res):
    if (isinstance(res,Number)):
        return res
    res=res.lower()
    if (res=='f'):
        return 0
    if (res=='h'):
        return 1    
    if (res=='m4'):
        return 2
    if (res=='m8'):
        return 3   
    return -1    
#==============================================================================#	
# DC Motor Functions	                                                       #
#==============================================================================#     
def dcCONFIG(addr,motor,dir,speed,acceleration):
    if (addr>=MAXADDR):
        return "ERROR: address out of range - must be less than", MAXADDR-1
    if ((motor<1) or (motor>4)):
        return "ERROR: incorrect DC motor selection. Must be between 1 and 4."   
    dir=dir.lower()
    if ((dir!='ccw') and (dir!='cw')):
        return "ERROR: incorrect direction parameter. Must be ''cw'' or ''ccw''." 
    if ((speed>100)or(speed<0)):
        return "ERROR: speed out of range. Must be between 0 and 100"    
    if ((acceleration>10) or (acceleration<0)):
        return "ERROR: incorrect acceleration time"   
       
    speed = int((speed*1023/100)+0.5)  
    if ((motor==1)or(motor==2)):
        speed=(speed*5)>>3
    ## Param1:|motor num 1|motor num 0|NA|direction|NA|NA|dc9|dc8|     
    param1=(motor-1)<<6
    if dir=='cw':
        param1=param1+0x10
    param1=param1+(speed>>8)
    param2= speed & 0x00FF
    ppCMDm(addr,0x30,param1,param2,0)  
    time.sleep(.001)   ##Allow uP on board time to process 
    ## Send 2nd set of parameters but with same command numbers 
    ## to add acceleration increment. This is a 15 bit number with the upper
    ## 5 bits being the integer value and the lower 10 bits being the fractional
    ## part
    if (acceleration==0):
        increment=0
    else:
        increment=int(1024*speed/(acceleration*RMAX)+0.5)
    ## Param1:|0|ACC14|ACC13|ACC12|ACC11|ACC10|ACC9|ACC10| 
    param1=(increment>>8)
    param2=increment & 0x00FF
    ppCMDm(addr,0x3A+(motor-1),param1,param2,0)
    time.sleep(.001)   ##Allow uP on board time to process
    
def dcSPEED(addr,motor,speed):
    if (addr>=MAXADDR):
        return "ERROR: address out of range - must be less than", MAXADDR-1
    if ((motor<1) or (motor>4)):
        return "ERROR: incorrect DC motor selection. Must be between 1 and 4."   
    if ((speed>100)or(speed<0)):    
        return "ERROR: speed out of range. Must be between 0 and 100" 
    speed = int((speed*1023/100)+0.5)  
    if ((motor==1) or (motor==2)):
        speed=(speed*5)>>3
    ## Param1:|motor num 1|motor num 0|NA|direction|NA|NA|dc9|dc8|     
    param1=(motor-1)<<6
    param1=param1+(speed>>8)
    param2= speed & 0x00FF       
    ppCMDm(addr,0x33,param1,param2,0)    
        
def dcSTART(addr,motor):
    if (addr>=MAXADDR):
        return "ERROR: address out of range - must be less than", MAXADDR-1
    if ((motor<1) or (motor>4)):
        return "ERROR: incorrect DC motor selection" 
    ppCMDm(addr,0x31,motor-1,0,0)
        
def dcSTOP(addr,motor):
    if (addr>=MAXADDR):
        return "ERROR: address out of range - must be less than", MAXADDR-1
    if ((motor<1) or (motor>4)):
        return "ERROR: incorrect DC motor selection" 
    ppCMDm(addr,0x32,motor-1,0,0)
    
#==============================================================================#	
# Sensor Functions	                                                           #
#==============================================================================#    
def getSENSORS(addr):
    if (addr>=MAXADDR):
        return "ERROR: address out of range - must be less than", MAXADDR-1
    resp=ppCMDm(addr,0x20,0,0,1)
    return resp[0]        
        
def getTACHcoarse(addr,tachnum):
    if (addr>=MAXADDR):
        return "ERROR: address out of range - must be less than", MAXADDR-1
    if ((tachnum>4) or (tachnum<1)):
        return "ERROR: tachometer number must be between 1 and 4."
    resp=ppCMDm(addr,0x22,tachnum,0,2)
    return resp[0]*256+resp[1]

def getTACHfine(addr,tachnum):
    if (addr>=MAXADDR):
        return "ERROR: address out of range - must be less than", MAXADDR-1
    if ((tachnum>4) or (tachnum<1)):
        return "ERROR: tachometer number must be between 1 and 4."
    resp=ppCMDm(addr,0x23,tachnum,0,2)
    return resp[0]*256+resp[1]

#==============================================================================#	
# LED Functions	                                                               #
#==============================================================================#   
def setLED(addr):
	if (addr>MAXADDR):
		return "ERROR: address out of range - must be less than", MAXADDR-1
	resp=ppCMDm(addr,0x60,0,0,0)

def clrLED(addr):
	if (addr>MAXADDR):
		return "ERROR: address out of range - must be less than", MAXADDR-1	
	resp=ppCMDm(addr,0x61,0,0,0)

def toggleLED(addr):
	if (addr>MAXADDR):
		return "ERROR: address out of range - must be less than", MAXADDR-1	
	resp=ppCMDm(addr,0x62,0,0,0)

     
#==============================================================================#	
# Interrupt Control Functions	                                               #
#==============================================================================#	
def intEnable(addr):	#MOTORplate will pull down on INT pin if an enabled event occurs
	if (addr>MAXADDR):
		return "ERROR: address out of range - must be less than", MAXADDR-1
	resp=ppCMDm(addr,0x04,0,0,0)
	
def intDisable(addr):
	if (addr>MAXADDR):
		return "ERROR: address out of range - must be less than", MAXADDR-1
	resp=ppCMDm(addr,0x05,0,0,0)
	
def getINTflag0(addr):	            #read INT flag register0 in MOTORplate
    if (addr>MAXADDR):
        return "ERROR: address out of range - must be less than", MAXADDR-1
    resp=ppCMDm(addr,0x06,0,0,1)
    return resp[0]  
    
def getINTflag1(addr):	            #read INT flag register1 in MOTORplate
    if (addr>MAXADDR):
        return "ERROR: address out of range - must be less than", MAXADDR-1
    resp=ppCMDm(addr,0x07,0,0,1)
    return resp[0] 

def setSENSORint(addr,sensor):
    if (addr>MAXADDR):
        return "ERROR: address out of range - must be less than", MAXADDR-1
    if ((sensor>4) or (sensor<1)):
        return "ERROR: sensor number must be between 1 and 4."
    ppCMDm(addr,0x24,sensor,0,0)        

def clrSENSORint(addr,sensor):
    if (addr>MAXADDR):
        return "ERROR: address out of range - must be less than", MAXADDR-1
    if ((sensor>4) or (sensor<1)):
        return "ERROR: sensor number must be between 1 and 4."
    ppCMDm(addr,0x25,sensor,0,0)
    
def enablestepSTOPint(addr,motor):   #enable the interrupt at the end of a move
    if (addr>=MAXADDR):
        return "ERROR: address out of range - must be less than", MAXADDR-1
    motor=motor.lower()
    if ((motor!='a') and (motor!='b')):
        return "ERROR: incorrect motor selection" 
    cmd=0x1A
    if (motor=='b'):
        cmd=0x1B 
    ppCMDm(addr,cmd,0,0,0)

def disablestepSTOPint(addr,motor):   #disable the interrupt at the end of a move
    if (addr>=MAXADDR):
        return "ERROR: address out of range - must be less than", MAXADDR-1
    motor=motor.lower()
    if ((motor!='a') and (motor!='b')):
        return "ERROR: incorrect motor selection"   
    cmd=0x1C
    if (motor=='b'):
        cmd=0x1D 
    ppCMDm(addr,cmd,0,0,0)

def enablestepSTEADYint(addr,motor):   #enable interrupt when speed is stable
    if (addr>=MAXADDR):
        return "ERROR: address out of range - must be less than", MAXADDR-1
    motor=motor.lower()
    if ((motor!='a') and (motor!='b')):
        return "ERROR: incorrect motor selection" 
    cmd=0x4A
    if (motor=='b'):
        cmd=0x4B 
    ppCMDm(addr,cmd,0,0,0)

def disablestepSTEADYint(addr,motor):   #disable the interrupt when speed is stable
    if (addr>=MAXADDR):
        return "ERROR: address out of range - must be less than", MAXADDR-1
    motor=motor.lower()
    if ((motor!='a') and (motor!='b')):
        return "ERROR: incorrect motor selection"   
    cmd=0x4C
    if (motor=='b'):
        cmd=0x4D 
    ppCMDm(addr,cmd,0,0,0)

def enabledcSTOPint(addr,motor):   #enable the interrupt at the end of a move
    if (addr>=MAXADDR):
        return "ERROR: address out of range - must be less than", MAXADDR-1
    if ((motor<1) or (motor>4)):
        return "ERROR: incorrect DC motor selection" 
    ppCMDm(addr,0x34,motor-1,0,0)

def disabledcSTOPint(addr,motor):   #disable the interrupt at the end of a move
    if (addr>=MAXADDR):
        return "ERROR: address out of range - must be less than", MAXADDR-1
    if ((motor<1) or (motor>4)):
        return "ERROR: incorrect DC motor selection" 
    ppCMDm(addr,0x35,motor-1,0,0)

def enabledcSTEADYint(addr,motor):   #enable interrupt when speed is stable
    if (addr>=MAXADDR):
        return "ERROR: address out of range - must be less than", MAXADDR-1
    if ((motor<1) or (motor>4)):
        return "ERROR: incorrect DC motor selection" 
    ppCMDm(addr,0x36,motor-1,0,0)

def disabledcSTEADYint(addr,motor):   #disable the interrupt when speed is stable
    if (addr>=MAXADDR):
        return "ERROR: address out of range - must be less than", MAXADDR-1
    if ((motor<1) or (motor>4)):
        return "ERROR: incorrect DC motor selection" 
    ppCMDm(addr,0x37,motor-1,0,0)

#==============================================================================#	
# System Functions	                                                           #
#==============================================================================#	    
def Poll():
    ppFoundCount=0
    for i in range (0,8):
        rtn = getADDR(i)
        if (rtn==i):
            print("MOTORplate found at address",rtn)
            ppFoundCount += 1
    if (ppFoundCount == 0):
        print("No MOTORplates found")    

def quietPoll():   
    global motorsPresent
    ppFoundCount=0
    for i in range (0,8):
        motorsPresent[i]=0
        rtn = getADDR(i)
        if (rtn==i):
            motorsPresent[i]=1
            ppFoundCount += 1
       
        
def getID(addr):
    global MOTORbaseADDR
    addr=addr+MOTORbaseADDR
    if (addr>255):
        return "ERROR: address out of range - must be less than 255"
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
    time.sleep(.01)
    while (count<20): 
        dummy=spi.xfer([00],300000,20)
        dummy=spi.xfer([00],300000,20)
        if (dummy[0] != 0):
            num = dummy[0]
            id = id + chr(num)
            count = count + 1
        else:
            count=20
    GPIO.output(ppFRAME,False)
    return id

def getHWrev(addr):
    global MOTORbaseADDR
    if (addr>MAXADDR):
        return "ERROR: address out of range - must be less than", MAXADDR-1
    resp=ppCMDm(addr,0x02,0,0,1)
    rev = resp[0]
    whole=float(rev>>4)
    point = float(rev&0x0F)
    return whole+point/10.0	 
    
def getFWrev(addr):
    global MOTORbaseADDR
    if (addr>MAXADDR):
        return "ERROR: address out of range - must be less than", MAXADDR-1
    resp=ppCMDm(addr,0x03,0,0,1)
    rev = resp[0]
    whole=float(rev>>4)
    point = float(rev&0x0F)
    return whole+point/10.0

def getVersion():
    return MPversion    
    
def getADDR(addr):
    global MOTORbaseADDR
    if (addr>MAXADDR):
        return "ERROR: address out of range - must be less than", MAXADDR-1
    resp=ppCMDm(addr,0x00,0,0,1)
    return resp[0]-MOTORbaseADDR
    
def RESET(addr):
    global MOTORbaseADDR
    if (addr>MAXADDR):
        return "ERROR: address out of range - must be less than", MAXADDR-1
    resp=ppCMDm(addr,0x0F,0,0,0)    
    time.sleep(.10)
    
def ppCMDm(addr,cmd,param1,param2,bytes2return):
    global MOTORbaseADDR
    arg = list(range(4))
    resp = []
    arg[0]=addr+MOTORbaseADDR;
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

quietPoll()    