import os
import sys
file_dir = os.path.dirname(__file__)
sys.path.append(file_dir)
from BASE import *

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
    
