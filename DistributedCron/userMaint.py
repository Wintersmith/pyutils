#!/usr/bin/env python
"""
    userMaint.py - Create users for use with the DistributedCron.
"""

import os, sys, getopt

try:
    from Crypto.Hash import MD5 as md5
    from Crypto.Hash import SHA as sha
except ImportError:
    import md5, sha

from PlusNet import DBStorage, Utils

def addUser( configSettings, userName, passWord ):
    dbInst = DBStorage.DBStorage( "Cron", configSettings[ 'dbhost' ], configSettings[ 'dbtype' ], 
                                            userName=configSettings[ 'dbuser' ], passWord=configSettings[ 'dbpass' ] )
    dbInst.dbOpen()
    instanceCursor = dbInst.getCursor()
    sqlToRun = "SELECT userName FROM Users WHERE userName = '%s';" % userName
    dbInst.execSQL( instanceCursor, sqlToRun )
    retRow = dbInst.returnSingle( instanceCursor )
    if retRow is None:
        print "Adding User: %s" % userName
        sqlToRun = "INSERT INTO Users VALUES( NULL, '%s', '%s' );" % ( userName, sha.new( passWord ).digest() )
        dbInst.execSQL( instanceCursor, sqlToRun )
    else:
        print "Updating Password For User: %s" % userName
        dbInst.execSQL( instanceCursor, "UPDATE Users SET userPassWord = '%s';" % sha.new( passWord ).digest() )

def main( argv=None ):
    if argv is None:
        argv = sys.argv
    try:
        try:
            opts, args = getopt.getopt( argv[1:], "c:u:p:h", [ "config", "user", "pwd", "help" ] )
        except getopt.error, msg:
            raise Utils.Usage( msg )

        configFile = None
        userName = None
        passWord = None

        for cliOpts, cliArgs in opts:
            if cliOpts in ( "-c", "--config" ):
                configFile = cliArgs

            if cliOpts in ( "-u", "--user" ):
                userName = cliArgs

            if cliOpts in ( "-p", "--pwd" ):
                passWord = cliArgs

            if cliOpts in ( "-h", "--help" ):
                DisplayUsage()
                return 2

        if configFile is None:
            print "A Config File Is Required."
            return 2

        if ( userName or passWord ) is None:
            print "UserName And PassWord Are Required!"
            return 2

        configSettings = Utils.loadConfig( configFile )

        if not configSettings is None:
            addUser( configSettings, userName, passWord )
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
    sys.exit( main() )
