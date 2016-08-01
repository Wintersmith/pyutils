"""
    DBStorage.py
    
    A module to handle various types of DB
    
    Requires:
        Python 2.3

    Supported DBs:
        Gadfly
        SQLite
        SAP DB
        MySQL
    
"""

import os, os.path, sys

import MySQLdb, _mysql_exceptions

import warnings
warnings.filterwarnings( "ignore", "DB-API extension" )

class DBError( Exception ):
    
    def __init__( self, *args ):
        Exception.__init__( self, *args )
        
class DBStorage( object ):
    
    sqlProcs = [ 'execSQL', 'getCursor' ]
    
    def __init__( self, dbName, dbPath, dbType, userName = None, passWord = None, mode=0755 ):
        """
            This is called with the following parameters:
                dbName - Name Of DB To Open
                dbPath - With Gadfly/Sqlite This Is The File Path To The DB.  For SAPDB/MySQLdb This Is The Server Hostname
                dbType - Current Supported DB's Are Gadfly/SQLite/SAPDB/MySQLdb
                userName- User To Connect To DB As
                passWord - Password For Connecting User
                mode - In The Case Of SQLite, 0755 = Read/Write - 044 = Read Only
        """
        
        self.dbName = dbName
        self.dbPath = dbPath
        self.dbType = dbType
        self.userName = userName
        self.passWord = passWord
        self.openMode = mode
        self._dbConn = None
        
    def dbOpen( self ):
        funcToCall = getattr( self, "_%sOpen" % self.dbType.lower() )
        if funcToCall:
            self._dbConn = funcToCall()
        else:
            raise DBError ( "The DB %s Is Not Currently Supported" % self.dbType )
        
    
    def _gadflyOpen( self ):
        
        try:
            import gadfly
        except ImportError:
            raise DBError( "The Module %s Doesn't Seem To Be Installed." % self.dbType )

        if os.path.exists( self.dbPath ) and os.path.isdir( self.dbPath ):
            try:
                initConn = gadfly.gadfly( self.dbName, self.dbPath )
            except IOError:
                initConn = gadfly.gadfly()
                try:
                    initConn.startup( self.dbName, self.dbPath )
                except:
                    raise
                else:
                    self.initDB( initConn )
        else:
            raise DBError( "The Path %s Does Not Exist." % self.dbPath )

        return initConn
    
    def _sqliteOpen( self ):
        """
            Function to handle opening of SQLite DB's.  Connects to the DB, with a timeout of 2 seconds.
        """
        try:
            import sqlite3 as sqlite
        except ImportError:
            try:
                from pysqlite2 import dbapi2 as sqlite
            except ImportError:
                DBError( "The Module %s Doesn't Seem To Be Installed." % self.dbType )

        dbConn = sqlite.connect( database = os.path.join( self.dbPath, self.dbName ), timeout = 2 )
        return dbConn
        
        
    def _sapdbOpen( self ):
        try:
            from sapdb import dbapi
        except ImportError:
            raise DBError( "The Module %s Doesn't Seem To Be Installed." % self.dbType )
        
        try:
            dbConn = dbapi.connect( self.userName.upper(), self.passWord.upper(), self.dbName, host=self.dbPath )
        except dbapi.ProgrammingError, ErrorMsg:
            print "Nooo!!! %s" % ErrorMsg
            sys.exit( 2 )
            
        return dbConn
        
    def _mysqlOpen( self ):
        
        try:
            dbConn = MySQLdb.connect( user=self.userName, passwd=self.passWord, db=self.dbName, host=self.dbPath )
        except _mysql_exceptions.OperationalError, errorMsg:
            raise DBError( "Failed To Connect.  Reason: %s " % errorMsg )
            
        return dbConn

    def dbClose( self ):
        self._dbConn.close()

    def initDB( self, dbConn ):
        """
            This function is to be over-ridden.  It is used to initialise the DB.  In the case of Gadfly, it is called automatically
            if the DB doesn't exist.
        """
        pass
    
    def getCursor( self ):
        return self._dbConn.cursor()

    def commit( self ):
        self._dbConn.commit()

        
    def execSQL( self, dbCursor, sqlToExec ):
        try:
            dbCursor.execute( sqlToExec )
        except ( _mysql_exceptions.ProgrammingError, _mysql_exceptions.OperationalError ), errorMsg:
            raise DBError( "Unable To Execute SQL.  Reason %s" % errorMsg )
            
    def returnMany( self, dbCursor, arraySize=100 ):
        retDone = False
        while not retDone:
            retRows = dbCursor.fetchmany( arraySize )
            if retRows == [] or retRows == ():
                retDone = True
            for retRow in retRows:
                yield retRow

    def returnSingle( self, dbCursor ):
        return dbCursor.fetchone()
        
def testDB():
    pass
    
if __name__ == "__main__":
    print "Testing"
    testDB()
