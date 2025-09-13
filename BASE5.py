#==============================================================================#	
# BASIC I/O Functions	                                                       #
#==============================================================================#          
import time
import spidev
import gpiod
   
FRAME = 25
ACK = 23
SRQ = 22

try:
    chip=gpiod.Chip('gpiochip4')
except:
    chip=gpiod.Chip('gpiochip0')
       
ppFRAME=chip.get_line(FRAME)
ppSRQ=chip.get_line(SRQ)
ppACK=chip.get_line(ACK)
ppFRAME.request(consumer="Frame", type=gpiod.LINE_REQ_DIR_OUT)
ppSRQ.request(consumer="SRQ", type=gpiod.LINE_REQ_DIR_IN, flags=gpiod.LINE_REQ_FLAG_BIAS_PULL_UP)
ppACK.request(consumer="ACK", type=gpiod.LINE_REQ_DIR_IN, flags=gpiod.LINE_REQ_FLAG_BIAS_PULL_UP)
#ppACK.request(consumer="ACK", type=gpiod.LINE_REQ_DIR_IN)
ppFRAME.set_value(0)

spi = spidev.SpiDev()
spi.open(0,1)
baseADDR=48

baseADDR=48
ppNAME='TINKERplate'
MAXADDR=8

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
    # t0=time.time()
    # wait=True    
    # while(wait):
        # if (ppACK.get_value()!=1):              
            # wait=False
        # if ((time.time()-t0)>0.05):   #timeout
            # wait=False
            # DataGood=False
    # if (DataGood==True): 
    ppFRAME.set_value(1)       #Set FRAME high - tell Pi-Plates to start listening
    null=spi.xfer(arg,500000,5)
    #DataGood=True
    t0=time.time()
    wait=True
    while(wait):
        if (ppACK.get_value()!=1):
            wait=False
        if ((time.time()-t0)>0.05):   #timeout
            wait=False
            DataGood=False    
    if (bytes2return>0) and DataGood:
        t0=time.time()
        wait=True
        while(wait):
            if (ppACK.get_value()!=1):              
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
    ppFRAME.set_value(0)
    time.sleep(.00001)       #added for the RPi5 which is damn fast. DAQC2plate would sometimes miss FRAME going from high to low
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
    ppFRAME.set_value(1)
    null=spi.xfer(arg,500000,50)
    DataGood=True
    t0=time.time()
    wait=True
    while(wait):
        if (ppACK.get_value()!=1):              
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
    ppFRAME.set_value(0)
    time.sleep(.00001)       #added for the RPi5 which is damn fast. DAQC2plate would sometimes miss FRAME going from high to low
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
        #print(rtn)
        if (rtn==i):           
            platesPresent[i]=1
            ppFoundCount += 1
        
def RESET(addr):
    VerifyADDR(addr)
    resp=ppCMD(addr,0x0F,0,0,0)
    time.sleep(.10)