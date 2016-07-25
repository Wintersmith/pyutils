
import os
import sys
import ssl
import json

from . import requests
from .requests import exceptions

HTTP_BASE = "http://"
HTTPS_BASE = "https://"
OVM_BASE_URI = "/ovm/core/wsapi/rest"

class MyAdapter( requests.adapters.HTTPAdapter ):
    def init_poolmanager(self, connections, maxsize, block=False):
        self.poolmanager = requests.packages.urllib3.poolmanager.PoolManager(num_pools=connections,
                                       maxsize=maxsize,
                                       block=block,
                                       ssl_version=ssl.PROTOCOL_TLSv1)
class OVMManager( object ):

    def __init__( self, hostAddr, portNo, userName, passWord ):
        self._hostAddr = hostAddr
        self._portNo = portNo
        self._userName = userName
        self._passWord = passWord
        self._ovmConn = None
        self._baseURI = "%s%s:%s%s/"% ( HTTPS_BASE, self._hostAddr, self._portNo, OVM_BASE_URI )

    def login( self ):
        self._ovmConn = requests.Session()
        self._ovmConn.mount( 'https://', MyAdapter() )
        self._ovmConn.auth = ( self._userName, self._passWord )
        self._ovmConn.verify = False
        self._ovmConn.headers.update({'Accept': 'application/json', 'Content-Type': 'application/json'})

    def managerState( self ):
        ovmResp = self._ovmConn.get( self._getURL( "Manager" ) )
#        try:
#            ovmResp = self._ovmConn.get( self._getURL( "Manager" ) )
#        except ( OSError, ConnectionError ):
#            print( "Failed To Connect To Host ( %s:%s )" % ( self._hostAddr, self._portNo ) )
#            return "FAILED"
        print( ovmResp.request.headers )
        print( ovmResp.headers, ovmResp.status_code )
        managerState = ovmResp.json()

        return managerState[ 0 ][ 'managerRunState' ].upper()

    def _getURL( self, ovmComponent ):
        return "%s%s" % ( self._baseURI, ovmComponent )
