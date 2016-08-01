# DNSLib.py
#
# Description: This module will contain functions to perform DNS requests.  Intially, these will only be client requests.  The Query call
#                will always return a list.  In the case of an MX record, it returns a list, containing a tuple pair in the format
#                ( preference, host ).
#
# TODO:
#
# Reverse queries
#
# History:
#
# Initial Version: 20 January, 2003 - Ability to query multiple DNS servers.  Supports the following record types:
#                                    CNAME
#                                    MX
#                                    A
# 

import socket, string, re, os, struct, select

class DNSServerError(Exception): pass
class DNSQueryError(Exception): pass

MAXLABEL = 63
MAXNAME = 255

VERSION = '0.3'

lookupTypes = {"A": 1, "CNAME": 5, "MX": 15, "NS": 2}
reverseType = {1 : "A", 5 : "CNAME", 15 : "MX", 2 : "NS" }

class  DNSClient( object ):
    
    
    def __init__( self, dnsServer, dnsPort=53, timeOut=30, reverseQuery=0, cacheQueries=False ):
        self.dnsServer = dnsServer
        self.dnsPort = dnsPort
        self.timeOut = timeOut
        self.reverseQuery = reverseQuery
        self.cacheQueries = cacheQueries
        if self.cacheQueries:
            self.queryCache = {}
        
    def Query( self, dnsQuery, recordType="A" ):
        if not lookupTypes.has_key( recordType ):
            raise DNSQueryError, "Record Type Not Valid"
        
#        if self.cacheQueries:
#            try:
#                DNSResult = self.queryCache[ dnsQuery ]
#             except:
                 
                 
        headerMessage = self._CreateHeader( self.reverseQuery )
        questionMessage = self._CreateQuestion( dnsQuery, recordType )
        
        DNSResult = self._SendRequest( headerMessage + questionMessage )
        
        return DNSResult
        
    def _SendRequest( self, dnsRequest ):
        DNSConn = self._UDPRequest()
        for serverIP in self.dnsServer:
            try:
                DNSConn.connect( ( serverIP, self.dnsPort ) )
            except socket.error, ErrorMsg:
                raise DNSServerError, ( "Unable To Connect To Server %s.  Reason: %s" % ( serverIP, ErrorMsg ) )
                break
            else:
                DNSConn.send( dnsRequest )
                if self.timeOut:
                    retOne, retTwo, retThree = select.select( [DNSConn], [], [], self.timeOut )
                    if not len(retOne):
                        raise DNSQueryError, ("The Server %s Timed Out" % serverIP )
                    else:
#                        break
                        try:
                            serverReply = DNSConn.recv(512)
                        except socket.error:
                            continue
                        else:
                            readReply = ByteToASCII( serverReply )
        
        return readReply.ProcessReturnPacket()
    
    def _ProcessReply( self, dnsReply ):
        readReply = ByteToASCII( dnsReply )
        
        return readReply.ProcessReturnPacket()
        
    def _UDPRequest( self ):
        connectHandle = socket.socket( socket.AF_INET, socket.SOCK_DGRAM )
        
        return connectHandle
    
    def _CreateHeader( self, opCode ):
        headerFields = [ 1, 0, 0, 0]
        crHeader = Conversions()
        crHeader.Build16Bit( 0 )
        crHeader.Build16Bit( ( 0 & 1 ) << 15 |
                             ( opCode & 0xF ) << 11 |
                             ( 0 & 1 ) << 10 | 
                             ( 0 & 1 ) << 9 | 
                             ( 0 & 1 ) << 8 | 
                             ( 0 & 1 ) << 7 | 
                             ( 0 & 7 ) << 4 | 
                             ( 0 & 0xF ) 
                             )
        for headerOption in headerFields:
            crHeader.Build16Bit( headerOption )
        
        return crHeader.ReturnContents()
    
    def _CreateQuestion( self, dnsQuery, recordType, classType=1 ):
        crQuestion = Conversions()
        crQuestion.BuildName( dnsQuery )
        crQuestion.Build16Bit( lookupTypes[ recordType ])
        crQuestion.Build16Bit( classType )
        
        return crQuestion.ReturnContents()
    
class Conversions( object ):
    
    def __init__( self ):
        self.message = ""
        
    def Build16Bit( self, concatValue ):
        self.message += self.ConvertTo16Bit( concatValue )
    
    def Build32Bit( self, concatValue ):
        self.message += self.ConvertTo32Bit( concatValue )
    
    def BuildName( self, domainName ):
        splitName = []
        for sectionSplit in string.split(domainName,"."):
            if len(sectionSplit) > MAXLABEL:
                raise DNSQueryError, "The Domain Section, Exceeds The Allowed Length"
            splitName.append( string.upper( sectionSplit ) )
        for sections in splitName:
            self.message += chr( len(sections) )
            self.message += sections
            
        self.message += chr( 0 )
            
    def ConvertTo16Bit( self, baseValue ):
        return struct.pack("!H", baseValue)
    
    def ConvertTo32Bit( self, baseValue ):
        return struct.pack("!L", baseValue)
    
    def ConvertFrom16Bit( self, baseValue ):
        return struct.unpack("!H", baseValue)[0]
    
    def ConvertFrom32Bit( self, baseValue ):
        return struct.unpack("!L", baseValue)[0]
    
    def ReturnContents( self ):
        return self.message

class ByteToASCII( object ):
    
    def __init__( self, byteString ):
        self.Conv = Conversions()
        self.byteString = byteString
        self.offSet = 0
        self.initialSize = len( byteString )
        self.pointerLoc = 0
        
    def ReturnSingle( self ):
        bytes = self.byteString [ self.offSet:self.offSet + 1 ]
        self.offSet += 1
        return bytes

    def IncrementOffset( self, incNo ):
        self.offSet += incNo

    def ReturnBytes( self, noOfBytes ):
        bytes = self.byteString [ self.offSet:self.offSet + noOfBytes ]
        self.offSet += noOfBytes
        return bytes
    
    def returnLeftAmt( self ):
        return self.initialSize - self.offSet
    
    def ProcessReturnPacket( self ):
        
        returnData = []
        
        self._ProcessHeader()
        if self.anCount > 0:
            domainName = self._ProcessName()
            retQType = self.Conv.ConvertFrom16Bit( self.ReturnBytes( 2 ) )
            retQClass = self.Conv.ConvertFrom16Bit( self.ReturnBytes( 2 ) )
            returnDataProc = getattr ( self, "_Process%sRecord" % reverseType [ retQType ], None )
            for answerRec in range( self.anCount ):
                dataLength = self._ProcessResource()
                if dataLength > 0:
                    returnData.append( returnDataProc() )
        else:
            returnData = "No Answer Was Returned"
        
        return returnData
        
    def _ProcessHeader( self ):

        self.indivFlags = []
        self.messageID = self.Conv.ConvertFrom16Bit( self.ReturnBytes( 2 ) )
        dnsFlags = self.Conv.ConvertFrom16Bit( self.ReturnBytes( 2 ) )
        
        self.indivFlags = ( ( dnsFlags >> 15 ) & 1,
                             ( dnsFlags >> 11 ) & 0xF,
                             ( dnsFlags >> 10 ) & 1,
                             ( dnsFlags >> 9 ) & 1, 
                             ( dnsFlags >> 8 ) & 1, 
                             ( dnsFlags >> 7 ) & 1, 
                             ( dnsFlags >> 4 ) & 7, 
                             ( dnsFlags ) & 0xF
                             )
        self.qdCount = self.Conv.ConvertFrom16Bit( self.ReturnBytes( 2 ) )
        self.anCount = self.Conv.ConvertFrom16Bit( self.ReturnBytes( 2 ) )
        self.nsCount = self.Conv.ConvertFrom16Bit( self.ReturnBytes( 2 ) )
        self.arCount = self.Conv.ConvertFrom16Bit( self.ReturnBytes( 2 ) )
        
        
    def _ProcessName( self ):

        domainName = []
        
        labelLen = ord( self.ReturnSingle() )
        while not labelLen == 0 :
            if labelLen == 192:
                pointerLoc = self.offSet
                self.offSet = ord( self.ReturnSingle() )
                domainName.append( self._ProcessName() )
                self.offSet = pointerLoc
                return string.join( domainName, "." )
            else:
                domainName.append( self.ReturnBytes( labelLen ) )
            
            labelLen = ord( self.ReturnSingle() )
        
        return string.join( domainName, "." )
        
    def _ProcessResource( self ):
        
        recDomainName = self._ProcessName()
        rrType = self.Conv.ConvertFrom16Bit( self.ReturnBytes( 2 ) )
        rrClass = self.Conv.ConvertFrom16Bit( self.ReturnBytes( 2 ) )
        rrTTL = self.Conv.ConvertFrom32Bit( self.ReturnBytes( 4 ) )
        rdLength = ord( self.ReturnSingle() )
                    
        return rdLength
    
    def _ProcessARecord( self ):
        self.IncrementOffset( 2 )
        
        return  self.NumToIP( self.Conv.ConvertFrom32Bit( self.ReturnBytes( 4 ) ) )
        
    def _ProcessCNAMERecord( self ):
        self.IncrementOffset( 2 )
        
        return self._ProcessName().lower()
        
    def _ProcessMXRecord( self ):
        self.IncrementOffset( 2 )
        prefLevel = self.Conv.ConvertFrom16Bit( self.ReturnBytes( 2 ) )
        hostName = self._ProcessName().lower()
        self.IncrementOffset( 1 )
        
        return prefLevel, hostName
        
    def NumToIP( self, largeNum ):
        return socket.inet_ntoa( struct.pack(">L", largeNum) )
        
if __name__ == "__main__":
    print "Starting DNS Test"
    Lookup = DNSClient( ("10.253.65.10","10.253.65.14") )
    print Lookup.Query("pa.press.net", recordType = "MX")
    print Lookup.Query("mailhost.howden.press.net")
    print Lookup.Query("pasportfeatures.howden.press.net", recordType = "CNAME")
    print Lookup.Query("lestat.howden.press.net")