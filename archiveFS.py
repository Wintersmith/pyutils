#!/usr/bin/env python
"""
    archiveFS.py - Designed to clean up / store Concurrent Request files created on ERP systems. 
"""

import os, sys, getopt, tarfile, zipfile, logging, logging.handlers, datetime, time

VERSION = "0.1"
writeFlags = { 0: "w", 1: "w:gz", 2: "w:bz2" }

# Constants
logDir = '/stage/scripts/logs'
maxSize = 5242880
sourceDir = '/u01/appllive/livecomn/admin/log/LIVE_erpadm90'
fileTypes = [ 'out', 'req' ]
dayStart = time.mktime( ( datetime.date.today() - datetime.timedelta( days=1 ) ).timetuple() )
dayEnd = time.mktime( datetime.date.today().timetuple() )

def calcModDay( minAge=1 ):
    minDate = datetime.date.today() - datetime.timedelta( days=minAge )
    minDayStart = time.mktime( ( str( minDate ).split( '-' )[ 0 ], str( minDate ).split( '-' )[ 1 ], str( minDate ).split( '-' )[ 2 ], 0, 0, 0 ) )
    minDayEnd = time.mktime( ( str( minDate ).split( '-' )[ 0 ], str( minDate ).split( '-' )[ 1 ], str( minDate ).split( '-' )[ 2 ], 23, 59, 59 ) )
    
    return minDayStart, minDayEnd
    

def printUsage():
    pass
    
def initLogging( logFileName=None, logLevelNo=1 ):
    """
        initLogging:  Initialise the logging system  Defaults to INFO, unless logLevelNo is passed.
        
        Possible values are:
            
            1: "INFO", 2: "WARNING", 3: "DEBUG", 4: "ERROR", 5: "CRITICAL"
            
    """
    loggingLevel = { 1: "INFO", 2: "WARNING", 3: "DEBUG", 4: "ERROR", 5: "CRITICAL" } 

    scriptName = returnScriptName( )
    if logFileName is None:
        logFileName = os.path.join( logDir, "%s.log" % scriptName )
        
    logFacility = logging.getLogger( scriptName )
    rotatingLogFile = logging.handlers.TimedRotatingFileHandler( logFileName, 'midnight' )
    logFormat = logging.Formatter( '%(asctime)s %(levelname)-8s %(message)s' )
    rotatingLogFile.setFormatter( logFormat )
    logFacility.addHandler( rotatingLogFile )
    logLevel = getattr( logging, loggingLevel[ logLevelNo ] )
        
    logFacility.setLevel( logLevel )
    
    logFacility.debug( "Logging Is Now Active" )

def returnHostName( ):
    """
        returnHostName - Does exactly what you think it does, it returns the name of the host the script is running on, using
                        socket.gethostname()
    """
    import socket
    
    return socket.gethostname()

def returnScriptName( ):
    """
        returnScriptName - Does what it says on the tin.  Returns the scriptname, minus the suffix.
    """
    scriptName = sys.argv[ 0 ][ ( sys.argv[ 0 ].rfind( os.sep ) + 1): ]
    return scriptName.replace( ".py", "" )

def tarFile( fileSource, outPutBase, compressType ):
    """
        tarFile: The business end of the script. Will parse the list/file, and create the tar file.
    """
    logFacility = logging.getLogger( returnScriptName() )
    
    fileSystems = []
    
    
    # Creates a filename based on todays date
    fileDate = datetime.date.today()
    tarFileName = "%s-%s.tar" % ( fileDate, returnHostName() )
    if compressType > 0:
        tarFileName = "%s.%s" % ( tarFileName, writeFlags[ compressType ].split( ":" )[ 1 ] )
        
    try:
        fullTarFile = os.path.join( outPutBase, tarFileName )
        tarFile = tarfile.open( fullTarFile, writeFlags[ compressType ] )
    except IOError, errorMsg:
        logFacility.error( "There was an error creating the tar file %s.  Reason: %s" % ( tarFileName, errorMsg ) )
        return 2
    
    # Add links ( symbolic/hard ) to the archive, instead of following them.
    tarFile.dereference = False
    
    for indivFileSystem in fileSystems:
        logFacility.info( "Attempting To BackUp %s" % indivFileSystem )
        if not os.path.exists( indivFileSystem ):
            # If an entry in the list/file does not exist, skip it....
            logFacility.error( "The filesystem ( %s ) does not exist, skipping...." % indivFileSystem )
            continue
            
        try:
            # Add the file/directory.  Note, it is recursive for dirctories!
            tarFile.add( indivFileSystem )
        except ( IOError, KeyboardInterrupt ), errMsg:
            # If manually run, as opposed to cron, hitting CTRL-C will kill the script, and cause it to clean up ( delete the tar file )
            # IOError is also trapped, so any problem with writing to the tar file will be logged.  The script will shutdown cleanly....
            logFacility.warning( "BackUp operation has been cancelled %s" % errMsg )
            if not outPutBase is None:
                logFacility.warning( "Cleaning up tarfile ( %s ), due to operation being cancelled...." % fullTarFile )
                os.unlink( fullTarFile )
                
            return 1
        
    tarFile.close()
    logFacility.info( "BackUp Complete.  Closing TarFile...." )
    
    return 0
    
def returnFileList( fileSuffix ):
    fileList= [ fileName for fileName in os.listdir( sourceDir ) if fileName.endswith( fileSuffix ) and checkStats( fileName ) ]
    
def checkStats( fileName ):
    pass

def main( argv=None ):
    if argv is None:
        argv = sys.argv
        
    try:
        cmdOpts, cmdArgs = getopt.getopt( argv[ 1: ], "BGh", [ "gzip", "bzip", "help" ] )
    except getopt.GetoptError, errorMsg:
        print errorMsg
        printUsage()
        return 1
        
    # Default, gzip
    compressType = 1
    
    for cliOpts, cliArgs in cmdOpts:
        if cliOpts in ( "-G", "--gzip" ):
            compressType = 1

        if cliOpts in ( "-B", "--bzip" ):
            compressType = 2

    initLogging( )
    logFacility = logging.getLogger( returnScriptName() )
    logFacility.info( "Script Is Running With Options: %s - %s - %s" % ( fileSystems, outPutBase, writeFlags[ compressType ] ) )

    for fileSuffix in fileTypes:
        fileList = returnFileList( sourceDir, fileSuffix, fileAge, maxSize )
        print fileList
#        retCode = tarFile( fileList, outPutBase, compressType )
    
    logFacility.info( "Script Is Now Exiting, Return Code: %d" % retCode )
    
    return retCode
    
if __name__ == "__main__":
    sys.exit( main() )