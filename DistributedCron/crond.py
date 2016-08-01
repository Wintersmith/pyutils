#!/usr/local/bin/python
"""
    crond.py
    
    This is a Python implementation of the *nix cron system.
    
    Requires Python2.4 or greater. ( Python2.3 + subprocess module avilable from effbot.org will run it, too ) 
    
    History:
    
    22 April, 2005: v0.1 - Initial release.  Supports crontab files.
    10 May, 2005: v0.2 - Added RDBMS support.
    
        
"""
# System imports
import sys, logging
import getopt

# Custom imports
from Cron import CronLib
from PlusNet import Utils, Platform

def main( argv=None ):
    if argv is None:
        argv = sys.argv
    try:
        try:
            opts, args = getopt.getopt( argv[1:], "dC:c:h", [ "debug", "config", "crontab", "help" ] )
        except getopt.error, msg:
            raise Utils.Usage( msg )
            
        debugMode = configFile = crontabFile = None
        
        for cliOpts, cliArgs in opts:
            if cliOpts in ( "-c", "--crontab" ):
                crontabFile = cliArgs

            if cliOpts in ( "-d", "--debug" ):
                debugMode = True

            if cliOpts in ( "-C", "--config" ):
                configFile = cliArgs

            if cliOpts in ( "-h", "--help" ):
                DisplayUsage()
                return 2
                
        if not Platform.isRunning():
            Utils.initLogging( logLevelNo=3 )
            logFacility = logging.getLogger( Utils.returnScriptName( ) )
            
            if configFile is None:
                print "A Config File Is Required."
                return 2
                
            configSettings = Utils.loadConfig( configFile )
            
            if not debugMode:
                if not Utils.makeDaemon():
                    logFacility.error( "Failed To Daemonize.  Running In The Foreground. " )
                    print "Failed To Daemonize.  Going To Run In The Foreground."
                
            if crontabFile is None:
                if not configSettings is None:
                    cronDaemon = CronLib.CronSQL( configSettings )
                else:
                    print "There Was A Problem Loading The Config File.  Check The Log File."
                    return 2
            else:
                try:
                    cronDaemon = CronLib.CronFile( crontabFile )
                except CronLib.CronError, errorMsg:
                    logFacility.error( "Failed To Start crond.  Reason: %s \n" % errorMsg )
                    print "Failed To Start crond.  Reason: %s \n" % errorMsg
                    return 1
                
            cronDaemon.run()
        else:
            print "There Is Already An Instance Of This Script Running!."
        
    except Utils.Usage, err:
        print >>sys.stderr, err.msg
        print >>sys.stderr, "for help use --help"
        
    return 2

def DisplayUsage( ):
    print "Usage:"
    print "crond -C/--config Config File  -h/--help Displays This Message"
    print "\nRun this script with no flags, to unleash it's full capabilities."
    
if __name__ == "__main__":
    sys.exit( main( ) )

