"""
    Utils.py
    
    Contains classes, functions that are useful for any package.
"""
import sys, logging, logging.handlers, os, urllib2, base64, re, sys, urlparse, datetime

# For RestrictedServer
import BaseHTTPServer, CGIHTTPServer, posixpath, urllib
try:
    import cStringIO as StringIO
except ImportError:
    import StringIO as StringIO

# For IP Utilities - isHostInNet
import socket, struct

# For takeBackUp
import filecmp, shutil

# For Password Generation
import string, random

# For genFileList
import glob

from sgmllib import SGMLParser

# For workDays
import datetime

class Usage( Exception ):
    def __init__(self, msg):
        self.msg = msg

scriptName = sys.argv[ 0 ].replace( ".py", "" )

class UnZip( object ):

    def __init__( self, zipFile ):
        self._archiveObject = zipfile.ZipFile( zipFile )
        
    def extract(self, extractDir, excludeList=None, fileMode='wb', createDir=True, toStdOut=False, overWriteFiles=True  ):
        if not os.path.exists( extractDir ):
            print "Destination Directory Does Not Exist!"
            sys.exit( 0 )
            
        for nameInZip in self._listZipContents():
            ( path, name) = os.path.split(os.path.join( extractDir, nameInZip ) )
            if ( not excludeList is None ) and ( not name in excludeList ):
                print "Extracting %s" % nameInZip
                if not nameInZip.endswith('/'):
                    try:
                        os.makedirs( path) 
                    except:
                        pass
                    localFile = os.path.join( extractDir, nameInZip )
                    if toStdOut:
                        outFile = sys.stdout
                    else:
                        if overWriteFiles:
                            outFile = file( localFile, fileMode )
                        else:
                            continue
                    outFile.write( self._archiveObject.read( nameInZip ) )
                    outFile.flush()
                    if not toStdOut:
                        outFile.close()
                else:
                    self._create_necessary_paths( nameInZip )
                
    def listArchive( self ):
        for nameInZip in self._listZipContents( ):
            print nameInZip
            
    def _create_necessary_paths( self, filename ):
        try:
            ( path,name ) = os.path.split( filename )
            os.makedirs( path) 
        except:
            pass   

    def _makedirs( self, directories, basedir ):
        """ 
            Create Any Directories That Don't Currently Exist
        """
        for dirName in directories:
            curdir = os.path.join( basedir, dirName )
            if not os.path.exists( curdir ):
                os.mkdir( curdir )

    def _listZipContents( self ):
        for nameInZip in  self._archiveObject.namelist():
            yield nameInZip
            
    def close( self ):
         self._archiveObject.close()

class RestrictedServer( BaseHTTPServer.HTTPServer ):
    """
        It is not threaded, though for some reason, adding the SocketServer.Threading* classes
        stops it serving pages.  To restrict access, add a list [ ] to allowedClientHosts.  It will
        always allow 127.0.0.1/localhost
    """
    
    allowedClientHosts = None
    allow_reuse_address = True
    ipRange = re.compile( "\d*\.\d*\.\d*\.\d*/\d*" )
    
    def verify_request( self, request, client_address ):
        if not self.allowedClientHosts is None:
            if client_address[ 0 ] in self.allowedClientHosts:
                return True
            else:
                retValue = False
                for allowedHosts in self.allowedClientHosts:
                    if self.ipRange.match( allowedHosts ):
                        retValue = isHostInNet( client_address[ 0 ], allowedHosts )
                        if retValue:
                            break
                return retValue

        return True

class CGIHandler( CGIHTTPServer.CGIHTTPRequestHandler ):
    """
        This is a custom CGI Server.  It is for use within a script, to provide *limited* web facilities.
    """
    
    httpRoot = os.curdir
    
    indexPage = """<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
    <html>
    <head>
        <title>PlaceHolder Page - Please Replace</title>
    </head>
    <body>
        This Is A Place Holder
    </body>
    </html>"""
    
    def __init__( self, request, client_address, server ):
        self._logFacility = logging.getLogger( returnScriptName( ) )
        CGIHTTPServer.CGIHTTPRequestHandler.__init__( self, request, client_address, server )
        
    def handleNoIndex( self ):
        indexPage = StringIO.StringIO( self.indexPage )
        self.send_response( 200 )
        self.send_header( "Content-type", "text/html" )
        self.send_header( "Content-Length", str( indexPage.tell() ) )
        self.end_headers()
        indexPage.seek( 0 )
        
        return indexPage
        
    def send_head( self ):
        if self.is_cgi():
            return self.run_cgi()
            
        path = self.translate_path( self.path )
        f = None
        if os.path.isdir( path ):
            for index in "index.html", "index.htm":
                index = os.path.join( path, index )
                if os.path.exists( index ):
                    path = index
                    break
            else:
                return self.handleNoIndex()
                
        ctype = self.guess_type( path )
        if ctype.startswith( 'text/' ):
            mode = 'r'
        else:
            mode = 'rb'
        try:
            f = open( path, mode )
        except IOError:
            self.send_error( 404, "File not found" )
            return None
        self.send_response( 200 )
        self.send_header( "Content-type", ctype )
        self.send_header( "Content-Length", str( os.fstat( f.fileno() )[6] ) )
        self.end_headers()
        return f

    def translate_path(self, path):
        path = posixpath.normpath( urllib.unquote( path ) )
        words = path.split( '/' )
        words = filter( None, words )
        if self.httpRoot is None:
            path = os.path.abspath( os.path.dirname( sys.argv[ 0 ] ) )
            self._logFacility.debug( "Using %s." % path )
        else:
            path = self.httpRoot
        for word in words:
            drive, word = os.path.splitdrive( word )
            head, word = os.path.split( word )
            if word in ( self.httpRoot, os.pardir ):
                continue
            path = os.path.join( path, word )

        return path
        
    def log_request( self, code='-', size='-' ):
        try:
            self._logFacility.info( "WebServer - Request: %s, Code: %s, Size: %s." % ( self.requestline, str( code ), str( size ) ) )
        except:
            pass
        
    def log_error( self, *args ):
        self._logFacility.error( "Web Server - Addr From: %s, Code: %d, Message: %s" % ( self.address_string(), args[ 1 ], args[ 2 ] ) )

class FTP( object ):
    """
        Class to wrap ftplib, and add niceties, such as putFile, getFile.  It will also perform a reconnect, if the connection
        times out.
    """

    def __init__( self, ftpHost, ftpUser, ftpPass ):
        self._ftpHost = ftpHost
        self._ftpUser = ftpUser
        self._ftpPass = ftpPass
        self_ftpConn = None

    def putFile( self, localFile, remoteFile ):
        xferStatus = True
        self._checkConnection()
        localFile = file( localFile, 'rb')
        try:
            ftpServer.storbinary( "STOR %s" % remoteFile, localFile )
        except ( ftplib.error_perm, ftplib.error_temp ):
            xferStatus = False
            
        localFile.close()
    
        return xferStatus

    def login( self ):
        self._ftpConn = ftplib.FTP()
        self._serverConnect()
        
    def _serverConnect( self ):
        self._ftpConn.connect( self._ftpHost )
        self._ftpConn.login( self._ftpUser, self._ftpPass )
        
    def _checkConnection( self ):
        try:
            self._ftpConn.pwd()
        except:
            self._serverConnect()

def returnScriptName( ):
    """
        returnScriptName - Does what it says on the tin.  Returns the scriptname, minus the suffix.
    """
    return sys.argv[ 0 ].replace( ".py", "" )

def scriptHome( ):
    return os.path.split( os.path.realpath( sys.argv[ 0 ] ) )[ 0 ]
    
def returnHostName( ):
    """
        returnHostName - Does exactly what you think it does, it returns the name of the host the script is running on, using
                        socket.gethostname()
    """
    import socket
    
    return socket.gethostname()
    
def makeDaemon( stdin='/dev/null', stdout='/dev/null', stderr='/dev/null', pidFile=None ):
    """
        makeDaemon:  On *nix platforms, will daemonize the script.
    """
    logFacility = logging.getLogger( returnScriptName( ) )
    
    if not sys.platform == "win32":
        if pidFile is None:
            pidFile = '/var/tmp/%s.pid' % returnScriptName()
            
        try:
            logFacility.info( "Daemonizing...Old PID %s" % os.getpid() )
        except:
            pass

        try:
            progPid = os.fork()
            if progPid > 0:
                sys.exit( 0 )
        except OSError, errorMsg:
            logFacility.error( "Failed First Daemonize Attempt %d - %s" % ( errorMsg.errno, errorMsg.strerror ) )
            return False

        os.chdir( "/var/tmp" )
        os.setsid()
        os.umask( 0 )

        try:
            progPid = os.fork()
            if progPid > 0:
                sys.exit( 0 )
        except OSError, errorMsg:
            try:
                logFacility.error( "Failed Second Daemonize Attempt %d - %s" % ( errorMsg.errno, errorMsg.strerror ) )
            except:
                pass
                
            return False
        
        for fileHandle in sys.stdout, sys.stderr:
            fileHandle.flush()
            
        stdIn = file( stdin, 'r' )
        stdOut = file( stdout, 'a+' )
        stdErr = file( stderr, 'a+', 0 )
        os.dup2( stdIn.fileno(), sys.stdin.fileno() )
        os.dup2( stdOut.fileno(), sys.stdout.fileno() )
        os.dup2( stdErr.fileno(), sys.stderr.fileno() )
        
        thisPid = os.getpid()
        try:
            logFacility.info( "Daemonizing...Complete - New PID: %s" % thisPid )
        except:
            pass

        newPidFile = file( pidFile, 'w' )
        newPidFile.write( "%s" % str( thisPid ) )
        newPidFile.close()

        return True
    
def initLogging( logFileName=None, logLevelNo=1 ):
    """
        initLogging:  Initialise the logging system  Defaults to INFO, unless logLevelNo is passed.
        
        Possible values are:
            
            1: "INFO", 2: "WARNING", 3: "DEBUG", 4: "ERROR", 5: "CRITICAL"
    """
    loggingLevel = { 1: "INFO", 2: "WARNING", 3: "DEBUG", 4: "ERROR", 5: "CRITICAL" } 

    scriptName = returnScriptName( )
    if logFileName is None:
        logFileName = "/var/tmp/%s.log" % scriptName
        
    logFacility = logging.getLogger( scriptName )
    rotatingLogFile = logging.handlers.TimedRotatingFileHandler( logFileName, 'midnight' )
    logFormat = logging.Formatter( '%(asctime)s %(levelname)-8s %(message)s' )
    rotatingLogFile.setFormatter( logFormat )
    logFacility.addHandler( rotatingLogFile )
    logLevel = getattr( logging, loggingLevel[ logLevelNo ] )
        
    logFacility.setLevel( logLevel )
    
    logFacility.debug( "Logging Is Now Active" )

def mailError( mailRelay, mailFrom, mailTo, mailSubject, mailBody ):
    import smtplib
    from email.MIMEText import MIMEText

    mailSender = smtplib.SMTP( )
    mailMsg = MIMEText( mailBody )
    
    mailMsg[ 'Subject' ] = mailSubject
    mailMsg[ 'To' ] = mailTo
    mailMsg[ 'From' ] = mailFrom
    
    mailSender.connect( mailRelay )
    mailSender.sendmail( mailFrom, [ mailTo ], mailMsg.as_string() )
    mailSender.close()

class hrefParser( SGMLParser ):

    gpgFile = re.compile( ".*\.gpg" )

    def reset( self ):
        SGMLParser.reset( self )
	self._hrefData = []

    def start_a( self, attrs ):
        if attrs[ 0 ][ 0 ].lower() == "href":
	    if self.gpgFile.match( attrs[ 0 ][ 1 ] ):
	        self._hrefData.append( attrs[ 0 ][ 1 ] )

    def output( self ):
        return self._hrefData

class AuthHTTP( object ):

    _saveDir = os.getcwd()

    def __init__( self, URL, userName, passWord ):
        self._theURL = URL
        self._userName = userName
        self._passWord = passWord

    def makeAuthHTTPConnection( self, newURL = None ):
        if newURL is None:
            remoteURL = self._theURL
        else:
            remoteURL = newURL
        httpRequest = urllib2.Request( remoteURL )
        b64String = base64.encodestring('%s:%s' % ( self._userName, self._passWord ) )[:-1]
        httpRequest.add_header("Authorization", "Basic %s" % b64String)
        try:
            httpConn = urllib2.urlopen( httpRequest)
        except urllib2.HTTPError, ErrorMsg:
            print "Failed To Open URL %s. Reason: %s" % ( remoteURL, ErrorMsg )
            return None
        else:
            return httpConn

    def returnFiles( self, httpConn ):
        htmlData = httpConn.read()
        pageParser = hrefParser()
        pageParser.feed( htmlData )
        pageParser.close()
        httpConn.close()

        return pageParser.output()

    def downloadGPGFiles( self, fileList  ):
        for fileName in fileList:
            fileURL = urlparse.urljoin( self._theURL, fileName )
            localFile = file( os.path.join( self._saveDir, fileName ), "w" )
            httpFileConn = self.makeAuthHTTPConnection( fileURL )
            if not httpFileConn is None:
                localFile.write( httpFileConn.read() )
                localFile.close()
                httpFileConn.close()

def genRandomPassword( passLength=8, randomChars=string.letters+string.digits ):
    import random
    
    return ''.join( [ random.choice( randomChars ) for charIndex in range( passLength ) ] )
    
class Password( object ):
    
    def __init__( self, referenceFile=None ):
        if referenceFile is None:
            referenceFile='/usr/share/dict/words'
        try:
            wordFile = file( referenceFile )
        except IOError, errorMsg:
            print "Unable To Read Dictionary File.  Reason: %s" % errorMsg
            sys.exit( 0 )
            
        self.wordDict = wordFile.read().lower()
        wordFile.close()
        print self.wordDict
        
    def generate( self, noOfRandom=8, maxHistory=3 ):
        newPassword = []
        for indexCount in range( noOfRandom ):
            randomSpot = random.randrange( len( self.wordDict ) )
            self.wordDict = self.wordDict[ randomSpot: ] + self.wordDict[ :randomSpot ]
            wherePointer = -1
            locateChar = ''.join( newPassword[ -maxHistory: ] )
            while wherePointer < 0 and locateChar:
                wherePointer = self.wordDict.find( locateChar )
                locateChar = locateChar[ 1: ]
                
            selectedChar = self.wordDict[ wherePointer + len( locateChar ) + 1 ]
            if not selectedChar.islower():
                selectedChar = random.choice( string.lowercase )
            newPassword.append( selectedChar )

        return ''.join( newPassword )
    
def takeBackup( sourceDir, backupDir="BackUp", maxVersions=100 ):
    for foundDir, foundSubDirs, foundFiles in os.walk( sourceDir ):
        destPath = os.path.join( backupDir, foundDir )
        if not os.path.exists( destPath ):
            os.makedirs( destPath )
            
        for fileName in foundFiles:
            origFile = os.path.join( foundDir, fileName )
            destFile = os.path.join( destPath, fileName )
            for versionCount in xrange( maxVersions ):
                backupFile = '%s.%2.2d' % ( destFile, versionCount )
                if not os.path.exists( backupFile):
                    break
            if versionCount > 0:
                prevBackup = '%s.%2.2d' % ( destFile, versionCount - 1 )
                absPath = os.path.abspath( prevBackup )
                if os.path.isfile( prevBackup ) and filecmp.cmp( absPath, origFile, shallow=False ):
                    continue
                    
            print "Copying %s To %s" % ( origFile, backupFile )
            shutil.copy( origFile, backupFile )


validNetMasks = {0: 0L, 1: 2147483648L, 2: 3221225472L, 3: 3758096384L,
                    4: 4026531840L, 5: 4160749568L, 6: 4227858432L,
                    7: 4261412864L, 8: 4278190080L, 9: 4286578688L,
                    10: 4290772992L, 11: 4292870144L, 12: 4293918720L,
                    13: 4294443008L, 14: 4294705152L, 15: 4294836224L,
                    16: 4294901760L, 17: 4294934528L, 18: 4294950912L,
                    19: 4294959104L, 20: 4294963200L, 21: 4294965248L,
                    22: 4294966272L, 23: 4294966784L, 24: 4294967040L,
                    25: 4294967168L, 26: 4294967232L, 27: 4294967264L,
                    28: 4294967280L, 29: 4294967288L, 30: 4294967292L,
                    31: 4294967294L, 32: 4294967295L}
                    
def netMaskToCIDR( netMask ):
    numNetMask = dottedQuadToNum( netMask )
    for netKey, netNum in validNetMasks.items():
        if netNum == numNetMask:
            return netKey


def dottedQuadToNum( ipAddr ):
    return struct.unpack( '>L',socket.inet_aton( ipAddr ) )[0]

    
def numToDottedQuad( ipNum ):
    return socket.inet_ntoa( struct.pack( '>L', ipNum ) )

    
def makeMask( ipMask ):
    "return a mask of n bits as a long integer"
    return ( 2L << ipMask - 1) - 1

    
def ipToNetAndHost( ipAddr, ipMask ):
    ipNum = dottedQuadToNum( ipAddr )
    maskNum = makeMask( ipMask )

    hostAddr = ipNum & maskNum
    netAddr = ipNum - hostAddr

    return numToDottedQuad( netAddr ), numToDottedQuad( hostAddr )
    
def isHostInNet( hostIPAddr, slashedNetIP ):
    netIPAddr, maskLength = slashedNetIP.split('/')
    maskLength = int( maskLength )
    netAddr, netHost  = ipToNetAndHost( netIPAddr, 32 - maskLength )
    try:
        assert netHost == '0.0.0.0'
    except AssertionError:
        return False
    hostNetAddr, hostHost = ipToNetAndHost( hostIPAddr, 32 - maskLength )
    
    return hostNetAddr == netAddr
    
def loadConfig( configFile ):
    configEntries = {}
    try:
        cfgFile = file( configFile )
    except IOError, errMsg:
        return None
        
    for configEntry in cfgFile:
        configKey, configValue = configEntry.split( '=' )
        if configValue[ -1 ] == '\n':
            configValue = configValue [ :-1 ]
        configEntries[ configKey.lower() ] = configValue
        
    return configEntries

def genFileList( sourceDir, filePattern=None ):
    if filePattern is None:
        fileListing = os.path.listdir( sourceDir )
    else:
        fileListing = glob.glob( os.path.join( sourceDir, filePattern ) )

    for retFile in fileListing:
        if filePattern is None:
            foundFile = retFile
        else:
            foundFile = os.path.basename( retFile )
            
        yield foundFile

def fileFind( sourceDir ):

    if not sourceDir.endswith( os.sep ):
        sourceDir = os.path.join( sourceDir, '' )
        
    for rootDir, subDirs, subFiles in os.walk( sourceDir ):
        if rootDir.startswith( '.' ):
            continue

        for fileName in subFiles:
            if fileName.startswith( '.' ):
                continue

            relPath = os.path.join( rootDir, fileName )
            yield relPath.replace( sourceDir, '' )
            
class IndexParser( SGMLParser ):

    def reset( self ):
        SGMLParser.reset( self )
        self._inTitle = False
        self._titleText = []

    def start_title( self, tag ):
        self._inTitle = True

    def end_title( self ):
        self._inTitle = False

    def handle_data( self, text ):
        if self._inTitle:
            self._titleText.append( text )

    def output( self ):
        return "".join( self._titleText )

def parseIndexPage( indexPage ):
    parser = IndexParser()

    indexFile = file( indexPage )
    parser.feed( indexFile.read() )
    parser.close()
    indexFile.close()

    return parser.output()
    

def versionFile( fileSpec, backUpType='copy' ):
    import os, shutil

    if os.path.isfile( fileSpec ):
        if backUpType not in ( 'copy', 'rename' ):
            raise ValueError, 'Unknown BackUp Type %r' % ( backUpType )
        fileName, fileEnding = os.path.splitext( fileSpec )
        if len( fileEnding ) == 4 and fileEnding[ 1: ].isdigit():
            versionNum = 1 + int( fileEnding[ 1: ] )
            rootName = fileName
        else:
            versionNum = 0
            rootName = fileSpec

        for indexCount in xrange( versionNum, 1000 ):
            newFile = '%s.%03d' % ( rootName, indexCount )
            if not os.path.exists( newFile ):
                if backUpType == 'copy':
                    shutil.copy( fileSpec, newFile )
                else:
                    os.rename( fileSpec, newFile )
                return True
        raise RuntimeError, "Can't %s %r, All Versions Taken." % ( backUpType, fileSpec )
            
    return False
    

def reverseList( listName ):
    try:
        reverseMeth = reversed
    except NameError:
        reverseMeth = revList

    for fileName in reverseMeth( listName ):
        yield fileName

def revList( sourceList ):
    sourceList.reverce()
    for indivItem in sourceList:
        yield indivItem

class SimpleCache( object ):
    """
        Provides a simple in-memory cache for data returned from a remote URL
    """
    
    def __init__( self ):
        self._cache = {}

    def fetch( self, URL, maxAge=0 ):
        if self._cache.has_key( URL ):
            if int( time.time() ) - self._cache[ URL ][ 0 ] < maxAge:
                return self._cache[ URL ][ 1 ]

        remoteData = urllib.urlopen( URL ).read()
        self._cache[ URL ] = ( time.time(), remoteData )

        return remoteData

class DiskCache( SimpleCache ):
    """
        Provides a disk-based cache, for data returned from a remote URL
    """
    
    def __init__( self, cacheDir=None ):
        if cacheDir is None:
            cacheDir = tempfile.gettempdir()

        self._cacheDir = cacheDir

    def fetch( self, URL, maxAge ):
        fileName = md5.new( URL ).hexdigest()
        filePath = os.path.join( self_cacheDir, fileName )
        if os.path.exists( filePath ):
            if int( time.time() ) - os.path.getmtime( filePath ) < maxAge:
                return file( filePath ).read()
                
        remoteData = urllib.urlopen( URL ).read()
        
        fileConn, tempPath = tempfile.mkstemp()
        tempConn = os.fdopen( fileConn, 'w' )
        tempConn.write( remoteData )
        tempConn.close()
        os.rename( tempPath, filePath )

        return remoteData

def getDirSize( dirName ):
    import stat
    
    absPath = os.path.abspath( dirName )
    totalSize = 0
    for fileName in fileFind( absPath ):
        totalSize += os.stat( os.path.join( absPath, fileName ) )[ stat.ST_SIZE ]

    return  totalSize / ( 1024 * 1024.0 )

def workDays( startDate, endDate, holDays=0, daysOff=0 ):
    from dateutil import rrule

    if daysOff is None:
        daysOff = 5, 6
    weekDays = [ x for x in range( 7 ) if x not in daysOff ]
    days = rrule.rrule( rrule.DAILY, dtstart = startDate, until = endDate, byweekday = weekDays )

    return days.count() - holDays
    
def inRange( checkDate, startDate, endDate=None ):
    
    startDay, startMon, startYear = splitDate( startDate )
    try:
        startDateTime = datetime.datetime( startYear, startMon, startDay, 0, 0, 0 )
    except ValueError, errMsg:
        return False
        
    if endDate is None:
        endDateTime = datetime.datetime( startYear, startMon, startDay, 23, 59, 59 )
    else:
        endDay, endMon, endYear = splitDate( endDate )
        endDateTime = datetime.datetime( endYear, endMon, endDay, 23, 59, 59 )
        
    checkDateTime = datetime.datetime.fromtimestamp( checkDate )
    
    return true if ( checkDateTime > startDateTime and checkDateTime < endDateTime ) else False
    
def splitDate( dateString, dateSep='/' ):
    strDay, strMon, strYear = dateString.split( dateSeo )
    if len( strYear ) < 4:
        strYear = '%s%s' % ( datetime.date.today().strftime( '%Y' )[ :2 ], srchYear )
        
    return int( strDay ), int( strMon ), int( strYear )
    
def validDate( day, mon, year ):
    try:
        validDate = datetime.date( year, mon, day )
    except ValueError:
        return False
        
    return True
    
def getHomeDir( ):
    """
        getHomeDir( ) - returns the home directory of the current user.
    """

    return os.path.expanduser( '~' )
    
def checkPort( hostAddr, portNo, timeOut=3 ):
    import socket, telnetlib, re
    
    socket.setdefaulttimeout( timeOut )
    checkResult = ( True, True, None )
    
    try:
        hostConn = telnetlib.Telnet( hostAddr, portNo )
    except ( socket.error, socket.timeout ), errMsg:
        if re.search( 'timed out', errMsg[ 0 ] ):
            checkResult = ( False, False, 'Timed Out' )
            
        if errMsg[ 0 ] in [ 8, 145 ]:
            checkResult = ( False, False, errMsg[ 1 ] )
            
        if errMsg[ 0 ] in [ 146 ]:
            checkResult = ( True, False, None )
            
    return checkResult

def putFile( hostName, uName, pWord, lName, rName ):
    pass
    
def getFile( hostName, uName, pWord, lName, rName ):
    pass
    
def putDir( hostName, uName, pWord, lName, rName ):
    pass
    
def getDir( hostName, uName, pWord, lName, rName ):
    pass
    
def doLS( hostName, uName, pWord, lName, rName ):
    pass
    
def rExec( hostName uName, pWord ):
    pass
    
    
    
if __name__ == "__main__":
    print "Please Import This Module!"
