import os
import sys
file_dir = os.path.dirname(__file__)
sys.path.append(file_dir)
from BASE import *

#===============================================================================#	
# Digital Input Functions	                                                   	#
#===============================================================================#
def getDIN(addr,bit):
    VerifyADDR(addr)	
    VerifyBIT(bit)
    bit -= 1
    resp=ppCMD(addr,0x20,bit,0,1)
    if resp[0] > 0:
        return 1
    else:
        return 0
		
def getDINall(addr):
    VerifyADDR(addr)	
    resp=ppCMD(addr,0x25,0,0,1)
    return resp[0]  
    # _______________________________________________________
    #|chan 8|chan 7|chan 6|chan 5|chan 4|chan 3|chan 2|chan 1|
    # -------------------------------------------------------

#==============================================================================#	
# Digital Output Functions	                                                   #
#==============================================================================#	
def setDOUT(addr,bit):
    VerifyADDR(addr)
    VerifyBIT(bit)	
    bit -= 1
    resp=ppCMD(addr,0x26,bit,0,0)
	
def clrDOUT(addr,bit):
    VerifyADDR(addr)	
    VerifyBIT(bit)
    bit -= 1
    resp=ppCMD(addr,0x27,bit,0,0)		

def toggleDOUT(addr,bit):
    VerifyADDR(addr)	
    VerifyBIT(bit)
    bit -= 1
    resp=ppCMD(addr,0x28,bit,0,0)		
	
def setDOUTall(addr,byte):
    VerifyADDR(addr)	
    assert ((byte>=0) and (byte<=255)),'ERROR: byte argument out of range - must be between 0 and 255'
    resp=ppCMD(addr,0x29,byte,0,0)			

def getDOUTall(addr):
    VerifyADDR(addr)	
    resp=ppCMD(addr,0x25,0,0,1)
    return resp[0]
    
def VerifyBIT(bit):
    assert ((bit>0) and (bit<9)), 'bit argument must be between 1 and 8'