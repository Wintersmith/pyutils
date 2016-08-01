"""

    CronLib.py
    
    Contains classes/functions for crond
    
    Requirements:
        Python 2.4+ or Py2.3 and subprocess moodule ( effbot.org )
        
        Could support Py2.2, by being re-written to use fork/spawn, etc, but why bother?
    
    TODO:
        Add ability to handle */2 increments
        Add ability for user processes
        Try and remove "duplicate" code ( _match* routines )
        Handle SIG
        
    History:
        12 May, 2005:  Initial Version - CronLib, export classes to support reading a crontab from a file ( CronFile ) or from an RDBMS ( CronSQL ).
"""
# Python Imports - As In Site-Packages
import logging, time, re, subprocess, os, sys, CGIHTTPServer, socket

try:
    import cStringIO as StringIO
except:
    import StringIO as StringIO
    
# Custom imports
from PlusNet import Utils, DBStorage, ThreadLib

class CronError( Exception ):
    
    def __init__( self, *args ):
        Exception.__init__( self, *args )

def splitCronEntry( cronEntry ):
    """
        Splits the cronEntry into individual componants.
        
        Minutes
        Hours
        Day Of Month
        Month
        Day Of Week
        Command Line
    """
    return cronEntry.split( None, 5 )
    
    
class Cron( object ):

    cronMatch = re.compile( ".*\s.*\s.*\s.*\s.*\s.*" )
    rangeMatch = re.compile( "(\d{1,2})-(\d{1,2})" )
    stepMatch = re.compile( "(.*)\/(\d{1,2})" )
    cronDaysOfWeek = { 0: 1, 1: 2, 2: 3, 3: 4, 4: 5, 5: 6, 6: 0 }
    
    def __init__( self ):
        self.cronEntries = []
        self._logFacility = logging.getLogger( Utils.returnScriptName() )
        self._webServer = False
        self._configSettings = []
        self._hostName = Utils.returnHostName()
            
    def _loadCron( self ):
        """
            _loadCron:  This function is to be over-ridden.  It provides the mechanism to populate self.cronEntries.
            
            It needs to return True if successful, False if not, along with the dictionary containing the cron entries ( or None, if return is False ).
        """
        pass
        
    def _refreshEntries( self ):
        """
            _refreshEntries:  This function will reload the cron entries from the relevant source, by calling _loadCron.
                            Only if _loadCron returns true, will self.cronEntries be over-written,
        """
        loadStatus, localEntries = self._loadCron()
        if loadStatus and localEntries is not None:
            self.cronEntries = localEntries
            self._logFacility.debug( "Cron Entries Have Been Refreshed.  Loaded %d Entries" % len( self.cronEntries ) )
        else:
            self._logFacility.debug( "Cron Entries Refresh Failed Miserably.  Using Cached Entries." )
            mailMessage = "For some reason, the refresh of the cron entries failed.  Please check the logs."
            Utils.mailError( "relay.plus.net", "cronDaemon@%s" % Utils.returnHostName, "jabel@plus.net", "Alert.  Failed To Refresh Cron", mailMessage )
            
    def run( self ):
        loadStatus, localEntries = self._loadCron()
        if loadStatus:
            self.cronEntries = localEntries
            self._runDaemon()
        else:
            self._logFacility.error( "Unable To Continue.  Exiting." )
            return 2
        
    def _runDaemon( self ):
        """
            _runDaemon:  The main loop.
        """
        nextTime = self._calcNextMinute()
        refreshEntries = False
        threadPool = ThreadLib.ThreadPool()
        if self._webServer:
            threadPool.addJob( launchWebServer, funcArgs=self._configSettings[ 'httproot' ] )
            
        while True:
            if refreshEntries:
                self._refreshEntries()
                refreshEntries = False
                
            currentTime = time.time()
            if currentTime < nextTime:
                sleepDuration = nextTime - currentTime + .1
                time.sleep( sleepDuration )
                
            splitNext = time.localtime( nextTime )
            if splitNext[ 4 ] in [ 14, 29, 44, 59 ]:
                refreshEntries = True
                self._logFacility.debug( "Refreshing Entries Next Pass." )
                
            for cmdLine in self._matchEntry( splitNext ):
                self._logFacility.info( "CMD: %s" % cmdLine )
                threadPool.addJob( launchSubProc, funcArgs=cmdLine )
                
            nextTime = self._calcNextMinute()
            
    def _calcNextMinute( self ):
        """
            calcNextMinute:  Calculates the next minute, to HH:MM::00
        """
        nextMinute = time.localtime( time.time() + 60 )
        nextMinute = nextMinute[ :5 ] + ( 0, ) + nextMinute[ 6: ]
        
        return time.mktime( nextMinute )

    def _matchEntry( self, cronTime ):
        for indivEntry in self.cronEntries:
            splitEntry = splitCronEntry( indivEntry )
            
            checkSum = 0
            for funcCount, funcName in enumerate( [ '_matchMinute', '_matchHour', '_matchDOM', '_matchMnth', '_matchDOW' ] ):
                checkFunc = getattr( self, funcName )
                checkSum = checkSum + checkFunc( splitEntry[ funcCount ].replace( ' ','' ), cronTime )
                print checkSum
                
            if checkSum == 5:
                print "CheckSum Matched - %s" % splitEntry[ 5 ] 
                yield splitEntry[ 5 ]
            else:
                print "CheckSum Didn't Match - %s " % splitEntry[ 5 ]
        
    def _matchMinute( self, splitMin, cronTime ):
        if splitMin == "*":
            return 1
        else:
            retValue =  self._performREMatch( splitMin, cronTime[ 4 ] )
            if retValue == 1 or retValue == 0:
                return retValue
                
            for indivMins in splitMin.split( ',' ):
                retValue = self._performREMatch( indivMins, cronTime[ 4 ] )
                if retValue == 1:
                    return 1
                elif retValue == 0:
                        continue
                        
                if int( indivMins ) == cronTime[ 4 ]:
                    return 1
            
        return 0
        
    def _matchHour( self, splitHour, cronTime ):
        if splitHour == "*":
            return 1
        else:
            retValue =  self._performREMatch( splitHour, cronTime[ 3 ] )
            if retValue == 1 or retValue == 0:
                return retValue
            for indivHour in splitHour.split( ',' ):
                retValue = self._performREMatch( indivHour, cronTime[ 3 ] )
                if retValue == 1:
                    return 1
                elif retValue == 0:
                        continue
                if int( indivHour ) == cronTime[ 3 ]:
                    return 1
            
        return 0
        
    def _matchDOM( self, splitDOM, cronTime ):
        if splitDOM == "*":
            return 1
        else:
            retValue =  self._performREMatch( splitDOM, cronTime[ 2 ] )
            if retValue == 1 or retValue == 0:
                return retValue
            for indivDOM in splitDOM.split( ',' ):
                retValue = self._performREMatch( indivDOM, cronTime[ 2 ] )
                if retValue == 1:
                    return 1
                elif retValue == 0:
                        continue
                if int( indivDOM ) == cronTime[ 2 ]:
                    return 1
            
        return 0
        
    def _matchMnth( self, splitMnth, cronTime ):
        if splitMnth == "*":
            return 1
        else:
            retValue =  self._performREMatch( splitMnth, cronTime[ 1 ] )
            if retValue == 1 or retValue == 0:
                return retValue
            for indivMnth in splitMnth.split( ',' ):
                retValue = self._performREMatch( indivMnth, cronTime[ 1 ] )
                if retValue == 1:
                    return 1
                elif retValue == 0:
                        continue
                if int( indivMnth ) == cronTime[ 1 ]:
                    return 1
            
        return 0
        
    def _matchDOW( self, splitDOW, cronTime ):
        if splitDOW == "*":
            return 1
        else:
            retValue =  self._performREMatch( splitDOW, self.cronDaysOfWeek [ cronTime[ 6 ] ] )
            if retValue == 1 or retValue == 0:
                return retValue
            for indivDOW in splitDOW.split( ',' ):
                retValue = self._performREMatch( indivDOW, self.cronDaysOfWeek [ cronTime[ 6 ] ] )
                if retValue == 1:
                    return 1
                elif retValue == 0:
                        continue
                if int( indivDOW ) == cronTime[ 6 ]:
                    return 1
            
        return 0

    def _performREMatch( self, matchField, timeField, fieldType="M" ):
#        regMatch = self.stepMatch.match( matchField )
#        if regMatch:
#            rangeStep = int( regMatch.group( 2 ) )
#            if regmatch.group( 1 ) == "*":
#                
#            regMatch = self.rangeMatch.match( regMatch.group( 1 ) )
#            if regMatch:
#                startRange = int( regMatch.group( 1 ) )
#                endRange = int( regMatch.group( 2 ) )
#            if timeField in range( startRange, endRange + 1, rangeStep ):
#                return 1

                    
        regMatch = self.rangeMatch.match( matchField )
        if regMatch:
            if regMatch.group( 2 ) < regMatch.group( 1 ):
                rangeEnd = int( regMatch.group( 2 ) ) + 24
            else:
                rangeEnd = int( regMatch.group( 2 ) )
            if timeField in range( int( regMatch.group( 1 ) ), rangeEnd + 1 ):
                return 1
            else:
                return 0
                    
        return 2

class CronFile( Cron ):
    
    
    def __init__( self, cronSource ):
        super( CronFile, self ).__init__( )
        self._cronSource = cronSource
        if not os.path.exists( cronSource ):
            raise CronError, "%s Does not Exist!" % cronSource
        
    def _loadCron( self ):
        localEntries = []
        self._logFacility.debug( "Loading Cron Entries From File" )
        
        try:
            cronFile = file( self._cronSource )
        except IOError, errorMsg:
            self._logFacility.error( "Unable To Open File %s.  Reason: %s" % ( self._cronSource, errorMsg ) )
            return False, None
            
        for indivEntry in cronFile:
            if not indivEntry.startswith( '#' ) and len( indivEntry ) > 1 and self.cronMatch.match( indivEntry ):
#                localEntries.append( indivEntry )
                print splitCronEntry( indivEntry )
                
        cronFile.close()
        
        return True, localEntries
    
class CronSQL( Cron ):
    
    def __init__( self, configSettings, webServer=True ):
        super( CronSQL, self ).__init__( )
        self._configSettings = configSettings
        self.dbInst = DBStorage.DBStorage( "Cron", self._configSettings[ 'dbhost' ], self._configSettings[ 'dbtype' ], 
                                                                    userName=self._configSettings[ 'dbuser' ], passWord=self._configSettings[ 'dbpass' ] )
        self._webServer = webServer
        self.hostID, self.groupID = self._returnHostID( )
        if self.hostID is None:
            self._logFacility.error( "SQL LookUp For Host Failed.  No Point In Running." )
            
    def _returnHostID( self ):
        _hostFound = False
        if self._prepareDB():
            while _hostFound == False:
                hostCursor = self.dbInst.getCursor()
                self.dbInst.execSQL( hostCursor, "SELECT hostID, hostGID FROM Hosts WHERE hostName = '%s';" % self._hostName )
                retRow = self.dbInst.returnSingle( hostCursor )
                if not retRow is None:
                    hostID =  retRow[ 0 ]
                    hostGID = retRow [ 1 ]
                    self._logFacility.debug( "Returned HostID, GroupID = %s, %s" % ( hostID, hostGID ) )
                    _hostFound = True
                    break
                else:
                    self._logFacility.info( "Host %s Not Found In The DB - Creating Record." % self._hostName )
                    self.dbInst.execSQL( hostCursor, "INSERT IN Hosts ( hostID, hostName ) VALUES( NULL, '%s' );" % self._hostName )
                    
            self._closeDB()
            
            return hostID, hostGID
            
        return None, None
        
    def _prepareDB( self ):
        try:
            self.dbInst.dbOpen()
        except DBStorage.DBError, errorMsg:
            return False
            
        return True
        
    def _closeDB( self ):
        self.dbInst.dbClose()
        
    def _loadCron( self ):
        localEntries = []
        masterStatus = True
        
        self._logFacility.debug( "Loading Cron Entries Via SQL" )
        
        if not self._prepareDB():
            return False, None
        selectCursor = self.dbInst.getCursor()
        if self.groupID > 0:
            self.dbInst.execSQL( selctCursor, "SELECT groupMaster in CronGroup WHERE groupID = %d;" % self.groupID )
            retRow = self.dbInst.returnSingle( selectCursor )
            if not retRow is None and retRow[ 0 ] != self.hostID:
                masterStatus = False
                self._logFacility.info( "Server Is Currently Running In BackUp Mode." )
            else:
                self._logFacility.info( "Server Is Master For Group" )
            
        if masterStatus:
            retrieveCronEntries = """SELECT cronMinute, cronHour, cronDayOfMonth, cronMonth, cronDayOfWeek, cronCommandLine, cronUID 
                                                                        FROM CronEntries WHERE cronHost = ( %d ) AND cronActive = 1""" % self.hostID
            try:
                self.dbInst.execSQL( selectCursor, retrieveCronEntries )
            except DBStorage.DBError, errorMsg:
                self._logFacility.error( "Failed To Load The Cron Entries From The DB.  Returned Error: %s" % errorMsg )
                mailMessage = "Failed To Load The Cron Entries From The DB.  Returned Error: %s." % errorMsg
                Utils.mailError( self._configSettings[ 'mailrelay' ], "cronDaemon@%s" % Utils.returnHostName(), 
                                                                            self._configSettings[ 'alertsto' ], "Alert.  Failed To Refresh Cron", mailMessage )
                return False, None
    
            for retRow in self.dbInst.returnMany( selectCursor ):
                cronText = "%s %s %s %s %s %s" % ( retRow[ 0 ], retRow[ 1 ], retRow[ 2 ], retRow[ 3 ], retRow[ 4 ], retRow[ 5 ], )
                self._logFacility.debug( "Loading - %s " % cronText )
                print cronText
                localEntries.append( cronText )
                
        self._closeDB()
        
        return True, localEntries

class CGIHandler( Utils.WebHandler ):
    cgi_directories = [ "/cgi-bin" ]
    httpRoot = None
    webPort = 8888
    server_version = "PlusNet-CGI/0.1"
    
    indexPage = """<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
    <html>
    <head>
        <title>Cron Management</title>
        <META HTTP-EQUIV="Refresh" CONTENT="2; URL=http://%s:%d/cgi-bin/cron.cgi">
    </head>
    <body>
        You Have Arrived At The Wrong Page, You Wil Be Shortly Directed To The
        Cron Maintenance Page
    </body>
    </html>""" % ( socket.gethostbyname( Utils.returnHostName() ), webPort )

    def handleNoIndex( self ):
        indexPage = StringIO.StringIO( self.indexPage )
        self.send_response( 200 )
        self.send_header( "Content-type", "text/html" )
        self.send_header( "Content-Length", str( indexPage.tell( ) ) )
        self.end_headers()
        indexPage.seek( 0 )
        
        return indexPage

def launchWebServer( httpRoot, webPort=8888 ):
    CGIHandler.httpRoot = httpRoot
    webServer = Utils.RestrictedServer( ( '', webPort ), CGIHandler )
    webServer.allowedClientHosts = [ '172.29.24.33', '172.29.24.0/21', '172.29.32.0/20', '192.168.98.0/22', '192.168.100.0/24' ]
    webServer.serve_forever()
    
def launchSubProc( cmdLine, newUID=None ):
    """
        launchSubProc: Launches the cmdline, and waits for the proc to terminate.  This should be run in a thread, as the call to wait()
                        holds up the rest of the script.  Unfortunately, there doesn't seem an easy way to "fork" off a program.
    """
    import pwd
    
    logFacility = logging.getLogger( Utils.returnScriptName() )
    
    if newUID is None:
        newUID = os.getuid()
        
    try:
        execProc = subprocess.Popen( cmdLine, shell=True, preexec_fn=lambda: os.setuid( newUID ) )
    except OSError, errorMsg:
        logFacility.error( "CMD: %s - Failed To Launch.  Reason: %s" % ( cmdLine, errorMsg ) )
    else:
        logFacility.info( "CMD: %s - Launched With PID %d" % ( cmdLine, execProc.pid ) )
        execProc.wait()
