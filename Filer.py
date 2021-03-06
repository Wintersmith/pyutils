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

    def __init__( self, filerHost, dryRun = False ):
        self._filerConn = None
        self._filerHost = filerHost
        self._nfsList = []
        self._logFacility = logging.getLogger( Utils.returnScriptName() )
        self._dryRun = dryRun

    def login( self ):
        if self._dryRun: return True
        
        try:
            self._filerConn = NaServer( self._filerHost, 1, 1 )
            filerResp = self._filerConn.set_style( 'LOGIN' )
            if filerResp and filerResp.result_errno() != 0:
                filerError = filerResp.results_reason()
                self._logFacility.error( "Failed On Call To login:set_style.  Reason: %s " % filerError)
                return False
                
            self._filerConn.set_admin_user( Settings.filerUser, Settings.filerPasswd )
            filerRep = self._filerConn.set_transport_type( 'HTTP' )
            if filerResp and filerRespt.result_errno() != 0:
                filerError = filerResp.results_reason()
                self._logFacility.error( "Failed On Call To login:set_transport_type.  Reason: %s " % filerError )
                return False
                
        except Exception as errMsg:
            self._logFacility.error( "Call To login:set_admin_user Failed.  Reason: %s" % errMsg )
            return False
        return True

    def listSnapshots( self, vName ):
        """
            listSnapshots - vName - expects to be passed the volume name, and will then list all snapshot for that volume.  It will exclude all snapshots that don't contain the volume name
                                    so that system snapshots ( if enabled ) don't interfere with the backups.  The name / status / date of each snapshot that matches is logged, as well.
        """
        if self._filerConn is None:
            return False

        snapList = []
        naReturn = None
        try:
            naReturn = self._filerConn.invoke( 'snapshot-list-info', 'volume', vName, 'terse', 'true' )
        except Exception as errMsg:
            self._logFacility.error( "Error Encountered In listSnapshots:snapshot-list-info on %s - %s" % ( vName, errMsg ) )
            return []
            
        self._logFacility.debug( "NetApp Invoke Results %s " % naReturn.results_errno() )
        if naReturn.results_errno() != 0:
            errMsg = naReturn.results_reason()
            self._logFacility.error( "Call To listSnapshots:snapshot-list-info Failed.  Reason: %s" % errMsg )

        else:
            try:
                for indivSnap in naReturn.child_get( 'snapshots' ).children_get():
                    snapName = indivSnap.child_get_string( 'name' )
                    if re.search( vName, snapName ):
                        snapList.append( snapName )
                        self._logFacility.info( "    %s - %s - %s" % ( snapName, indivSnap.child_get_string( 'busy' ), strftime ( "%a, %d %b %Y %H:%M:%S", gmtime( indivSnap.child_get_int( 'access-time' ) ) ) ) )
            except Exception as errMsg:
                self._logFacility.error( "Call To listSnapshots:child_get:snapshots Is None" )

        return snapList

    def createFlexClone( self, srcVol, fcName, snapShot = 1 ):
        if self._filerConn is None:
            return False

        snapName = '%s.snapshot.%s' % ( srcVol, str( snapShot ) )
        
        self._logFacility.info( 'Creating A FlexClone, %s, %s' % ( srcVol, fcName ) )
        fcConn = NaElement( "volume-clone-create" )
        fcConn.child_add_string( "parent-volume", srcVol )
        fcConn.child_add_string( "parent-snapshot", snapName )
        fcConn.child_add_string( "volume", fcName )
       
        fcOutput = self._filerConn.invoke_elem( fcConn )
        if ( fcOutput.results_status() == "failed" ):
            self._logFacility.error( "Failed To Create Flexclone: %s, %s" % (  fcOutput.results_reason(), fcOutput.results_status() ) )
            return False
        self._logFacility.info( 'FlexClone %s Created' % fcName )
        
        return True

    def deleteFlexClone( self, fcName ):
        if self._filerConn is None:
            return False

        for apiCall in [ "volume-offline", "volume-destroy" ]:
            self._logFacility.info( 'Performing %s On FlexClone %s' % ( apiCall, fcName ) )
            fcConn = NaElement( apiCall )
            fcConn.child_add_string( "name", fcName )
       
            fcOutput = self._filerConn.invoke_elem( fcConn )
            if ( fcOutput.results_status() == "failed" ):
                self._logFacility.error( "Failed To Delete Flexclone: %s, %s" % ( fcOutput.results_reason(), fcOutput.results_status() ) )
                return False
            self._logFacility.info( 'Action %s On FlexClone %s Successful' % ( apiCall, fcName ) )

        return True

    def listiGroups( self, hostName ):
        if self._filerConn is None:
            return False
            
        trueHost = Utils.getHostName( hostName )
        self._logFacility.info( "True Hostname = %s" % trueHost )
        hostGroups = []
        naReturn = self._filerConn.invoke( 'igroup-list-info' )
        if naReturn.results_status() == "failed":
            self._logFacility.error( "Failed To List iGroups: %s" % naReturn.results_reason() )
            yield None

        iGroupInfo = naReturn.child_get( "initiator-groups" )
        if not iGroupInfo is None:
            iGroupList = iGroupInfo.children_get()
            for indivEntry in iGroupList:
                iGroupName = indivEntry.child_get_string( "initiator-group-name" )
                reHost = '%s.*' % trueHost
                reMatch = re.search( reHost, iGroupName )
                if reMatch:
                    yield iGroupName

    def mountVolume( self, fcName ):
        if self._filerConn is None:
            return False
            
    def getLunPath( self, volName, indivVol ):
        """
            getLunPath - this function sucks, the idea was to return only the luns for the given volume, but the call to lun-list-info kept erroring saying volume-name was invalid / unexpected.
        """
        if self._filerConn is None:
            return None
            
        print( "Listing Luns For %s" % volName )
        lunList = []

        partPath = '/vol/%s' % volName
        naReturn = self._filerConn.invoke( "lun-list-info" )
        if naReturn.results_status() == "failed":
            self._logFacility.error( 'Failed To Execute lun-list-info, %s' % naReturn.results_reason() )
            return lunList
            
        for indivLun in naReturn.child_get( 'luns' ).children_get():
            indivPath = indivLun.child_get_string( 'path' )
            self._logFacility.debug( "Found Lun In Volune, %s" % indivpath)
            reMatch = re.search( indivVol, indivPath )
            if reMatch:
                return indivPath
                
        return None
        
            
    def mapLun( self, fcName, iGroups, lunID ):
        if self._filerConn is None:
            return False

        self._logFacility.debug( "About to lun-map, args - %s / %s / %s" % ( fcName, iGroups, str( lunID) ) )
        lunCmd = NaElement( "lun-map" )
        for iGroup in iGroups:
            self._logFacility.debug( "Adding %s To iGroup" % iGroup )
            lunCmd.child_add_string( "initiator-group", iGroup )
            self._logFacility.debug( "Adding %s To LunID" % lunID )
            lunCmd.child_add_string( "lun-id", lunID )
            self._logFacility.debug( "Adding %s To Path" % fcName )
            lunCmd.child_add_string( "path", fcName )
        naReturn = self._filerConn.invoke_elem( lunCmd )
        if naReturn.results_status() == "failed":
            self._logFacility.error( "Failed to map lun %s to %s with id %s, %s" % ( fcName, iGroups, lunID, naReturn.results_reason() ) )
            return False

        self._logFacility.debug( "About to lun-online, args - %s" % fcName )
        lunCmd = NaElement( "lun-online" )
        lunCmd.child_add_string( "path", fcName )
        naReturn = self._filerConn.invoke_elem( lunCmd )
        self._logFacility.error( "Filer Return, %s " % naReturn.results_status() )
        if naReturn.results_status() == "failed":
            self._logFacility.error( "Unable to online lun %s, %s" % ( fcName, naReturn.results_reason() ) )
            return False
            
        return True
            

    def unMapLun( self, fcName ):
        pass

    def isNFS( self, fcName ):
        if self._filerConn is None:
            return False

        exportList = self.listNFS()
        for indivExport in exportList:
            if re.search( fcName, indivExport ):
                return True

        return False

    def listNFS( self ):
        if self._filerConn is None:
            return False

        nfsList = []
        naReturn = None
        try:
            naReturn = self._filerConn.invoke( "nfs-exportfs-list-rules" )
        except Exception as errMsg:
            self._logFacility.error( "Call To listNFS:nfs-exportnfs-list-rules Raised Exception: %s" % errMsg )
            return nfsList
            
        if naReturn.results_errno() != 0:
            errMsg = naReturn.results_reason()
            self._logFacility.error( "Call To listNFS:nfs-exportnfs-list-rules Returned Error: %s" % errMsg )
        else:
            exportConn = naReturn.child_get( "rules" )
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
        if self._filerConn is None:
            return False

        oldestSnap = None
        self._logFacility.info( "Backing Up Volume %s, Maximum Snapshots %d" % ( volName, maxCount ) )
        snapList = self.listSnapshots( volName )
        if len( snapList ) > 0:
            lastSnap = snapList[ -1 ]
            self._logFacility.debug( "Last Snapshot For Volume %s, %s" % ( volName, lastSnap ) )
            reString = '%s\.snapshot\.(\d*)' % volName
            self._logFacility.debug( "RegEx Pattern Set To %s" % reString )
            reMatch = re.search( ".*\.(\d*)", lastSnap )
            if reMatch:
                oldestSnap = int( reMatch.group( 1 ) )
                self._logFacility.debug( "Setting oldestSnap ( 1 ) To %d" % oldestSnap )
                if oldestSnap >= maxCount:
                    for snapNo in reversed( range( maxCount, oldestSnap + 1 ) ):
                        self._deleteSnapshot( volName, "%s.snapshot.%d" % ( volName, snapNo ) )

                    oldestSnap = maxCount - 1
            else:
                self._logFacility.debug( "Setting oldestSnap ( 2 ) To %d" % maxCount )
                oldestSnap = maxCount

            self._rotateSnaps( volName, oldestSnap )
        else:
            self._logFacility.info( "No Snapshots Found For Volume %s" % volName )

        self._createSnapshot( volName, "%s.snapshot.1" % volName )

    def _rotateSnaps( self, volName, maxCount ):
        if self._filerConn is None:
            return False
            
        for snapNo in reversed( range( 1, maxCount + 1) ):
            self._logFacility.debug( "About To Rename Snapshot %d On %s" % ( snapNo, volName ) )
            self._renameSnapshot( volName, "%s.snapshot.%d" % ( volName, snapNo ), "%s.snapshot.%d" % ( volName, snapNo + 1 ) )


    def _createSnapshot( self, volName, snapName ):
        if self._filerConn is None:
            return False
            
        self._logFacility.debug( "Call _createSnapshot:snapshot-create. Args: %s, %s " % ( volName, snapName ) )
        naReturn = None
        try:
            naReturn = self._filerConn.invoke( 'snapshot-create', 'volume', volName, 'snapshot', snapName )
        except Exception as errMsg:
            self._logFacility.error( "Call To _createSnapshot:snapshot-create Raised Exception.  Reason: %s ( %s )" % ( errMsg, snapName ) )
            return False
            
        if naReturn.results_errno() != 0:
            errMsg = naReturn.results_reason()
            self._logFacility.error( "Call To _createSnapshot:snapshot-create Failed.  Reason: %s ( %s )" % ( errMsg, snapName ) )
            return False

        return True

    def _renameSnapshot( self, volName, origName, newName ):
        if self._filerConn is None:
            return False
            
        self._logFacility.debug( "Call _renameSnapshot:snapshot-rename. Args: %s, %s, %s " % ( volName, origName, newName ) )
        naReturn = None
        try:
            naReturn = self._filerConn.invoke( 'snapshot-rename', 'volume', volName, 'current-name', origName, 'new-name', newName )
        except Exception as errMsg:
            self._logFacility.error( "Call To _renameSnapshot:snapshot-rename Failed.  Reason: %s ( %s / %s )" % ( errMsg, origName, newName ) )
            return False
            
        if naReturn.results_errno() != 0:
            errMsg = naReturn.results_reason()
            self._logFacility.error( "Call To _renameSnapshot:snapshot-rename Failed.  Reason: %s ( %s / %s )" % ( errMsg, origName, newName ) )
            return False

        return True

    def _deleteSnapshot( self, volName, snapName ):
        if self._filerConn is None:
            return False
            
        self._logFacility.debug( "Call _deleteSnapshot:snapshot-delete. Args: %s, %s" % ( volName, snapName ) )
        naReturn = None
        try:
            naReturn = self._filerConn.invoke( 'snapshot-delete', 'volume', volName, 'snapshot', snapName )
        except Exception as errMsg:
            self._logFacility.error( "Call To _deleteSnapshot:snapshot-delete Failed.  Reason: %s ( %s )" % ( errMsg, snapName ) )
            return False
            
        if naReturn.results_errno() != 0:
            errMsg = naReturn.results_reason()
            self._logFacility.error( "Call To _deleteSnapshot:snapshot-delete Failed.  Reason: %s ( %s )" % ( errMsg, snapName ) )
            return False

        return True
        

    def _execAPI( self, apiCall ):
        if self._filerConn is None:
            return False
            
        naReturn = None
        try:
            naReturn = self._filerConn.invoke( apiCall )
        except Exception as errMsg:
            self._logFacility.error( "Call To _execAPI:%s Failed, Exception Was Raised: %s" % ( apiCall, errMsg ) )
            return None
            
        if naReturn.results_errno() != 0:
            print( naReturn.results_reason() )
            return None

        return naReturn
        
    def checkShelf( self ):
        if self._filerConn is None:
            return None

        return self._execAPI( 'storage-shelf-environment-list-info' )
        
    def checkDisk( self ):
        if self._filerConn is None:
            return None
            
        naReturn = self._filerConn.invoke( 'disk-list-info' )
        if naReturn.results_errno() != 0:
            print( naReturn.results_reason() )

        diskList = naReturn.child_get( 'disk-details' )
        print( diskList )
        diskDets = {}
        for indivDisk in diskList.children_get():
            diskInfo = {}
            for keyName in diskLabel:
                diskInfo[ keyName ] = indivDisk.child_get_string( keyName )
            diskDets[ indivDisk.child_get_string( 'name' ) ] = diskInfo

        return diskDets
        
    def checkVolume( self, volName=None ):
        if self._filerConn is None:
            return None
            
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
        
    def checkAggr( self, aggrName=None ):
        if self._filerConn is None:
            return None
            
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

    def checkFiler( self ):
        if self._filerConn is None:
            return None
            
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
        

if __name__ == '__main__':
    naConn = NetApp( 'erpna03' )
    print( naConn.diskDets )
