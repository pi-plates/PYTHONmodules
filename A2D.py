import os
import sys
import subprocess

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
    from BASE5 import * 
else:
    from BASE0 import *

#==============================================================================#	
# A2D Functions	     	                                              		   #
#==============================================================================#	
def getADC(addr,channel):
    VerifyADDR(addr)
    VerifyAINchannel(channel)
    resp=ppCMD(addr,0x30,channel-1,0,2)
    value=(256*resp[0]+resp[1])
    value=(value*5.10*2.4/4095)
    return round(value,3)

def getADCall(addr):
    value=list(range(4))
    VerifyADDR(addr)
    resp=ppCMD(addr,0x31,0,0,8)
    for i in range (0,4):
        value[i]=(256*resp[2*i]+resp[2*i+1])
        value[i]=round((value[i]*5.10*2.4/4095),3)
    return value    
 
def VerifyAINchannel(ain):
    assert ((ain>=1) and (ain<=4)),"Analog input channel value out of range. Must be in the range of 1 to 4"