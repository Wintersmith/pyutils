"""
    Filer.py - A lib designed to make NetApp's SDK a bit more friendly.

    Requires Python 3 ( I used @functools.lru_cache( maxsize=32 ) to provide a cache so that this function wouldn't be a heavy load on the filer, as it's used as part of a web app )
"""

from __future__ import print_function

import re, sys, logging, functools
from time import gmtime, strftime
from .NaServer import *
from . import Settings, Utils

haLabel = [ 'is-enabled', 'partner', 'state', 'is-interconnect-up' ]
filerLabel = [ 'system-name', 'system-model', 'system-machine-type', 'system-serial-number', 'board-type', 'number-of-processors', 'memory-size' ]
aggrLabel = [ 'state', 'mirror-status', 'size-total', 'size-used', 'size-percentage-used', 'size-available', 'raid-size', 'raid-status', 'is-checksum-available', 'checksum-status', 'is-inconsistent', 'disk-count', 'volume-count' ]
volLabel = [ 'name', 'state', 'size-total', 'size-used', 'percentage-used', 'snapshot-percent-reserved' ]
diskLabel = [ 'disk-type', 'shelf', 'bay', 'disk-model', 'aggregate', 'vendor-id' ]
lunLabel = [ 'size', 'online', 'mapped' ]
userLabel = [ 'comment' ]

class NetApp( object ):

    def __init__( self, filerHost ):
        self._filerConn = None
        self._filerHost = filerHost
        self._nfsList = []
        self._logFacility = logging.getLogger( Utils.returnScriptName() )

    def login( self ):
        self._filerConn = NaServer( self._filerHost, 1, 1 )
        self._filerConn.set_admin_user( Settings.filerUser, Settings.filerPasswd )

    def listSnapshots( self, vName ):
        snapList = []
        naReturn = self._filerConn.invoke( 'snapshot-list-info', 'volume', vName, 'terse', 'true' )
        self._logFacility.debug( "NetApp Invoke Results %d " % naReturn.results_errno() )
        if naReturn.results_errno() != 0:
            errMsg = naReturn.results_reason()
            self._logFacility.error( "Call To listSnapshots:snapshot-list-info Failed.  Reason: %s" % errMsg )
            return None

        for indivSnap in naReturn.child_get( 'snapshots' ).children_get():
            snapList.append( indivSnap.child_get_string( 'name' ) )
            self._logFacility.debug( "%s - %s - %s" % ( indivSnap.child_get_string( 'name' ), indivSnap.child_get_string( 'busy' ), strftime ( "%a, %d %b %Y %H:%M:%S", gmtime( indivSnap.child_get_int( 'access-time' ) ) ) ) )

        return snapList

    def createFlexClone( self, srcVol, snapName, fcName ):
        if self._filerConn is None:
            return False

        fcConn = NaElement( "volume-clone-create" )
        fcConn.child_add_string( "parent-volume", srcVol )
        fcConn.child_add_string( "parent-snapshot", snapName )
        fcConn.child_add_string( "volume", fcName )
       
        fcOutput = self._filerConn.invoke_elem( fcConn )
        if ( fcOutput.results_status() == "failed" ):
            self._logFacility.error( "Failed To Create Flexclone: %s, %s" % (  fcOutput.results_reason(), fcOutput.results_status() ) )
            return False

        return True

    def deleteFlexClone( self, fcName ):
        if self._filerConn is None:
            return False

        for apiCall in [ "volume-offline", "volume-destroy" ]:
            fcConn = NaElement( apiCall )
            fcConn.child_add_string( "name", fcName )
       
            fcOutput = self._filerConn.invoke_elem( fcConn )
            if ( fcOutput.results_status() == "failed" ):
                self._logFacility.error( "Failed To Delete Flexclone: %s, %s" % ( fcOutput.results_reason(), fcOutput.results_status() ) )
                return False

        return True

    def listiGroups( self, hostName ):
        hostGroups = []
        iGroupConn = NaElement( "igroup-list-info" )
        iGroupOut = self._filerConn.invoke_elem( iGroupConn )
        if iGroupOut.results_status() == "failed":
            self._logFacility.error( "Failed To List iGroups: %s" % iGroupOut.results_reason() )
            yield None

        iGroupInfo = iGroupOut.child_get( "initiator-groups" )
        iGroupList = iGroupInfo.children_get()
        for indivEntry in iGroupList:
            iGroupName = indivEntry.child_get_string( "initiator-group-name" )
            if re.search( hostName, iGroupName ):
                yield iGroupName

    def mapLun( self, fcName, hostNames, LunID ):
        baseLun = LunID
        lunConn = NaElement( "lun-map" )
        for iGroup in self.listiGroups( hostNames ):
            lunConn.child_add_string( "initiator-group", iGroup )
            lunConn.child_add_string( "lun-in", baseLun )
            baseLun += 1

        return baseLun
            

    def unMapLun( self, fcName ):
        pass

    def checkNFS( self, fcName ):
        exportList = self.listNFS()
        for indivExport in exportList:
            if re.search( fcName, indivExport ):
                return True

        return False

    def listNFS( self ):
        nfsList = []
        nfsConn = self._filerConn.invoke( "nfs-exportfs-list-rules" )
        exportConn = nfsConn.child_get( "rules" )
        if exportConn:
            exportInfo = exportConn.children_get()
            for exportDets in exportInfo:
                nfsList.append( exportDets.child_get_string( "pathname" ) )

            return nfsList

    def backUpVolume( self, volName, maxCount ):
        """
            backUpVolume - function will take a backup of the specified volName, cycling the snapshots, maintaining the limit passed.

            Be Warned, the function expects the snapshots to be named x.d where d is a number
        """

        oldestSnap = None

        self._logFacility.info( "Backing Up Volume %s, Maximum Snapshots %d" % ( volName, maxCount ) )
        snapList = self.listSnapshots( volName )
        if len( snapList ) > 0:
            lastSnap = snapList[ -1 ]
            self._logFacility.debug( "Last Snapshot For Volume %s, %s" % ( volName, lastSnap ) )
            reMatch = re.search( '.*\.(\d*)', lastSnap )
            if reMatch:
                oldestSnap = int( reMatch.group( 1 ) )
                self._logFacility.debug( "Setting oldestSnap ( 1 ) To %d" % oldestSnap )
                if oldestSnap >= maxCount:
                   for snapNo in reversed( range( maxCount, oldestSnap + 1 ) ):
                       self._deleteSnapshot( volName, "%s.snapshot.%d" % ( volName, snapNo ) )

                oldestSnap = maxCount
            else:
                self._logFacility.debug( "Setting oldestSnap ( 2 ) To %d" % maxCount )
                oldestSnap = maxCount

            self._rotateSnaps( volName, oldestSnap )
        else:
            self._logFacility.info( "No Snapshots Found For Volume %s" % volName )

        self._createSnapshot( volName, "%s.snapshot.1" % volName )

    def _rotateSnaps( self, volName, maxCount ):
        for snapNo in reversed( range( 1, maxCount ) ):
            self._renameSnapshot( volName, "%s.snapshot.%d" % ( volName, snapNo ), "%s.snapshot.%d" % ( volName, snapNo + 1 ) )


    def _createSnapshot( self, volName, snapName ):
        self._logFacility.debug( "Call _createSnapshot:snapshot-create. Args: %s, %s " % ( volName, snapName ) )
        naReturn = self._filerConn.invoke( 'snapshot-create', 'volume', volName, 'snapshot', snapName )
        if naReturn.results_errno() != 0:
            errMsg = naReturn.results_reason()
            self._logFacility.error( "Call To _createSnapshot:snapshot-create Failed.  Reason: %s ( %s )" % ( errMsg, snapName ) )
            return False

        return True

    def _renameSnapshot( self, volName, origName, newName ):
        self._logFacility.debug( "Call _renameSnapshot:snapshot-rename. Args: %s, %s, %s " % ( volName, origName, newName ) )
        naReturn = self._filerConn.invoke( 'snapshot-rename', 'volume', volName, 'current-name', origName, 'new-name', newName )
        if naReturn.results_errno() != 0:
            errMsg = naReturn.results_reason()
            self._logFacility.error( "Call To _renameSnapshot:snapshot-rename Failed.  Reason: %s ( %s / %s )" % ( errMsg, origName, newName ) )
            return False

        return True

    def _deleteSnapshot( self, volName, snapName ):
        self._logFacility.debug( "Call _deleteSnapshot:snapshot-delete. Args: %s, %s" % ( volName, snapName ) )
        naReturn = self._filerConn.invoke( 'snapshot-delete', 'volume', volName, 'snapshot', snapName )
        if naReturn.results_errno() != 0:
            errMsg = naReturn.results_reason()
            self._logFacility.error( "Call To _deleteSnapshot:snapshot-delete Failed.  Reason: %s ( %s )" % ( errMsg, snapName ) )
            return False

        return True

    @functools.lru_cache( maxsize=32 )
    def clusterStatus( self ):
        naReturn = self._filerConn.invoke( 'system-get-version' )
        if naReturn.results_errno() != 0:
            print( naReturn.results_reason() )
            return None

        naVersion = naReturn.child_get_string( 'version' )

    def haStatus( self ):
        haStat = {}
        naReturn = self._filerConn.invoke( 'cf-status' )
        if naReturn.results_errno() != 0:
            print( naReturn.results_reason() )
            return None

        for indivLabel in haLabel:
            haStat[ indivLabel ] = naReturn.child_get_string( indivLabel )

        return haStat
        
    def checkFiler( self ):
        filerDets = {}
        naReturn = self._filerConn.invoke( 'system-get-info' )
        if naReturn.results_errno() != 0:
            print( naReturn.results_reason() )
            return None
        for sysElem in naReturn.child_get( 'system-info' ).children_get():
            reMatch = re.search( '<(.*)>(.*)<.*>', sysElem.toEncodedString() )
            if reMatch:
                filerDets[ reMatch.group( 1 ) ] = reMatch.group( 2 )

        return filerDets

    def aggrDets( self, aggrName=None ):
        if aggrName is None:
            naReturn = self._filerConn.invoke( 'aggr-list-info' )
        else:
            naReturn = self._filerConn.invoke( 'aggr-list-info', 'aggregate', aggrName, 'verbose', 'true' )
        if naReturn.results_errno() != 0:
            print( naReturn.results_reason() )

        aggrInfo = naReturn.child_get( 'aggregates' )
        aggrDets = {}
        for indivAggr in aggrInfo.children_get():
            indivDets = {}
            for keyName in aggrLabel:
                indivDets[ keyName ] = indivAggr.child_get_string( keyName )
            if indivAggr.child_get_int( 'volume-count' ) > 0:
                aggrVolList = []
                for aggrVolInfo in indivAggr.child_get( 'volumes' ).children_get():
                    aggrVolList.append( aggrVolInfo.child_get_string( 'name' ) )
                indivDets[ 'volumes' ] = aggrVolList
            aggrDets[ indivAggr.child_get_string( 'name' ) ] = indivDets

        return aggrDets

    def volDets( self, volName=None ):
        if volName is None:
            naReturn = self._filerConn.invoke( 'volume-list-info' )
        else:
            naReturn = self._filerConn.invoke( 'volume-list-info', 'volume', volName )

        if naReturn.results_errno() != 0:
            print( naReturn.results_reason() )

        volInfo = naReturn.child_get( 'volumes' )
        volDets = {}
        for indivVol in volInfo.children_get():
            filerVol = {}
            for keyName in volLabel:
                filerVol[ keyName ] = indivVol.child_get_string( keyName )
            volDets[ indivVol.child_get_string( 'name' ) ] = filerVol

        return volDets

    def diskDets( self ):
        naReturn = self._filerConn.invoke( 'disk-list-info' )
        if naReturn.results_errno() != 0:
            print( naReturn.results_reason() )

        diskList = naReturn.child_get( 'disk-details' )
        diskDets = {}
        for indivDisk in diskList.children_get():
            diskInfo = {}
            for keyName in diskLabel:
                diskInfo[ keyName ] = indivDisk.child_get_string( keyName )
            diskDets[ indivDisk.child_get_string( 'name' ) ] = diskInfo

        return diskDets
 
    @functools.lru_cache( maxsize=32 )
    def getVersion( self ):
        naReturn = self._filerConn.invoke( 'system-get-version' )
        if naReturn.results_errno() != 0:
            print( naReturn.results_reason() )
            return None

        return naReturn.child_get_string( 'version' )

    def listLuns( self ):
        naReturn = self._filerConn.invoke( 'lun-list-info' )
        if naReturn.results_errno() != 0:
            print( naReturn.results_reason() )
            return None

        lunList = naReturn.child_get( 'luns' )
        lunInfo = {}
        for indivLun in lunList.children_get():
            lunDets = {}
            for indivLabel in lunLabel:
                lunDets[ indivLabel ] = indivLun.child_get_string( indivLabel )
            lunInfo[ indivLun.child_get_string( 'path' ) ] = lunDets

        return lunInfo

    @functools.lru_cache( maxsize=32 )
    def userList( self ):
        naReturn = self._execAPI( 'useradmin-user-list' )
        if not naReturn is None:
            userList = {}
            userInfo = naReturn.child_get( 'useradmin-users' )
            for indivUser in userInfo.children_get():
                userDets = {}
                userDets[ 'comment' ] = indivUser.child_get_string( 'comment' )
                grpInfo = indivUser.child_get( 'useradmin-groups' )
                grpList = []
                for indivGrp in grpInfo.children_get():
                    grpList.append( indivGrp.child_get_string( 'name' ) )
                userDets[ 'groups' ] = grpList
                userList[ indivUser.child_get_string( 'name' ) ] = userDets

            return userList
        return None

    def _execAPI( self, apiCall ):
        naReturn = self._filerConn.invoke( apiCall )
        if naReturn.results_errno() != 0:
            print( naReturn.results_reason() )
            return None

        return naReturn

if __name__ == '__main__':
    naConn = NetApp( 'devfiler' )
