
from pyVim import connect
from pyVmomi import vmodl, vim
from tools import pchelper
from tools import alarm


vmProperties = ["name", "config.uuid", "config.hardware.numCPU", "config.hardware.memoryMB", "guest.guestState", 
                  "config.guestFullName", "config.guestId", "config.version"] 

class Tin( object ):

    def __init__( self, hostAddr, userName, passWord, portNo=443 ):
        self._hostAddr = hostAddr
        self._portNo = int( portNo )
        self._uName = userName
        self._pWord = passWord
        self._vmConn = None

    def login( self ):
        self._vmConn = connect.SmartConnect( host = self._hostAddr, user = self._uName, 
                                             pwd = self._pWord, port = self._portNo, sslContext = None  )

    def listVMs( self ):
        vmContent = self._vmConn.content.rootFolder
        vmView = pchelper.get_container_view( self._vmConn, obj_type = [ vim.VirtualMachine ] )
        vmData = pchelper.collect_properties( self._vmConn, view_ref = vmView, obj_type = vim.VirtualMachine,
                                              path_set = vmProperties, include_mors = True )
        for indivVM in vmData:
            yield indivVM
            

    def listHostAlarms( self ):
        sIndex = self._vmConn.content.searchIndex
        if sIndex:
            vmHost = sIndex.FindByIp( datacenter=None, ip=self._hostAddr, vmSearch=False )
            alarm.print_triggered_alarms( entity=vmHost )

    def getDataStoreDets( self ):
        hostContent = self._vmConn.RetrieveContent()
        objView = hostContent.viewManager.CreateContainerView( hostContent.rootFolder, [ vim.HostSystem ], True )
        esxHosts = objView.view
        dataStores = {}
        for indivHost in esxHosts:
            print( "Host: %s" % indivHost.name )
            storageConn = indivHost.configManager.storageSystem
            hostMountInfo = storageConn.fileSystemVolumeInfo.mountInfo
            dsDict = {}
            for hostFileSysInfo in hostMountInfo:
                print( hostFileSysInfo )

if __name__ == '__main__':
    esxConn = Tin( '10.99.37.22', 'root', 'Br1ckTop' )
    esxConn.login()
    for vm in esxConn.listVMs():
        print( vm )
