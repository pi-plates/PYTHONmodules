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
# PWM Functions                                                                #
#==============================================================================# 
def setPWM(addr,chan,dutyCycle):
    VerifyADDR(addr)
    assert ((chan>=1) and (chan<=6)),"PWM port number is out of range. Must between 1 and 6"
    assert ((dutyCycle>=0)and(dutyCycle<=100)), "Duty Cycle must be a value between 0.0 and 100.0"
    registerVal=int(dutyCycle*1024.0/100.0+0.5)
    param1=((chan-1)<<4)+(registerVal>>8)
    param2=registerVal&0xFF
    resp=ppCMD(addr,0xC0,param1,param2,0)
    
