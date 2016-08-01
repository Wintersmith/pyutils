#!/usr/local/bin/python
"""

    crona.py - This is an albatross version of cron.cgi
    
"""
# Imports From StdLib
import cgi, os

# Imports From Additional Modules
from albatross import SimpleContext

# Custom Imports
from PlusNet import DBStorage, Utils

def returnHostID( dbConn ):
    hostList = []
    
    selCursor = dbConn.getCursor()
    dbConn.execSQL( selCursor, "SELECT hostID, hostName FROM Hosts;" )
    for hostID, hostName in dbInst.returnMany( selCursor ):
        hostList.append( ( hostID, hostName ) )
        
    return hostList

def fieldToDict( fieldStorage ):
    cgiParams = {}
    for cgiKey in fieldStorage:
        cgiParams[ cgiKey ] = fieldStorage[ cgiKey ].value

    return cgiParams

    
if __name__ == "__main__":
    import cgitb; cgitb.enable()
    
    configSettings = Utils.loadConfig( os.path.join( os.environ[ 'PATH_TRANSLATED' ], "config.cfg" ) )
    if not configSettings is None:
        dbInst = DBStorage.DBStorage( "Cron", configSettings[ 'dbhost' ], configSettings[ 'dbtype' ], 
                                                            userName=configSettings[ 'dbuser' ], passWord=configSettings[ 'dbpass' ] )
    dbInst.dbOpen()
    
    userForm = cgi.FieldStorage()
    frmContext = SimpleContext( 'cgi-bin/' )

    cgiDict = fieldToDict( userForm )
    
    frmContext.locals.userForm = userForm
    frmContext.locals.hostList = returnHostID( dbInst )
    
    for fieldName in userForm.keys():
        if type( userForm[ fieldName ] ) is type( [] ):
            fieldValue = []
            for elem in userForm[ fieldName ]:
                fieldValue.append( elem.value )
        else:
            fieldValue = userForm[ fieldName ].value
        setattr(frmContext.locals, fieldName, fieldValue)

    if 'cronHost' in cgiDict:
        sqlToRun = """SELECT cronMinute, cronHour, cronDayOfMonth, cronMonth, cronDayOfWeek, cronCommandLine, cronUID, cronID 
                                                            FROM CronEntries WHERE cronHost = %d AND cronActive = 1;""" % int( cgiDict[ 'cronHost' ] )
        selCursor = dbInst.getCursor()
        dbInst.execSQL( selCursor, sqlToRun )
        tempField = [ cronEntry for cronEntry in dbInst.returnMany( selCursor ) ]
        frmContext.locals.cronEntries = tempField
    else:
        frmContext.locals.cronEntries = []
        tempField = []
        
    htmlTemplate = frmContext.load_template( 'form.html' )
    htmlTemplate.to_html( frmContext )

    print 'Content-Type: text/html'
    print

    frmContext.flush_content()

