import os
import sys
file_dir = os.path.dirname(__file__)
sys.path.append(file_dir)
from BASE import *
from DIO  import *
from PWM import *

#===============================================================================#	
# LED Functions	                                                   		   		#
#===============================================================================#			
def setLED(addr,chan,bright=None):
    assert ((chan>=0) and (chan<=8)),"Invalid LED number - must be between 0 and 8"
    VerifyADDR(addr)
    if (chan==0):
        assert (bright==None),"The brightness can only be controlled on channels 1 through 6."
        resp=ppCMD(addr,0x60,0,0,0)
    else:
        if (bright==None):
            resp=ppCMD(addr,0x90,chan-1,1,0)    #force DOUT mode
            clrDOUT(addr,chan)
        else:
            assert ((chan>=1) and (chan<=6)),"The brightness can only be controlled on channels 1 through 6."
            assert ((bright>=0.0) and (bright<=100.0)), 'Brightness must be between 0 and 100%'
            resp=ppCMD(addr,0x90,chan-1,3,0)    #force PWM mode
            bright=100.0-bright
            setPWM(addr,chan,bright)

def clrLED(addr,chan):
    assert ((chan>=0) and (chan<=8)),"Invalid LED number - must be between 0 and 8"
    VerifyADDR(addr)
    if (chan==0):
        resp=ppCMD(addr,0x61,0,0,0)
    else:
        resp=ppCMD(addr,0x90,chan-1,1,0)    #force DOUT mode
        setDOUT(addr,chan)
        #setPWM(addr,chan,100.0)

def toggleLED(addr,chan):
    assert ((chan>=0) and (chan<=8)),"Invalid LED number - must be between 0 and 8"
    VerifyADDR(addr)
    if (chan==0):
        resp=ppCMD(addr,0x62,0,0,0)	
    else:
        state=getDIN(addr,chan)
        resp=ppCMD(addr,0x90,chan-1,1,0)    #force DOUT mode
        if (state==0):
            setDOUT(addr,chan)
        else:
            clrDOUT(addr,chan)      

def getLED(addr,chan):
    assert ((chan>=0) and (chan<=8)),"Invalid LED number - must be between 0 and 8"
    VerifyADDR(addr)
    if (chan==0):    
        resp=ppCMD(addr,0x63,0,0,1)
        arg=resp[0]
    else:
        arg=getDIN(addr,chan)
        if (arg==0):
            arg=1
        else:
            arg=0
    return arg

def setRGB(addr,chan,red,grn,blu):
    assert ((chan>=1) and (chan<=8)),"Invalid LED channel - must be between 1 and 8"
    VerifyADDR(addr)
    VerifyCHAN(chan)
    ppCMD(addr,0x64,chan-1,0,0) #select the channel
    ledarg=RGBto24(red,grn,blu)
    ledarg=RGB24to565(ledarg)  #Convert 8:8:8 to 5:6:5
    param1=ledarg>>8
    param2=ledarg&0xFF    
    ppCMD(addr,0x65,param1,param2,0)    #send the data
    
def setRGBSTRING(addr,chan,string):
    assert ((chan>=1) and (chan<=8)),"Invalid LED channel - must be between 1 and 8"
    VerifyADDR(addr)
    VerifyCHAN(chan)
    assert (len(string)>=3), "LED string length is too sort. Must be 3 or more."
    assert (len(string)<=64*3), "LED string length is too long. Must be 3*64 or less."
    assert ((len(string)%3)==0), "LED string length must be a mulitple of 3."
    ppCMD(addr,0x64,chan-1,0,0) #set the channel
    ledarg=RGBto24(string[0],string[1],string[2])  #Convert 8:8:8 to 5:6:5
    ledarg=RGB24to565(ledarg)
    param1=ledarg>>8
    param2=ledarg&0xFF
    resp=ppCMD(addr,0x66,param1,param2,0)     #Start LED string command
    if (len(string)>3):
        for i in range(len(string)//3-1):
            ledarg=RGBto24(string[(i+1)*3],string[(i+1)*3+1],string[(i+1)*3+2])
            ledarg=RGB24to565(ledarg)
            param1=ledarg>>8
            param2=ledarg&0xFF
            resp=ppCMD(addr,0x67,param1,param2,0)     #Append LED string command
    resp=ppCMD(addr,0x68,0,0,0)             #String complete. Write to LEDs.
            
def RGBto24(red,grn,blu):
    red=int(red)
    assert (red<=255), "Red color is greater than 255."
    grn=int(grn)
    assert (grn<=255), "Green color is greater than 255."
    blu=int(blu)
    assert (blu<=255), "Blue color is greater than 255."
    rgb24=(red<<16)+(grn<<8)+blu
    return(rgb24)   
    
def RGB24to565(val888):
    red=val888>>16
    lowbits=red&0x7
    red=red>>3
    if ((lowbits>3) and (red<31)):
        red += 1
    grn=(val888>>8)&0xFF
    lowbits=grn&0x3
    grn=grn>>2
    if ((lowbits>1) and (grn<63)):
        grn += 1   
    blu=val888&0xFF
    lowbits=blu&0x7
    blu=blu>>3
    if ((lowbits>3) and (blu<31)):
        blu += 1
    val565=(red<<11) + (grn<<5) + blu
    return(val565)
    