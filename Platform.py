"""
    Platform.py:  Loads the correct module for the relevant OS.
    
    History:
    28 April, 2005:     Initial version

"""
# System Imports 
import sys

# Custom Imports
from Utils import returnScriptName

def _importModule( moduleName ):
    modName = __import__ ( moduleName )
    modComponents = moduleName.split( '.' )
    for indivComp in modComponents[ 1: ]:
        modName = getattr( modName, indivComp )

    return modName

currentOS = sys.platform
platformModule = _importModule( 'iPython._%s' % currentOS )

def isRunning( scriptName=None ):
    """
        isRunning: Returns True/False if scriptName is running.  To make it as portable as possible, will
                    call platform._ version for the relevant platform.
    """
    
    if scriptName is None:
        scriptName = returnScriptName()

    return platformModule._isRunning( scriptName )
    
def processListing( ):
    """
        processListing:  Returns a list of tuples, containing ( for now ) pid, uid, command line.
    """
    return platformModule._processListing()
