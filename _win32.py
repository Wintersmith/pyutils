"""
    _win32.py - This module contains all routines relevant to the Win32 platform
 
"""
 
# System Imports
 
import os
from win32com.client import GetObject
 
 
def _isRunning( scriptName, pidFile=None ):
    WMIConn = GetObject( 'winmgmts:' )
 
    queryString = 'select * from Win32_Process where Name = "%s"' % scriptName
    retRow = WMIConn.ExecQuery( queryString )
 
    try:
        scriptPID = retRow[ 0 ].Properties_( 'ProcessId' ).Value
    except IndexError:
        return False
 
    return True
 
 
def _processListing( ):
    WMIConn = GetObject( 'winmgmts:' )
    procList = WMIConn.InstancesOf( 'Win32_Process' )
 
    return [ process.Properties_( 'Name' ).Value for process in procList ]
