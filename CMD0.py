import spidev
import time
import sys
import RPi.GPIO as GPIO
import subprocess
import os

#Initialize
if (sys.version_info < (3,0,0)):
    sys.stderr.write("You need python 3 to use this library")
    exit(1)

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
ADCbaseADDR=64
ppFRAME = 25
ppINT = 22
ppACK = 23
#ppSW = 24

GPIO.setup(ppFRAME,GPIO.OUT)
GPIO.output(ppFRAME,False)  #Initialize FRAME signal
time.sleep(.001)            #let Pi-Plate reset SPI engine if necessary
GPIO.setup(ppINT, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(ppACK, GPIO.IN, pull_up_down=GPIO.PUD_UP)
#GPIO.setup(ppSW, GPIO.IN, pull_up_down=GPIO.PUD_UP)

drMAP=[5,6,13,19,26,21,20,16]
dedSRQ=8*[0]

try:
    spi = spidev.SpiDev()
    spi.open(0,1)
except:
    print("Did you enable the SPI hardware interface on your Raspberry Pi?")
    print("Go to https://pi-plates.com/getting_started/ and learn how.")
    
def enDedicated(addr):
    GPIO.setup(drMAP[addr], GPIO.IN, pull_up_down=GPIO.PUD_UP)

def disDedicated(addr):
    try:
        GPIO.cleanup(drMAP[addr])
        #dedSRQ[addr].release()
        dedSRQ[addr]=0
    except:
        pass

def getDedicated(addr):
    try:
        stat=False
        if (GPIO.input(drMAP[addr])==0):
            stat=True
        return stat
    except:
        return False
    
def getSRQ():
    if (GPIO.input(ppINT)==1):
        val=False
    else:
        val=True
    return val

def CLOSE():
    spi.close()
    GPIO.cleanup()
    
def ppCMD1(addr,cmd,param1,param2,bytes2return):
    #global GPIObaseADDR
    arg = list(range(4))
    resp = []
    arg[0]=addr;
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
  
def ppCMD2(addr,cmd,param1,param2,bytes2return):
    global DataGood
    DataGood=True
    arg = list(range(4))
    resp = []
    arg[0]=addr;
    arg[1]=cmd;
    arg[2]=param1;
    arg[3]=param2;
    GPIO.output(ppFRAME,True)       #Set FRAME high - tell Pi-Plates to start listening
    null=spi.xfer(arg,500000,5)     #Send out 4 byte command - ignore what comes back 
    DataGood=True
    t0=time.time()
    wait=True
    while(wait):
        if (GPIO.input(ppACK)!=1):  #wait 50msec for the addressed DAQC2 to ACKnowledge command
            wait=False
        if ((time.time()-t0)>0.05):   #timeout
            wait=False
            DataGood=False    
    if (bytes2return>0) and DataGood:   #If DAQC2 is supposed to send data AND no timeout occurred
        t0=time.time()
        wait=True
        while(wait):
            if (GPIO.input(ppACK)!=1):  #Ensure that ACK is still low before collecting data             
                wait=False
            if ((time.time()-t0)>0.08): #timeout
                wait=False
                DataGood=False
        if (DataGood==True):            #if ACK is still low AND there was no timeout then fetch data
            #time.sleep(.0001)
            for i in range(0,bytes2return+1):	#Fetch each byte. That [00] is simply a single element list set to zero
                dummy=spi.xfer([00],500000,5)   #That [00] is simply a single element list set to zero
                resp.append(dummy[0])           
            csum=0;                             
            for i in range(0,bytes2return):     #calculate and verify checksum
                csum+=resp[i]
            if ((~resp[bytes2return]& 0xFF) != (csum & 0xFF)):
                DataGood=False
    GPIO.output(ppFRAME,False)
    t0=time.time()
    wait=True
    while(wait):
        if (GPIO.input(ppACK)==1):  #wait 50msec for the addressed DAQC2 to ACKnowledge command
            wait=False
        if ((time.time()-t0)>0.05):   #timeout
            wait=False
            DataGood=False    
    #time.sleep(.00001)       #added for the RPi5 which is damn fast. DAQC2plate would sometimes miss FRAME going from high to low
    return resp
    
def getID1(addr):
    id=""
    arg = list(range(4))
    resp = []
    arg[0]=addr;
    arg[1]=0x1;
    arg[2]=0;
    arg[3]=0;
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

def getID2(addr):
    id=""
    arg = list(range(4))
    resp = []
    arg[0]=addr;
    arg[1]=0x1;
    arg[2]=0;
    arg[3]=0;
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
        if ((~checkSum & 0xFF) != (csum & 0xFF)):
            DataGood=False
    GPIO.output(ppFRAME,False)
    t0=time.time()
    wait=True
    while(wait):
        if (GPIO.input(ppACK)==1):  #wait 50msec for the addressed DAQC2 to ACKnowledge command
            wait=False
        if ((time.time()-t0)>0.05):   #timeout
            wait=False
            DataGood=False    
    #time.sleep(.00001)       #added for the RPi5 which is damn fast. DAQC2plate would sometimes miss FRAME going from high to low
    return id
    
def ppCMDADC(addr,cmd,param1,param2,bytes2return,slow=None):
    global DataGood
    if (slow==None):
        tOut=0.05
    else:
        tOut=3.0
    arg = list(range(4))
    resp = [0]*(bytes2return+1)
    arg[0]=addr;
    arg[1]=cmd;
    arg[2]=param1;
    arg[3]=param2;
    DataGood=True
    wait=True
    t0=time.time()
    while(wait):
        if (GPIO.input(ppACK)!=0):
            wait=False
        if ((time.time()-t0)>0.05):   #timeout
            wait=False
            DataGood=False
    GPIO.output(ppFRAME,True)
    time.sleep(0.000001)     #allow the uP some time to initialize the SPI
    spi.xfer(arg,400000,0)
    t0=time.time()
    wait=True
    while(wait):
        if (GPIO.input(ppACK)!=1):
            wait=False
        if ((time.time()-t0)>tOut):   #timeout
            wait=False
            DataGood=False
    if (bytes2return>0) and DataGood:
        time.sleep(0.000001)     #allow the uP some time to initialize the SPI
        t0=time.time()
        wait=True
        while(wait):
            if (GPIO.input(ppACK)!=1):
                wait=False
            if ((time.time()-t0)>0.1):   #timeout
                wait=False
                DataGood=False
        if (DataGood==True):
            resp=spi.xfer([0]*(bytes2return+1),4000000,0)   #don't exceed 4Mhz
            csum=0;
            for i in range(0,bytes2return+1):
                csum+=resp[i]
            if ((csum & 0xFF) != 0xFF):
                DataGood=False
    GPIO.output(ppFRAME,False)
    t0=time.time()
    wait=True
    while(wait):
        if (GPIO.input(ppACK)==1):  #wait 50msec for the addressed DAQC2 to ACKnowledge command
            wait=False
        if ((time.time()-t0)>0.05):   #timeout
            wait=False
            DataGood=False    
    #time.sleep(0.000001)     #allow the uP some time to close SPI engine
    return resp
    
def ppCMDosc(addr,cmd,param1,param2,bytes2return):
    global DataGood
    DataGood=True
    arg = list(range(4))
    resp = [0]*(bytes2return)
    N=bytes2return>>6
    #print(bytes2return,N)
    arg[0]=addr;
    arg[1]=cmd;
    arg[2]=param1;
    arg[3]=param2;
    GPIO.output(ppFRAME,True)            #Set FRAME high - tell Pi-Plates to start listening
    null=spi.xfer(arg,500000,5)     #Send out 4 byte command - ignore what comes back 
    DataGood=True
    t0=time.time()
    wait=True
    while(wait):
        if (GPIO.input(ppACK)!=1):         #wait 50msec for the addressed DAQC2 to ACKnowledge command
            wait=False
        if ((time.time()-t0)>0.05):   #timeout
            wait=False
            DataGood=False    
    if (bytes2return>0) and DataGood:   #If DAQC2 is supposed to send data AND no timeout occurred
        t0=time.time()
        wait=True
        while(wait):
            if (GPIO.input(ppACK)!=1):  #Ensure that ACK is still low before collecting data             
                wait=False
            if ((time.time()-t0)>0.08): #timeout
                wait=False
                DataGood=False
        if (DataGood==True):            #if ACK is still low AND there was no timeout then fetch data
            for i in range(N):          # bug in RPi5 SPIDEV limits block transfers to 64 bytes            
                resp[i*64:i*64+63]=spi.xfer([0]*(64),2000000) 
                #print(len(resp))
    GPIO.output(ppFRAME,False)
    t0=time.time()
    wait=True
    while(wait):
        if (GPIO.input(ppACK)==1):  #wait 50msec for the addressed DAQC2 to ACKnowledge command
            wait=False
        if ((time.time()-t0)>0.05):   #timeout
            wait=False
            DataGood=False    
    #time.sleep(.00001)                  #added for the RPi5 which is damn fast. DAQC2plate would sometimes miss FRAME going from high to low
    return resp
    
def fetchBLOCK(addr,cmd,param1,param2,bytes2return):
    global DataGood
    blockBYTES=[0]*bytes2return
    REM=bytes2return&0x3F
    N=bytes2return>>6
    
    arg = list(range(4))
    arg[0]=addr
    arg[1]=cmd;
    arg[2]=param1;
    arg[3]=param2;
    DataGood=True
    wait=True
    t0=time.time()
    while(wait):
        if (GPIO.input(ppACK)!=0):  #Ensure that ACK is high before proceeding
            wait=False
        if ((time.time()-t0)>0.05):   #timeout
            wait=False
            DataGood=False
    GPIO.output(ppFRAME,True)       #Set the FRAME signal high
    time.sleep(0.000001)       #allow the uP some time to initialize the SPI
    spi.xfer(arg,500000,0)     #Send the fetch command
    t0=time.time()
    wait=True
    while(wait):
        if (GPIO.input(ppACK)==0):  #wait until the command is received and ACKnowledged
            wait=False
        if ((time.time()-t0)>0.05):   #timeout
            wait=False
            DataGood=False
    if DataGood:
        time.sleep(0.000001)     #allow the uP some time to initialize the SPI
        if(N>0):
            for i in range(N):          # bug in RPi5 SPIDEV limits block transfers to 64 bytes            
                blockBYTES[i*64:i*64+63]=spi.xfer3([0x55]*64,4000000,0)
            if (REM != 0):
                blockBYTES[N*64:N*64+(REM-1)]=spi.xfer3([0x55]*REM,4000000,0)
        else:
            if (REM != 0):
                blockBYTES[0:(REM-1)]=spi.xfer3([0x55]*REM,4000000,0)
    GPIO.output(ppFRAME,False)
    t0=time.time()
    wait=True
    while(wait):
        if (GPIO.input(ppACK)==1):  #wait 50msec for the addressed DAQC2 to ACKnowledge command
            wait=False
        if ((time.time()-t0)>0.05):   #timeout
            wait=False
            DataGood=False    
    #time.sleep(.00001)          #added for the RPi5 which is damn fast. DAQC2plate would sometimes miss FRAME going from high to low    
    return list(blockBYTES)