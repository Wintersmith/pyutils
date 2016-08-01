#!/usr/bin/env python

import os, sys
from struct import unpack, calcsize

def processTree( basePID ):
    pidList = []
    testPID = basePID
    currPid = None
    while testPID != currPid:
        currPid, pPid, gPid, rUID, eUID, rGUID, eGUID, cmdExec, cmdLine = openProcFS( testPID )
        testPID = pPid
        pidList.append( currPid )
        if currPid == gPid and pPid == 1:
            break
        
    return pidList
    
def openProcFS( osPID ):
    psInfoRaw = open( "/proc/%d/psinfo" % int( osPID ), "rb" ).read( 232 )
    psInfo = unpack( "6i5I4LHH6L16s80siiIIc3x7i", psInfoRaw)
    
    return psInfo[ 2 ], psInfo[ 3 ], psInfo[ 4 ], psInfo[ 6 ], psInfo[ 7 ], psInfo[ 8 ], psInfo[ 9 ], psInfo[ 23 ].strip( "\x00" ), psInfo[ 24 ].strip( "\x00" )
        
if __name__ == "__main__":
    currPid = os.getpid()
    print "Looking At %s" % currPid
    print processTree( currPid )

