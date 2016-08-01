import MySQLdb

if __name__ == "__main__":
    dbConn = MySQLdb.connect( user='', passwd='', db='Cron', host='192.168.70.2' );
    dbCursor = dbConn.cursor()
    for machineName in file( "/home/john/Hosts" ):
        dbCursor.execute( """INSERT INTO Hosts VALUES ( NULL, %s ) """, ( machineName.strip().lower(), ) )
        
