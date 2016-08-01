#!/usr/local/bin/python
"""
    cron.cgi:  This page deals listing/adding/deleting cron entries.
    
"""
# System Imports
import cgi, os, Cookie, time

# Custom Imports
import DBStorage, Utils

htmlStart = """Content-type: text/html

<HTML>
<HEAD>
    <TITLE>Distributed Cron Maintenance</TITLE>
</HEAD>
<BODY>"""

htmlFormStart = """<FORM ACTION = "/cgi-bin/cron.cgi" METHOD="POST">"""

htmlFormList = """<SELECT NAME="%s" SIZE=%d><BR>"""

htmlFormBody = """
Enter Minutes: <INPUT TYPE="text" NAME="cronMin" SIZE=25 VALUE="*" MAXLENGTH=255 ><BR>
Enter Hours: <INPUT TYPE="text" NAME="cronHours" SIZE=25 VALUE="*" MAXLENGTH=255 ><BR>
Enter Day(s) Of Month: <INPUT TYPE="text" NAME="cronDOM" SIZE=25 VALUE="*" MAXLENGTH=255 ><BR>
Enter Month: <INPUT TYPE="text" NAME="cronMonth" SIZE=25 VALUE="*" MAXLENGTH=255 ><BR>
Enter Day Of Week: <INPUT TYPE="text" NAME="cronDOW" SIZE=25 VALUE="*" MAXLENGTH=255 ><BR>
Enter Command Line: <INPUT TYPE="text" NAME="cronCLI" SIZE=75 MAXLENGTH=255 ><BR>
Enter User ID: <INPUT TYPE="text" NAME="cronUID" SIZE=5 MAXLENGTH=5 VALUE=0 ><BR>
<INPUT TYPE="submit" VALUE="Submit Cron Entry">
<INPUT TYPE="reset"  VALUE="Reset Fields To Default"><BR>
"""

loginForm = """
<center>
<FORM ACTION = "/cgi-bin/cron.cgi" METHOD="POST">
<table border="0" cellpadding="0" cellspacing="0" width="300">
  <tbody>
    <tr>
      <td bgcolor="#CCCCCC" style="width: 75%; text-align: center;">UserName</td>
      <td><INPUT TYPE="text" NAME="cronUser" SIZE=25 MAXLENGTH=64></td>
    </tr>
    <tr>
      <td bgcolor="#CCCCCC" style="width: 75%; text-align: center;">Password</td>
      <td><INPUT TYPE="password" NAME="cronPassword" SIZE=25 MAXLENGTH=32></td>
    </tr>
    <tr>
      <td style="width: 75%; text-align: right;"></td>
      <td><INPUT TYPE="submit" VALUE="Login"></td>
    </tr>"""

loginFormError = """
    <tr>
        <td colspan="2" style="width: 75%; text-align: right;">%s</td>
    </tr>

"""

loginFormEnd = """
  </tbody>
</table>
</form>
</center>

"""

htmlEnd = """</BODY>
</HTML>"""

startTable = """
<TABLE WIDTH=100% BORDER=1 CELLPADDING=0 CELLSPACING=0>
    <TBODY>
        <TR VALIGN=TOP>
        <TD>Mins</TD><TD>Hours</TD><TD>Days Of Month</TD><TD>Month</TD><TD>Days Of Week</TD><TD>Command Line</TD><TD>UID</TD><TD>Delete</TD></TR><TR VALIGN=TOP>

"""

startTableRow = """
    <TD>
"""

endTableRow = """</TD>"""

endTable = """
    </TBODY>
</TABLE><BR>
"""

def executeSQL( dbInst, sqlToExec ):
    execCursor = dbInst.getCursor()
    dbInst.execSQL( execCursor, sqlToExec )
    for hostData in dbInst.returnMany( execCursor ):
        yield hostData

def returnEntriesForHost( dbInst, cronHost ):
    execCursor = dbInst.getCursor()
    dbInst.execSQL( execCursor, retAllhosts )
    for cronEntries in dbInst.returnMany( execCursor ):
        yield cronEntries
    
def logChange( ):
    remoteAddr = os.environ[ 'REMOTE_ADDR' ]

def fieldToDict( fieldStorage ):
    cgiParams = {}
    for cgiKey in fieldStorage:
        cgiParams[ cgiKey ] = fieldStorage[ cgiKey ].value

    return cgiParams

def verifyDetails( dbInst, userName, passWord ):
    import sha
    
    selectCursor = dbInst.getCursor()
    dbInst.execSQL( selectCursor, "SELECT userName, userPassWord FROM Users WHERE userName = '%s';" % userName )
    retRow = dbInst.returnSingle( selectCursor )
    if not retRow is None:
        if retRow[ 1 ] == sha.new( passWord ).digest():
            return True, None
            
    return False, "Login Failed, ReEnter Login Details"
    
if __name__ == "__main__":
    doLogin = True
    errMsg = None
    import cgitb; cgitb.enable()
    
    configSettings = Utils.loadConfig( os.path.join( os.environ[ 'PATH_TRANSLATED' ], "config.cfg" ) )
    if not configSettings is None:
        dbInst = DBStorage.DBStorage( "Cron", configSettings[ 'dbhost' ], configSettings[ 'dbtype' ], 
                                                            userName=configSettings[ 'dbuser' ], passWord=configSettings[ 'dbpass' ] )
    else:
        print htmlStart
        print "There Has Been An Error Loading The Config File."
        print htmlEnd
        sys.exit()
        
    dbInst.dbOpen()
    localCookie = Cookie.SimpleCookie()

    try:
        localCookie.load( os.environ[ 'HTTP_COOKIE' ] )
    except:
        pass
            
    if 'cronUser' in localCookie:
        cronUser = localCookie[ 'cronUser' ].value
        lastLogin = int( localCookie[ 'cronTime' ].value )
        timeDiff = int( time.time() ) - lastLogin
        if timeDiff < 300:
            doLogin = False
    
    cgiParams = fieldToDict( cgi.FieldStorage() )
    if os.environ[ 'REQUEST_METHOD' ] == "POST":
        if 'cronUser' in cgiParams:
            loginStatus, errMsg = verifyDetails( dbInst, cgiParams[ 'cronUser' ], cgiParams[ 'cronPassword' ] )
            if loginStatus:
                localCookie[ 'cronUser' ] = cgiParams[ 'cronUser' ]
                localCookie[ 'cronTime' ] = int( time.time() )
                os.environ[ 'HTTP_COOKIE' ] = str( localCookie )
                print localCookie
                doLogin = False
    print htmlStart
    if doLogin:
        print loginForm
        if not errMsg is None:
            print '<tr> <td colspan="2" style="text-align: center;">%s</td> </tr>' % errMsg

            print loginFormEnd

    else:
        displayEntries = False
        if 'cronHost' in cgiParams:
            selectCursor = dbInst.getCursor()
            dbInst.execSQL( selectCursor, """SELECT hostID FROM Hosts WHERE hostName = '%s'""" % cgiParams[ 'cronHost' ] )
            _hostFound = False
            while _hostFound == False:
                for retRow in dbInst.returnMany( selectCursor ):
                    hostID =  retRow[ 0 ]
                    _hostFound = True
                    break
            if 'listCron'in cgiParams:
                sqlToRun = """SELECT cronMinute, cronHour, cronDayOfMonth, cronMonth, cronDayOfWeek, cronCommandLine, cronUID, cronID 
                                FROM CronEntries WHERE cronHost = %d AND cronActive = 1;""" % int( hostID ) 
                displayEntries = True
            elif 'deleteCron' in cgiParams:
                sqlToRun = "UPDATE CronEntries SET cronActive = 0 WHERE cronID = %d" % int( cgiParams[ 'delCron' ] )
            else:
                sqlToRun = "INSERT INTO CronEntries VALUES ( NULL, %d, '%s', '%s', '%s', '%s', '%s', '%s', 1, '', '%s', 0 )" % \
                                        ( int( hostID ), cgiParams[ 'cronMin' ], cgiParams[ 'cronHours' ], cgiParams[ 'cronDOM' ], cgiParams[ 'cronMonth' ], \
                                        cgiParams [ 'cronDOW' ], cgiParams[ 'cronCLI' ], cgiParams[ 'cronCLI' ] )
            mainCursor = dbInst.getCursor()
            dbInst.execSQL( mainCursor, sqlToRun )
    
                
        print htmlFormStart
        print htmlFormList % ( "cronHost", 1 )
        for hostName in executeSQL( dbInst, "SELECT hostName FROM Hosts;" ):
            print "<OPTION>%s" % hostName[ 0 ]
        print """</SELECT><INPUT TYPE="submit" NAME="listCron" VALUE="List CronEntries"><BR><BR>"""
        if displayEntries:
            print startTable
            for cronEntries in executeSQL( dbInst, sqlToRun ):
                for fieldCount in range( 0,7 ):
                    print startTableRow, "%s" % cronEntries[ fieldCount ]
                    print endTableRow
                print startTableRow, """<INPUT TYPE=RADIO NAME=delCron value="%d">""" % cronEntries[ 7 ], endTableRow
                print "</TR>"
            print endTable
            print """<INPUT TYPE="submit" NAME="deleteCron" VALUE="Delete CronEntries"><BR><BR>"""
            print htmlFormBody

    
    print htmlEnd


