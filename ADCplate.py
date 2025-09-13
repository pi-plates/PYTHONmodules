import time
import site
import sys
import os
#import CMD
#import gpiod
import subprocess
import threading

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
    sys.stderr.write("This library is only compatible with Python 3")
    exit(1)

ADCbaseADDR=64

Vref=2.5
FSR=25

#chip=gpiod.Chip('gpiochip4')
#drMAP=[5,6,13,19,26,21,20,16]

if (sys.base_prefix == sys.prefix):
    result = subprocess.run(['pip', 'show', 'Pi-Plates'], stdout=subprocess.PIPE)
    result=result.stdout.splitlines()
    result=str(result[7],'utf-8')
    k=result.find('/home')
    result=result[k:]
else:
    result=site.getsitepackages()[0]
helpPath=result+'/piplates/ADChelp.txt'
#helpPath='ADChelp.txt'       #for development only

ADCversion=2.0
#   Revision 1 - initial release
#   Revision 2 - updated to support RPi5


#DataGood=False
lock = threading.Lock()
lock.acquire()

RMAX = 2000
MAXADDR=8
SHARED=0
DEDICATED=1


adcsPresent = list(range(8))
chanTYPE=[[256 for z in range(16)] for x in range(8)]       #character to indicate sample rate for each channel
chanENABLE=[[False for z in range(16)] for x in range(8)]   #enable status for each channel
trigENABLED=[False for z in range(8)]
assignedSETUP=[[0xFF for z in range(8)] for x in range(8)]

#lastTYPE=['v' for z in range(8)]
ADCbusy=[False for z in range(8)]
ADCerr=[0 for z in range(8)]
blockSIZE=[0 for z in range(8)]
streamSIZE=[0 for z in range(8)]
streamMODE=[False for z in range(8)]
blockMODE=[False for z in range(8)]
blockBYTES=[0]*8192*4
blockVALS=[0]*8192
blockCHANS=[0]*8192
srLIST=[5 for z in range(8)]
modeLIST=[1 for z in range(8)]
scanLIST=[0 for z in range(8)]
srqSOURCE=[SHARED for z in range(8)]
srqLINE=[SHARED for z in range(8)]

def CLOSE():
    spi.close()


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
                        input('press \"Enter\" for more...')
                else:
                    Count=100
                    valid=False
        f.close()
    except IOError:
        print ("Can't find help file.")

def setMODE(addr,mode):
    global ADCbusy, modeLIST
    modeindex=['SLOW', 'MED', 'FAST', 'ADV','HIGH','MED','LOW','ADV']
    if (VerifyADDR(addr) == 0):
        return
    if(ADCbusy[addr]!=False):
        print("You cannot change mode while ADCplate is busy with a measurement.")
        #sys.exit()
    else:
        if (isinstance(mode, str) and mode.isalpha()):
            mode=mode.upper()
        else:
            print("Not a valid mode. Mode arguments can be 'SLOW', 'MEDium', 'FAST', or 'ADVanced'")
            print("Or mode arguments can be 'HIGH', 'MEDium', 'LOW', or 'ADVanced'")
            return            
        if (mode!='SLOW' and mode!='FAST' and mode[:3]!='MED' and mode[:3]!='ADV' and mode!='HIGH' and mode!='LOW'):
            print("Not a valid mode. Mode arguments can be 'SLOW', 'MEDium', 'FAST', or 'ADVanced'" )
            print("Or mode arguments can be 'HIGH', 'MEDium', 'LOW', or 'ADVanced'")            
            return
        ppCMD(addr,0x3B,modeindex.index(mode)%4,0,0)
        if (mode[:3]=='ADV'):
            enableEVENTS(addr)
            getEVENTS(addr)
        else:
            disableEVENTS(addr)
            getEVENTS(addr)
        modeLIST[addr]=modeindex.index(mode)%4

def getMODE(addr):
    if (VerifyADDR(addr) == 0):
        return
    resp=ppCMD(addr,0x3C,0,0,1)
    modeLIST[addr]=resp[0]
    return resp[0]


#==============================================================================#
# Begin A2D Functions - configuration
#==============================================================================#
#enableINPUT(addr,input,SR)
# input - the ADCplate supports 16 inputs labeled S0 thru S7, D0 thru D3, and I0 thru I3
#         numeric values of 00-15 can be used as well
# sampleRate(sr) - each channel can have unique sampling rate with values from
#                  0 to 18. The characteristics of each of these values is shown
#                  below:
# SR    ODR Fdata  Ts(msec)    Fmux(Hz)    fc (Hz)  50Hz Rej 60Hz Rej Venb   Ienb   Filter
# 0     22  1.25    2400        1.25        0.3     -125.63 -130.43   22.7    24      3
# 1     21  2.5     1200        2.5         0.6     -108.66 -113.49   22.7    24      3
# 2     20  5       600         5           1.3     -103.09 -107.92   22.4    24      3
# 3     19  10      300         10          2.6     -101.71 -106.52   22.4    24      3
# 4     NA  16.667  60          16.67       ~10     -90     -90       21.9    24      5
# 5     NA  20      50          20.00       ~10     -85     -85       21.8    24      5
# 6     NA  25      40          25.00       ~10     -62     -62       21.6    23.6    5
# 7     16  50      60          49.68       12.8    -100.76 -46.95    21.8    23.7    3
# 8     15  59.98   50.02       59.52       15.4    -40.34  -105.8    21.6    23.6    3
# 9     14  100.2   10          100.20      44.2    NA      NA        21.3    20.6    5
# 10    13  200.3   5           200.30      89.5    NA      NA        20.6    20.1    5
# 11    12  381     2.63        380.95      174.4   NA      NA        20.2    19.9    5
# 12    11  504     1.99        503.8       234.0   NA      NA        19.9    19.4    5
# 13    10  1007    0.993       1007.00     502     NA      NA        19.5    18.8    5
# 14    9   2597    0.385       2597.00     1664.0  NA      NA        18.7    18.0    5
# 15    8   5208    0.321       3115        2182    NA      NA        18.3    17.9    5
# 16    7   10417   0.225       4444        3933    NA      NA        17.9    17.4    5
# 17    6   15625   0.193       5181        5150    NA      NA        17.7    17.2    5
# 18    5   31250   0.161       6211       6750    NA      NA        17.5    17.0    5
#=======================================================================================#

def srTable():
    print('=================================================================')
    print('SR Fdata  Ts(msec) Fmux(Hz) fc (Hz)  50Hz Rej 60Hz Rej Venb Ienb ')
    print('0  1.25    2400     1.25     0.3     -125.63 -130.43   22.7  24  ')
    print('1  2.5     1200     2.5      0.6     -108.66 -113.49   22.7  24  ')
    print('2  5       600      5        1.3     -103.09 -107.92   22.4  24  ')
    print('3  10      300      10       2.6     -101.71 -106.52   22.4  24  ')
    print('4  16.667  60       16.67    ~10     -90     -90       21.9  24  ')
    print('5  20      50       20.00    ~10     -85     -85       21.8  24  ')
    print('6  25      40       25.00    ~10     -62     -62       21.6  23.6')
    print('7  50      60       49.68    12.8    -100.76 -46.95    21.8  23.7')
    print('8  59.98   50.02    59.52    15.4    -40.34  -105.8    21.6  23.6')
    print('9  100.2   10       100.20   44.2      NA      NA      21.3  20.6')
    print('10 200.3   5        200.30   89.5      NA      NA      20.6  20.1')
    print('11 381     2.63     380.95   174.4     NA      NA      20.2  19.9')
    print('12 504     1.99     503.8    234.0     NA      NA      19.9  19.4')
    print('13 1007    0.993    1007.00  502       NA      NA      19.5  18.8')
    print('14 2597    0.385    2597.00  1664.0    NA      NA      18.7  18.0')
    print('15 5208    0.321    3115     2182      NA      NA      18.3  17.9')
    print('16 10417   0.225    4444     3933      NA      NA      17.9  17.4')
    print('17 15625   0.193    5181     5150      NA      NA      17.7  17.2')
    print('18 31250   0.161    6211     6750      NA      NA      17.5  17.0')
    print('=================================================================')


def configINPUT(addr,input,sampleRate,enable=None):
    global chanENABLE
    global chanTYPE
    global assignedSETUP
    global ADCbusy
    global modeLIST
    if (VerifyADDR(addr) == 0):
        return
    if (modeLIST[addr] != 3):
        print ('This command is only valid for ADVanced mode.')
        return
    if (ADCbusy[addr]==True):
        print("Command ignored - this ADCplate is busy with a measurement.")
        return
    if ((sampleRate < 0) or (sampleRate > 18)):
        print('Command ignored - the sample rate argument must be between 0 and 18.')
        return
    cCheck=verifyInput(input)
    cTypes=['S0','S1','S2','S3','S4','S5','S6','S7','D0','D1','D2','D3','I0','I1','I2','I3']
    mux=cTypes[cCheck]
    #chanTYPE[addr][cCheck]=mux+'-'+str('{:02d}'.format(sampleRate))   #local copy of channel configuration
    chanTYPE[addr][cCheck]=sampleRate  #local copy of channel sample rate
    if (enable==None):
        enable=chanENABLE[addr][cCheck]
    else:
        if(enable!=True and enable!=False):
            print ('Command ignored - the optional enable argument must be "True" or "False".')
            return
    if (enable):
        if (setupCOUNT(addr)>7):
            print ('Command ignored - the maximum enabled channel count (8) exceeded.')
            return
        chanENABLE[addr][cCheck]=enable
        setup=getSETUP(addr,cCheck)<<4
        eARG=3
    else:
        eARG=2
        setup=0xF0
    #muxSelect=cCheck #this is the mux selection value to to send to the ADC
    ppCMD(addr,0x39, setup+cCheck,(eARG<<5)+sampleRate,0)

def enableINPUT(addr,input):
    global chanENABLE
    global ADCbusy,modeLIST
    if (VerifyADDR(addr) == 0):
        return
    if (ADCbusy[addr]==True):
        print("Command ignored - this ADCplate is busy with a measurement.")
        return
    if (modeLIST[addr] != 3):
        print ('This command is only valid for ADVanced mode.')
        return
    cCheck=verifyInput(input)
    if (setupCOUNT(addr)>7):
        print ('Command ignored - the maximum enabled channel count (8) exceeded.')
        return
    setup=getSETUP(addr,cCheck)<<4
    chanENABLE[addr][cCheck]=True
    ppCMD(addr,0x39,setup+cCheck,(1<<5),0)


def disableINPUT(addr,input):
    global chanENABLE
    global ADCbusy, modeLIST
    if (VerifyADDR(addr) == 0):
        return
    if (ADCbusy[addr]==True):
        print("Command ignored - this ADCplate is busy with a measurement.")
        return
    if (modeLIST[addr] != 3):
        print ('This command is only valid for ADVanced mode.')
        return
    cCheck=verifyInput(input)
    clrSETUP(addr,cCheck)
    chanENABLE[addr][cCheck]=False
    ppCMD(addr,0x39,0xF0+cCheck,(0<<5),0)

def verifyInput(mux):
    #global chanTYPE
    if (isinstance(mux,int)):
        assert (mux<16), 'Invalid input value - must be between 0 and 15.'
        cNum=mux
    else:
        assert (len(mux)==2 and mux[0].isalpha() and mux[1].isdigit()), 'Invalid input argument - must be S0-S7, D0-D3, or I0-I3.'
        mux=mux[0].upper()+mux[1]
        cType=mux[0]
        assert (cType=='S' or cType=='D' or cType=='I'), 'Invalid input type - must be S0-S7, D0-D3, or I0-I3.'
        cNum=int(mux[1])
        if (cType=='S'):
            assert ((cNum >= 0) and (cNum <=7)), 'Only single ended input numbers 0 through 7 are valid'
            #chan=cNum
        if (cType=='D'):
            assert ((cNum >= 0) and (cNum <=3)), 'Only differential input numbers 0 through 3 are valid'
            cNum=8+cNum
        if (cType=='I'):
            assert ((cNum >= 0) and (cNum <=3)), 'Only current input numbers 0 through 3 are valid'
            cNum=12+cNum
    return cNum

def initADC(addr):
    global chanENABLE, ADCbusy, streamMODE, trigENABLED, modeLIST
    if (VerifyADDR(addr) == 0):
        return
    ppCMD(addr,0x3A,0,0,0)
    for i in range(16):
        chanENABLE[addr][i]=False
    for i in range(8):
        assignedSETUP[addr][i]=0xFF
    ADCbusy[addr]=False
    streamMODE[addr]=False
    trigENABLED[addr]=False
    modeLIST[addr] = 1
    disableEVENTS(addr)
    time.sleep(0.01)
    

def getSETUP(addr,chan):
    global assignedSETUP
    #first check to see if channel has already been assigned a setup
    i=0
    search=True
    while(search and (i<8)):
        if (assignedSETUP[addr][i]==chan):
            search=False
        else:
            i=i+1
    #if i==8 then channel has not already been assigned a setup so find the next available one
    if (i==8):
        i=0
        search=True
        while(search and (i<8)):
            if (assignedSETUP[addr][i] == 0xFF):
                assignedSETUP[addr][i]=chan
                search=False
            else:
                i=i+1
    return i

def clrSETUP(addr,chan):
    global assignedSETUP
    i=0
    search=True
    while(search and (i<8)):
        if (assignedSETUP[addr][i]==chan):
            search=False
            assignedSETUP[addr][i]=0xFF
        else:
            i=i+1
    pass

def setupCOUNT(addr):
    global assignedSETUP
    count=0
    for i in range(8):
        if (assignedSETUP[addr][i]!=0xFF):
            count=count+1
    return count

#==============================================================================#
#ADC - read  modes and functions
#==============================================================================#
def getADC(addr,input):
    global ADCbusy, modeLIST, Vref
    cCheck=verifyInput(input)
    if (VerifyADDR(addr) == 0):
        return
    if (modeLIST[addr]==3):
        print("Command ignored - this function cannot be used in ADVanced mode")
        return
    resp=ppCMD(addr,0x30,cCheck,0,4)
    val=((resp[0])<<16)+(resp[1]<<8)+resp[2]
    assert(val<0xFFFFFF),'ADC error occurred'
    ADCerr[addr]=resp[3]
    if (cCheck<12):
        Vin=10*Vref*((val/8388608.0)-1)*FSR/25
    else:
        Vin=1000/50*Vref*val/16777216.0 #return current in mA
    ADCbusy[addr]=False
    return round(Vin,6)

def getADCall(addr):
    global Vref, modeLIST, blockSIZE, blockVALS, blockCHANS
    if (VerifyADDR(addr) == 0):
        return
    if (modeLIST[addr]==3):
        print("Command ignored - this function cannot be used in ADVanced mode")
        return       
    blockSIZE[addr]=16
    fetchBLOCK(addr,0x31,0,0,64)
    for i in range(blockSIZE[addr]):
        k=i<<2
        val=blockBYTES[k]<<16
        val += blockBYTES[k+1]<<8
        val += blockBYTES[k+2]
        lblockCHAN=blockBYTES[k+3] & 0x0F
        if (i<12):
            Vin=10.0*Vref*((val/8388608.0)-1)*FSR/25
        else:
            Vin=1000/50*Vref*val/16777216.0 #return current in mA
        blockVALS[i] = round(Vin,7)
        blockCHANS[i]=lblockCHAN
    return blockVALS[0:blockSIZE[addr]]

def getSall(addr):  #Only return the eight Single Ended inputs
    wholeBlock=16*[0]
    wholeBlock=getADCall(addr)
    return wholeBlock[:8]

def getDall(addr):  #Only return the four Differential inputs
    wholeBlock=16*[0]
    wholeBlock=getADCall(addr)    
    return wholeBlock[8:12]

def getIall(addr):  #Only return the four 4-30mA inputs
    wholeBlock=16*[0]
    wholeBlock=getADCall(addr)    
    return wholeBlock[12:16]
    
def readSINGLE(addr,input,sampleRate=None):
    #VerifyADDR(addr)
    global ADCbusy, modeLIST
    if (ADCbusy[addr]==True):
        print("Command ignored - this ADCplate is busy with a measurement.")
        return
    if (modeLIST[addr] != 3):
        print ('This command is only valid for ADVanced mode.')
        return
    cCheck=verifyInput(input)
    if (sampleRate==None):
        startSINGLE(addr,input)
    else:
        startSINGLE(addr,input,sampleRate)
    while(check4EVENTS(addr)==False):
        pass
    getEVENTS(addr) #clear the interrupt register
    return getSINGLE(addr,cCheck)

def startSINGLE(addr,input,sampleRate=None):
    global ADCbusy, modeLIST
    if (ADCbusy[addr]==True):
        print("Command ignored - this ADCplate is busy with a measurement.")
        return
    if (VerifyADDR(addr) == 0):
        return
    if (modeLIST[addr] != 3):
        print ('This command is only valid for ADVanced mode.')
        return
    cCheck=verifyInput(input)
    if (sampleRate!=None):
        assert ((sampleRate >= 0) and (sampleRate <= 18)), 'The sample rate argument must be between 0 and 18.'
        sr=sampleRate
    else:
        sr=0xFF
    ADCbusy[addr]=True
    ppCMD(addr,0x32,cCheck,sr,0)

def getSINGLE(addr,input):
    global ADCerr, Vref
    global ADCbusy, modeLIST
    #assert(ADCbusy[addr]==False), "This ADCplate is busy a another measurement."
    if (VerifyADDR(addr) == 0):
        return
    if (modeLIST[addr] != 3):
        print ('This command is only valid for ADVanced mode.')
        return
    cCheck=verifyInput(input)
    resp=ppCMD(addr,0x33,0,0,4,'s')
    val=((resp[0])<<16)+(resp[1]<<8)+resp[2]
    assert(val<0xFFFFFF),'ADC error occurred'
    ADCerr[addr]=resp[3]
    #Vref=2.5
    if (cCheck<12):
        Vin=10*Vref*((val/8388608.0)-1)*FSR/25
    else:
        Vin=1000/50*Vref*val/16777216.0 #return current in mA
    ADCbusy[addr]=False
    return round(Vin,6)

def readSCAN(addr):
    global ADCbusy, chanENABLE, modeLIST
    if (ADCbusy[addr]==True):
        print("Command ignored - this ADCplate is busy with a measurement.")
        return
    if (VerifyADDR(addr) == 0):
        return
    if (modeLIST[addr] != 3):
        print ('This command is only valid for ADVanced mode.')
        return
    N=0
    for i in range(16):
        if (chanENABLE[addr][i]==True):
            N=N+1
    if (N>0):
        startSCAN(addr)
        while(check4EVENTS(addr)==False):
            pass
        getEVENTS(addr) #clear the interrupt register
        return getSCAN(addr)
    else:
        chanVALS=[None for z in range(16)]
        return chanVALS

def startSCAN(addr,trig=None):
    global ADCbusy, blockSIZE, modeLIST,trigENABLED
    if (ADCbusy[addr]==True):
        print("Command ignored - this ADCplate is busy with a measurement.")
        return
    if (VerifyADDR(addr) == 0):
        return
    if (modeLIST[addr] != 3):
        print ('This command is only valid for ADVanced mode.')
        return
    assert ((trig==None) or (trig==True) or (trig==False)),"If used, the optional trig value should be True or False."
    trigFlag=0
    if (trig==True):
        assert(trigENABLED[addr]==True), "The trigger settings need to be configured before use."
        trigFlag=0x80
    ADCbusy[addr]=True
    N=0
    for i in range(16):
        if (chanENABLE[addr][i]==True):
            N=N+1
    blockSIZE[addr]=N
    if (N>0):
        ppCMD(addr,0x34,trigFlag,0,0)

def getSCAN(addr):
    global blockSIZE, chanENABLE, blockCHANS, modeLIST
    if (VerifyADDR(addr) == 0):
        return
    if (modeLIST[addr] != 3):
        print ('This command is only valid for ADVanced mode.')
        return
    vals=getBLOCK(addr)
    #print(vals)
    chanVALS=[None for z in range(16)]
    N=0
    for i in range(16):
        if (chanENABLE[addr][i]==True):
            N=N+1
    if (N>0):
        k=blockSIZE[addr]
        for i in range(k):
            chanVALS[blockCHANS[i]]=vals[i]
    return chanVALS

def startBLOCK(addr, num):
#def startBLOCK(addr, num, trig=None):
    global blockSIZE, blockMODE, ADCbusy, modeLIST
    if (VerifyADDR(addr) == 0):
        return
    if (modeLIST[addr] != 3):
        print ('This command is only valid for ADVanced mode.')
        return
    if (ADCbusy[addr]==True):
        print("Command ignored - this ADCplate is busy with a measurement.")
        return
    ADCbusy[addr]=True
    assert ((num<=8192) and (num>0)), 'Block size has to be between 1 and 8,192 samples'
    blockSIZE[addr]=num
    #blockMODE[addr]=True
    num=num-1
    param1=num>>8
    param2=num&0xFF
    #param1=param1 + trigFlag
    ppCMD(addr,0x35,param1,param2,0)


def startSTREAM(addr, num):
    global blockSIZE, streamMODE, ADCbusy, modeLIST
    if (VerifyADDR(addr) == 0):
        return
    if (modeLIST[addr] != 3):
        print ('This command is only valid for ADVanced mode.')
        return
    if (ADCbusy[addr]==True):
        print("Command ignored - this ADCplate is busy with a measurement.")
        return
    assert (streamMODE[addr]==False), "This ADCplate is already streaming data."
    assert ((num<=4096) and (num>0)), 'Block size for streaming has to be between 1 and 4,096 samples'
    blockSIZE[addr]=num
    streamMODE[addr]=True
    ADCbusy[addr]=True
    num=num-1
    param1=num>>8
    param2=num&0xFF
    ppCMD(addr,0x36,param1,param2,0)

def stopSTREAM(addr):
    global modeLIST
    if (VerifyADDR(addr) == 0):
        return
    if (modeLIST[addr] != 3):
        print ('This command is only valid for ADVanced mode.')
        return
    assert (streamMODE[addr]==True), 'This ADCplate is not currently in stream mode.'
    streamMODE[addr]=False
    ADCbusy[addr]=False
    ppCMD(addr,0x37,0,0,0)

def getSTREAM(addr):
    global blockSIZE
    global blockVALS
    global blockBYTES
    global blockMODE
    global modeLIST
    global blockCHANS
    if (VerifyADDR(addr) == 0):
        return
    if (modeLIST[addr] != 3):
        print ('This command is only valid for ADVanced mode.')
        return
    if (streamMODE[addr]==False):
        print ('This ADCplate is not currently in stream mode.')
        return
    num=blockSIZE[addr]
    num=num-1
    param1=num>>8
    param2=num&0xFF
    fetchBLOCK(addr,0x38,param1,param2,blockSIZE[addr]<<2)
    #SF.binWRITE(addr,bytes(blockBYTES[0:(blockSIZE[addr]<<2)]))
    for i in range(blockSIZE[addr]):
        k=i<<2
        val=blockBYTES[k]<<16
        val += blockBYTES[k+1]<<8
        val += blockBYTES[k+2]
        lblockCHAN=blockBYTES[k+3] & 0x0F
        #type=chanTYPE[addr][blockCHANS[i]]
        #type=type[0].lower()
        #lastTYPE[addr]=type
        if (lblockCHAN<12):
            Vin=10.0*Vref*((val/8388608.0)-1)*FSR/25
        else:
            Vin=1000/50*Vref*val/16777216.0 #return current in mA
        blockVALS[i] = round(Vin,6)
        blockCHANS[i]=lblockCHAN
    return blockVALS[0:blockSIZE[addr]]
    
def getBLOCK(addr):
    global blockSIZE
    global blockVALS
    global blockBYTES
    global blockMODE
    global blockCHANS
    global ADCbusy, Vref, modeLIST
    if (VerifyADDR(addr) == 0):
        return
    if (modeLIST[addr] != 3):
        print ('This command is only valid for ADVanced mode.')
        return
    if ((streamMODE[addr]==False) and (trigENABLED[addr]==False)):
        ADCbusy[addr]=False
    num=blockSIZE[addr]
    num=num-1
    param1=num>>8
    param2=num&0xFF
    #print (param1, param2, blockSIZE[addr])
    fetchBLOCK(addr,0x38,param1,param2,blockSIZE[addr]<<2)
    #blockMODE[addr]=False
    #Vref=2.5
    for i in range(blockSIZE[addr]):
        k=i<<2
        val=blockBYTES[k]<<16
        val += blockBYTES[k+1]<<8
        val += blockBYTES[k+2]
        lblockCHAN=blockBYTES[k+3] & 0x0F
        #type=chanTYPE[addr][blockCHANS[i]]
        #type=type[0].lower()
        #lastTYPE[addr]=type
        if (lblockCHAN<12):
            Vin=10.0*Vref*((val/8388608.0)-1)*FSR/25
        else:
            Vin=1000/50*Vref*val/16777216.0 #return current in mA
        blockVALS[i] = round(Vin,6)
        blockCHANS[i]=lblockCHAN
    return blockVALS[0:blockSIZE[addr]]

#==============================================================================#
# AD4112 Diagnostic Functions                                                  #
#==============================================================================#
def dumpCHANregs(addr,chan):
    global ADCbusy
    if (ADCbusy[addr]==True):
        print("Command ignored - this ADCplate is busy with a measurement.")
        return
    assert(chan >= 0 and chan <= 0xF), "invalid chan value"
    Channel=getADCreg(addr,0x10+chan)
    print ('CH'+str(chan)+':',hex(Channel))

    chan=(Channel>>12)&0x07

    # if (chan<8):
        # chan=chan>>1
    # else:
        # chan=chan-8
    Setup=getADCreg(addr,0x20+chan)
    print ('SETUPCON'+str(chan)+':',hex(Setup))
    Filter=getADCreg(addr,0x28+chan)
    print ('FILTCON'+str(chan)+':',hex(Filter))
    Offset=getADCreg(addr,0x30+chan)
    print ('OFFSET'+str(chan)+':',hex(Offset))
    Gain=getADCreg(addr,0x38+chan)
    print ('GAIN'+str(chan)+':',hex(Gain))
    Status=getADCreg(addr,0)
    print ('Status:',hex(Status))
    print ('-----------------')


#returns a single ADC register
def getADCreg(addr,reg):
    if (VerifyADDR(addr) == 0):
        return
    #assert(reg >= 0x10 and reg <= 0x3F), "invalid register address"
    if (reg==0):
        resp=ppCMD(addr,0x3E,reg,0,1)
        val=resp[0]
    if (reg>=0x10 and reg<0x30):
        resp=ppCMD(addr,0x3E,reg,0,2)
        val=(resp[0]<<8)+resp[1]
    if (reg>=0x30):
        resp=ppCMD(addr,0x3E,reg,0,4)
        val=(resp[1]<<16)+(resp[2]<<8)+resp[3]
    return val

#==============================================================================#
# Digital Input Functions                                                      #
#==============================================================================#
def getDINbit(addr,bit):
    if (VerifyADDR(addr) == 0):
        return
    assert ((bit>=0) and (bit<=4)),"DIN bit must be between 0 and 4"
    resp=ppCMD(addr,0x20,bit,0,1)
    if resp[0] > 0:
        return 1
    else:
        return 0
    pass

def getDINall(addr):
    if (VerifyADDR(addr) == 0):
        return
    resp=ppCMD(addr,0x25,0,0,1)
    return resp[0]

def enableDINevent(addr, bit):    # enable DIN interrupt
    if (VerifyADDR(addr) == 0):
        return
    assert ((bit>=0) and (bit<=3)),"DIN bit must be between 0 and 3"
    ppCMD(addr,0x21,bit,0,0)

def disableDINevent(addr,bit):    # disable DIN interrupt
    if (VerifyADDR(addr) == 0):
        return
    assert ((bit>=0) and (bit<=4)),"DIN bit must be between 0 and 4"
    ppCMD(addr,0x22,bit,0,0)

#===============================================================================#
# Event Functions                                                               #
#===============================================================================#
def enableEVENTS(addr,signal=None): #ADC will pull down on selected SRQ pin if an enabled event occurs
    global srqSOURCE
    global srqLINE
    global drMAP
    if (VerifyADDR(addr) == 0):
        return
    if (signal==None):
        signal=srqSOURCE[addr]
    else:
        if ((signal!=SHARED) and (signal!=DEDICATED)):
            print("Command ignore - signal value must be SHARED or DEDICATED")
            return
        if (signal==DEDICATED):
            #srqLINE[addr]=chip.get_line(drMAP[addr])
            #srqLINE[addr].request(consumer="SRQ"+str(addr), type=gpiod.LINE_REQ_DIR_IN, flags=gpiod.LINE_REQ_FLAG_BIAS_PULL_UP)
            #GPIO.setup(drMAP[addr], GPIO.IN, pull_up_down=GPIO.PUD_UP) 
            CMD.enDedicated(addr)
        srqSOURCE[addr]=signal
    ppCMD(addr,0x04,signal,0,0)

def disableEVENTS(addr):   #ADC will not assert interrupts on INT pin (GPIO22) if an enabled event occurs
    if (VerifyADDR(addr) == 0):
        return
    ppCMD(addr,0x05,0,0,0)
    CMD.disDedicated(addr)

def getEVENTS(addr):   #read INT flag register - this resets interrupt line and clears the register
    if (VerifyADDR(addr) == 0):
        return
    resp=ppCMD(addr,0x06,0,0,1)
    value=(resp[0])
    return value

# The ADCplate does not support the masking of interrupts - this must be done in SW.

def check4EVENTS(addr):
    global ADCbaseADDR
    global drMAP
    global srqLINE
    if (VerifyADDR(addr) == 0):
        return
    stat=False
    if (srqSOURCE[addr]==DEDICATED):
        stat=CMD.getDedicated(addr)
    else:
        stat = CMD.getSRQ()
    return stat

#==============================================================================#
# Trigger Functions - these functions work w/ Block and List ADC readings only #
#==============================================================================#
def configTRIG(addr,mode,primary=None):
    global modeLIST, trigENABLED
    if (VerifyADDR(addr) == 0):
        return
    if (modeLIST[addr] != 3):
        print ('This command is only valid for ADVanced mode.')
        return
    mode=mode.upper()
    if ((mode!='OFF') and (mode!='EXT') and  (mode!='SW') and (mode!='CLOCKED')):
        print('Command ignored -',mode,' is not a valid trigger mode.')
        return
    if (mode=='OFF'):
        disableTRIG(addr)
        ppCMD(addr,0x42,0,0,0)
        trigENABLED[addr]=False
    elif (mode=='EXT'):
        nmode=1
        ppCMD(addr,0x42,nmode,0,0)
        trigENABLED[addr]=True
    elif (mode=='SW'):
        trigENABLED[addr]=True
        nmode = 2
        if primary==True:
            nmode = nmode + 0x80
        ppCMD(addr,0x42,nmode,0,0)
    else:   #defaults to clocked mode
        trigENABLED[addr]=True
        nmode=3
        if primary==True:
            nmode = nmode + 0x80
        ppCMD(addr,0x42,nmode,0,0) #set for clocked internal trigger mode
                                   #default trigger frequency is 100Hz.

def startTRIG(addr):   #start trigger mode - must be used after trig configuration is set
    global modeLIST
    if (VerifyADDR(addr) == 0):
        return
    if (modeLIST[addr] != 3):
        print ('This command is only valid for ADVanced mode.')
        return
    if (trigENABLED[addr] != True):
        print ('The trigger settings have to be set before executing this function. See configTRIG.')
        return
    ppCMD(addr,0x41,0,0,0)
    startSCAN(addr,True)
    trigENABLED[addr]=True

def stopTRIG(addr):  #disable trigger mode
    global modeLIST
    if (VerifyADDR(addr) == 0):
        return
    if (modeLIST[addr] != 3):
        print ('This command is only valid for ADVanced mode.')
        return
    ppCMD(addr,0x40,0,0,0)
    trigENABLED[addr]=False

def triggerFREQ(addr,freq): #configure internal trigger clock and output a pulse if primary == True
    global modeLIST
    if (VerifyADDR(addr) == 0):
        return
    if (modeLIST[addr] != 3):
        print ('This command is only valid for ADVanced mode.')
        return
    assert (freq<=1000),'The internal frequency should not exceed 1000Hz'
    val=int(64000/freq)-1
    actualFreq=64000/(val+1)
    ppCMD(addr,0x44,val>>8,val&0xFF,0)
    return actualFreq

def swTRIGGER(addr):    #trigger ADC measurement and output a pulse if primary == True
    global modeLIST
    if (VerifyADDR(addr) == 0):
        return
    if (modeLIST[addr] != 3):
        print ('This command is only valid for ADVanced mode.')
        return
    ppCMD(addr,0x43,0,0,0)


def maxTRIGfreq(addr):
    global modeLIST
    global chanTYPE
    global chanENABLE
    singleCHANrates=[1.25,2.5,5,10,16.667,20,25,50,59.98,100.2,200.3,381,504,1007,2597,5208,10417,15625,31250]
    multiCHANrates=[1.25,2.5,5,10,16.667,20,25,49.68,59.52,100.2,200.3,380.95,503.8,1007,2597,3115,4444,5181,6211]
    if (VerifyADDR(addr) == 0):
        return
    if (modeLIST[addr] != 3):
        print ('This command is only valid for ADVanced mode.')
        return
    chanCount=0
    for i in range(16):
        if (chanENABLE[addr][i]==True):
            chanCount = chanCount+1
    if (chanCount==0):
        print ('No channels enabled yet.')
        return
    sTime=0
    for i in range(16):
        if (chanENABLE[addr][i]==True):
            if (chanCount<2):
                sTime=sTime+1/singleCHANrates[chanTYPE[addr][i]]
            else:
                sTime=sTime+1/multiCHANrates[chanTYPE[addr][i]]
    return 1.0/sTime
                
        
    

#==============================================================================#
# LED Functions                                                                #
#==============================================================================#
def setLED(addr):
    if (VerifyADDR(addr) == 0):
        return
    ppCMD(addr,0x60,0,0,0)

def clrLED(addr):
    if (VerifyADDR(addr) == 0):
        return
    ppCMD(addr,0x61,0,0,0)

def toggleLED(addr):
    if (VerifyADDR(addr) == 0):
        return
    ppCMD(addr,0x62,0,0,0)

def getLED(addr):
    if (VerifyADDR(addr) == 0):
        return
    resp=ppCMD(addr,0x63,0,0,1)
    return resp[0]

#==============================================================================#
# System Functions                                                             #
#==============================================================================#
def getFWrev(addr):
    if (VerifyADDR(addr) == 0):
        return
    resp=ppCMD(addr,0x03,0,0,1)
    rev = resp[0]
    whole=float(rev>>4)
    point = float(rev&0x0F)
    return whole+point/10.0

def getHWrev(addr):
    if (VerifyADDR(addr) == 0):
        return
    resp=ppCMD(addr,0x02,0,0,1)
    rev = resp[0]
    whole=float(rev>>4)
    point = float(rev&0x0F)
    return whole+point/10.0

def getVersion():
    return ADCversion

def setINT(addr):
    if (VerifyADDR(addr) == 0):
        return
    ppCMD(addr,0xF4,0,0,0)

def clrINT(addr):
    if (VerifyADDR(addr) == 0):
        return
    ppCMD(addr,0xF5,0,0,0)


#==============================================================================#
# Utility Functions                                                            #
#==============================================================================#
def getID(addr):
    global ADCbaseADDR
    if (VerifyADDR(addr)):
        addr=addr+ADCbaseADDR
        return CMD.getID2(addr)


def VerifyADDR(addr):
    global MAXADDR, adcsPresent
    if((addr<0) or (addr>=MAXADDR)):
        print("ADCplate address out of range - must be between 0 and 7")
        return 0
    addr_str=str(addr)
    if (adcsPresent[addr]!=1):
        print("Command ignored - no ADCplate found at address "+addr_str)
        return 0
    return 1

def ppCMD(addr,cmd,param1,param2,bytes2return,slow=None):
    global ADCbaseADDR
    return CMD.ppCMDADC(addr+ADCbaseADDR,cmd,param1,param2,bytes2return,slow)

def fetchBLOCK(addr,cmd,param1,param2,bytes2return):
    global ADCbaseADDR
    global blockBYTES
    blockBYTES=CMD.fetchBLOCK(addr+ADCbaseADDR,cmd,param1,param2,bytes2return)


def getADDR(i):
    global ADCbaseADDR, DataGood
    resp=ppCMD(i,0x00,0,0,1)
    #print(CMD.DataGood,resp)
    if (CMD.DataGood):
        return resp[0]-ADCbaseADDR
    else:
        return 8

def quietPoll():
    global adcsPresent, drMAP
    ppFoundCount=0
    for i in range (0,8):
        adcsPresent[i]=0
        rtn = getADDR(i)
        if (rtn==i):
            adcsPresent[i]=1
            ppFoundCount += 1
            initADC(i)

def RESET(addr):
    VerifyADDR(addr)
    ppCMD(addr,0x0F,0,0,0)
    time.sleep(1)
    quietPoll()

quietPoll()