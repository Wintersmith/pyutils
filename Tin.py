import os, sys
import Utils

class Server( object ):

    def __init__( self, hostName, userName ):
        self._sshConn = Utils.RemoteCommand( hostName, userName )
