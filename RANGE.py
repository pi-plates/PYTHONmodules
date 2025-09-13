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

dist_units = 'in'
#==============================================================================#
# RANGEFINDER Functions	                                                       #
# Uses "channel pairs" with valid values of 12, 34, 56 and 78                  #
#==============================================================================#
def getRANGE(addr,channelpair,units=None):
    global dist_units
    VerifyADDR(addr)	
    assert ((channelpair==12) or (channelpair==34) or (channelpair==56) or (channelpair==78)),"Invalid channel pair argument. Valid values are 12, 34, 56, and 78"
    channelpair=(channelpair>>1)//10
    if units is None:
        uni=dist_units
    else:   
        uni=units.lower()
        assert ((uni=='cm') or (uni=='in')),"ERROR: incorrect units parameter. Must be 'cm' or 'in'."
    resp=ppCMD(addr,0x81,channelpair,0,2)   #get data
    Range=resp[0]*256+resp[1]
    if (Range==0):
        return "ERROR: sensor failure"
    Range=(Range<<1)*12.0/49.0
    if (uni=='cm'):
        Range = Range/58.326
    if (uni=='in'):
        Range = Range/148.148
    Range=round(Range,2)
    return Range
    
def getRANGEfast(addr,channelpair,units=None):
    global dist_units
    VerifyADDR(addr)	
    assert ((channelpair==12) or (channelpair==34) or (channelpair==56)or (channelpair==78)),"Invalid channel pair argument. Valid values are 12, 34, 56, and 78"
    channelpair=(channelpair>>1)//10
    if units is None:
        uni=dist_units
    else:   
        uni=units.lower()
        assert ((uni=='cm') or (uni=='in')),"ERROR: incorrect units parameter. Must be 'cm' or 'in'."
    resp=ppCMD(addr,0x82,channelpair,0,2)   #get data
    Range=resp[0]*256+resp[1]
    if (Range==0):
        return "ERROR: sensor failure"
    Range=(Range<<1)*12.0/49.0
    if (uni=='cm'):
        Range = Range/58.326
    if (uni=='in'):
        Range = Range/148.148
    Range=round(Range,2)
    return Range
    
def setUNITS(units):
    global dist_units
    units=units.lower()
    assert ((units=='in') or (units=='cm')), "Distance units must be 'in' or 'cm'."
    dist_units=units
    
def getUNITS():
    global dist_units
    return dist_units