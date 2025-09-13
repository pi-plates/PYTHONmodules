#==============================================================================#	
# BASIC I/O Functions	                                                       #
#==============================================================================#          
import time
import spidev
import RPi.GPIO as GPIO

baseADDR=48
ppNAME='TINKERplate'

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
baseADDR=48
MAXADDR=8
ppFRAME = 25
ppINT = 22
ppACK = 23
GPIO.setup(ppFRAME,GPIO.OUT)
GPIO.output(ppFRAME,False)  #Initialize FRAME signal
time.sleep(.001)            #pause to let Pi-Plate reset SPI HW if necessary
GPIO.setup(ppINT, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(ppACK, GPIO.IN, pull_up_down=GPIO.PUD_UP)
try:
    spi = spidev.SpiDev()
    spi.open(0,1)
except:
    print("Did you enable the SPI hardware interface on your Raspberry Pi?")
    print("Go to https://pi-plates.com/getting_started/ and learn how.")

DataGood=False
platesPresent = list(range(8))

def VerifyADDR(addr):
    assert ((addr>=0) and (addr<MAXADDR)),ppNAME+" address out of range"
    addr_str=str(addr)
    assert (platesPresent[addr]==1),"No "+ppNAME+" found at address "+addr_str
    
def VerifyCHAN(chan):
    assert ((chan>=1) and (chan<9)),"Invalid channel number - must be between 1 and 8"
  
def ppCMD(addr,cmd,param1,param2,bytes2return):
    global baseADDR
    global DataGood
    DataGood=True
    arg = list(range(4))
    resp = []
    arg[0]=addr+baseADDR;
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

def getID(addr):
    global baseADDR
    VerifyADDR(addr)
    addr=addr+baseADDR
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
            #print checkSum, ~checkSum & 0xFF, csum & 0xFF
            if ((~checkSum & 0xFF) != (csum & 0xFF)):
                DataGood=False
        GPIO.output(ppFRAME,False)
    return id   
    
def getADDR(addr):
    global baseADDR
    resp=ppCMD(addr,0x00,0,0,1)
    #print resp, DataGood;
    if (DataGood):
        return resp[0]-baseADDR
    else:
        return 8
    
def quietPoll():   
    global platesPresent
    ppFoundCount=0
    for i in range (0,8):
        platesPresent[i]=0
        rtn = getADDR(i)
        if (rtn==i):           
            platesPresent[i]=1
            ppFoundCount += 1
        
def RESET(addr):
    VerifyADDR(addr)
    resp=ppCMD(addr,0x0F,0,0,0)
    time.sleep(.10)