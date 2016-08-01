#!/usr/local/bin/python

"""
    listEntries.py
    
    This program will list the cron entries stored in the DB the host on which the program is run.
    
"""
import sys, getopt

from PlusNet import Utils, DBStorage

def listEntries( configSettings ):
    cronStatus = { 0: "Inactive", 1: "Active" }
    hostName = Utils.returnHostName()
    dbInst = DBStorage.DBStorage( "Cron", configSettings[ 'dbhost' ], configSettings[ 'dbtype' ], 
                                                                    userName=configSettings[ 'dbuser' ], passWord=configSettings[ 'dbpass' ] )
    dbInst.dbOpen()
    _hostFound = False
    selectCursor = dbInst.getCursor()
    dbInst.execSQL( selectCursor, "SELECT hostID FROM Hosts WHERE hostName = '%s';" % hostName )
    while _hostFound == False:
        for retRow in dbInst.returnMany( selectCursor ):
            hostID =  retRow[ 0 ]
            _hostFound = True
            break
    if _hostFound is True:
        print "HostName Is %s, HostID Is %s" % ( hostName, str( hostID ) )
        dbInst.execSQL( selectCursor, """SELECT cronMinute, cronHour, cronDayOfMonth, cronMonth, cronDayOfWeek, cronCommandLine, cronActive 
                                                                                FROM CronEntries WHERE cronHost = ( %d );""" % hostID )
        for cronEntry in dbInst.returnMany( selectCursor ):
            print "%s - %s - %s - %s - %s \t %s - %s" % ( cronEntry[ 0 ], cronEntry[ 1 ], cronEntry[ 2 ], cronEntry[ 3 ], cronEntry[ 4 ], cronEntry[ 5 ],
                                                    cronStatus[ cronEntry[ 6 ] ] )
    else:
        print "The Host Does Not Exist In The DB"

def main( argv=None ):
    if argv is None:
        argv = sys.argv
        try:
            try:
                opts, args = getopt.getopt( argv[1:], "c:h", [ "config", "help" ] )
            except getopt.error, msg:
                raise Utils.Usage( msg )
                
            configFile = None
            
            for cliOpts, cliArgs in opts:
                if cliOpts in ( "-c", "--config" ):
                    configFile = cliArgs

                if cliOpts in ( "-h", "--help" ):
                    DisplayUsage()
                    return 2
                    
            if configFile is None:
                print "A Config File Is Required."
                return 2
                    
            configSettings = Utils.loadConfig( configFile )
                
            if not configSettings is None:
                listEntries( configSettings )
            else:
                print "There Was A Problem Loading The Config File."
                return 2
            
        except Utils.Usage, err:
            print >>sys.stderr, err.msg
            print >>sys.stderr, "for help use --help"
            
        return 2

def DisplayUsage( ):
    print "Usage:"
    print "crond -c/--crontab Path/Name Of Crontab File - DO NOT USE!  -h/--help Displays This Message"
    print "\nRun this script with no flags, to unleash it's full capabilities."
    
if __name__ == "__main__":
    sys.exit( main( ) )

