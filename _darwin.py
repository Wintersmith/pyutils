"""
    _darwin.py - This module contains functions that are for use on the Darwin platform.
"""


def _isRunning( scriptName, pidFile=None ):
    """
        _isRunning:  Called automatically from Platform.  Detects if a version of scriptName
                    is already running.
    """
    if pidFile is None:
        pidFile = "/var/tmp/%s.pid" % scriptName
    
    if os.path.exist( pidFile ):
        thisPid = file( pidFile ).read()
    else:
        thisPid = os.getpid()
    
    for pidDir in os.listdir( procDir ):
        if pidDir != str( thisPid ) and pidDir != 'self':
            cmdFile = "%s/cmdline" % os.path.join( procDir, pidDir )
            if os.path.exists( cmdFile ):
                cmdContents = file( cmdFile ).read()
                if re.compile( scriptName ).search( cmdContents ):
                    return True
                    

    return False

def _processListing( ):
    """
        _processListing:  Called automatically from Platform.  Returns a list of tuples, containing
                        pid, uid, gid, state, commandline.
    """
    import glob
    import Utils
    
    pidDirMatch = "%s/[0-9]*" % procDir
    
    procListing = []
    for pidDir in glob.glob( pidDirMatch ):
        statusFile = file( "%s/status" % pidDir, 'r' )
        statusDict =Utils.makeDict( statusFile )
        statusFile.close()
        procListing.append( ( file( "%s/cmdline" % pidDir, 'r').read(), statusDict[ 'Pid' ], statusDict[ 'Uid' ], statusDict[ 'Gid' ] ) ) 
        
    print procListing

        
