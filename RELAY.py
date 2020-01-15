import os
import sys
file_dir = os.path.dirname(__file__)
sys.path.append(file_dir)
from BASE import *

#==============================================================================#	
# RELAY Functions	                                                           #
#==============================================================================#  
def relayON(addr,relay):
    VerifyADDR(addr)
    assert ((relay>=1) and (relay<=2)),"Relay number out of range. Must be between 1 and 2"
    relay -= 1
    ppCMD(addr,0x10,relay,0,0)

def relayOFF(addr,relay):
    VerifyADDR(addr)
    assert ((relay>=1) and (relay<=2)),"Relay number out of range. Must be between 1 and 2"
    relay -= 1
    ppCMD(addr,0x11,relay,0,0)
    
def relayTOGGLE(addr,relay):
    VerifyADDR(addr)
    assert ((relay>=1) and (relay<=2)),"Relay number out of range. Must be between 1 and 2"
    relay -= 1
    ppCMD(addr,0x12,relay,0,0)   

def relayALL(addr,relays):
    VerifyADDR(addr)
    assert ((relays>=0) and (relays<=3)),"Argument out of range. Must be between 0 and 3"
    ppCMD(addr,0x13,relays,0,0) 
    
def relaySTATE(addr,relay):
    VerifyADDR(addr)
    assert ((relay>=1) and (relay<=2)),"Relay number out of range. Must be between 1 and 2"
    relay -= 1
    resp=ppCMD(addr,0x14,relay,0,1) 
    return resp[0]
    
