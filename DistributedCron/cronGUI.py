#!/usr/local/bin/python
"""
    cronGUI.py - Does exactly what it says on the CLI.  It's a GUI for maintaining the distributed Cron.
    
"""

import os, Tkinter, tkMessageBox, sys

from PlusNet import Utils, DBStorage

class CronGUI( Tkinter.Frame ):

    def __init__( self, master=None ):
        Tkinter.Frame.__init__( self, master )
        self._dbInst = DBStorage.DBStorage( "Cron", "localhost", "MySQL", userName="admindb", passWord="Frodo" )
        self._dbInst.dbOpen()
        self.grid( )
        self.createWidgets( )

    def _getServerNames( self ):
        serverNames = []
        selectCursor = self._dbInst.getCursor()
        self._dbInst.execSQL( selectCursor, "SELECT hostName from Hosts;" )
        for indivName in self._dbInst.returnMany( selectCursor ):
            yield indivName
            
        
    def createWidgets( self ):
        self.QuitButton = Tkinter.Button( self )
        self.QuitButton["text"] = "Quit"
        self.QuitButton["fg"]  = "black"
        self.QuitButton["command"] =  self.quit
        self.QuitButton.grid( row=10, column=0 )
        
        self.yScrollLBS = YScrollBar( self )
        self.yScrollLBS.grid( row=0, column=1, sticky=Tkinter.N+Tkinter.S )
        self.ListBoxServers = Tkinter.Listbox( self, height=5, width=25, selectmode=Tkinter.BROWSE, yscrollcommand=self.yScrollLBS.set )
        for serverName in self._getServerNames():
            self.ListBoxServers.insert( Tkinter.END, serverName )
#        self.ListBoxServers.bind( '<Double-Button-1>', self._listCronEntries )
        self.ListBoxServers.grid( row=0, column=0, sticky=Tkinter.N+Tkinter.S )
        self.yScrollLBS[ "command" ] = self.ListBoxServers.yview 
        
        self.ListCronButton = Tkinter.Button( self )
        self.ListCronButton[ "text" ] = "List Cron Entries"
        self.ListCronButton[ "fg" ] = "black"
        self.ListCronButton[ "command" ] = self._listCronEntries
        self.ListCronButton.grid( row=0, column=10 )


        self.yScrollLBC = YScrollBar( self )
        self.ListBoxCrons = Tkinter.Listbox( self, height=5, width=65, selectmode=Tkinter.SINGLE, yscrollcommand=self.yScrollLBC.set )
        self.ListBoxCrons.grid( row=0, column=15, sticky=Tkinter.N+Tkinter.S )
        self.yScrollLBC[ "command" ] = self.ListBoxCrons.yview
        
    def _listCronEntries( self ):
        try:
            selectedHost = self.ListBoxServers.get( self.ListBoxServers.curselection()[ 0 ] )
        except IndexError:
            tkMessageBox.showerror( "No Selection", "Please Select A Host" )
            return
            
        self.ListBoxCrons.delete( 0, Tkinter.END )
        sqlToRun = """SELECT cronMinute, cronHour, cronDayOfMonth, cronMonth, cronDayOfWeek, cronCommandLine 
                    FROM CronEntries WHERE cronHost = ( SELECT hostID FROM Hosts WHERE hostName = '%s' );""" % selectedHost
        selectCursor = self._dbInst.getCursor()
        self._dbInst.execSQL( selectCursor, sqlToRun )
        for cronEntry in self._dbInst.returnMany( selectCursor ):
            self.ListBoxCrons.insert( Tkinter.END, cronEntry )
            
class YScrollBar( Tkinter.Scrollbar ):
    
    def __init__( self, instance, orient=Tkinter.VERTICAL ):
        Tkinter.Scrollbar.__init__( self, instance, orient=orient )
        
def main( ):
    cronGUIApp = CronGUI()
    cronGUIApp.master.title( "Distributed Cron Maintenance" )
    cronGUIApp.mainloop()
    
if __name__ == "__main__":
    print "Starting GUI For Distributed Cron....."
    sys.exit( main ( ) )
