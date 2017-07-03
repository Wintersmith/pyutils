# pyutils
Dumping ground for various Python utils / libs I've created over the years ( with thanks to various people on the internet for their examples that have pointed me in the right direction ).
With the odd exception ( Filer.py, for example ), Py3 support is non-existent ( the target version was primarily 2.4 on Solaris ), though I'll get round to doing something about that sooner, or later....


 - Platform.py ( and _darwin.py, _linux2.py, _win32.py ) was my attempt at having platform specific imports and functions.  Mostly successful...
 - DBStorage.py - an attempt at creating a DB agnostic interface; supports Gadfly ( no idea if that is still available....  Shows how old this is :( ), SAP DB, MySQL, and SQLite ( before it was included in the standard lib )
 - DNSLib.py - Pretty much what it says ( though DNSLib might be overstating things ).  It allows DNS requests to be fired at specified DNS servers.
 - Filer.py - A more "friendly" interface to NetApp's SDK.  It provides access to LUN info, system status, and will even take snapshots.
 - OVM.py - An interface to the Oracle VM Manager's API, currently shows VM's and their statuses, and jobs running on the Manager.
 - VMware.py -  An interface to ESXi's API, currently lists VM's, datastores, and shows alarms.
 - DistributedCron - A distributed cron, that utilises a DB to provide failover / load cron's.
 - archiveFS.py - Designed to clean up / store Concurrent Request files created on ERP systems.  Creates compressed tar's of log / out files.
 - parseDayOne.py - parses the JSON backup from DayOne, and creates a directory for each entry, and populates it with the text, and optionally, photos, weather, location ( weather / location are raw dicts, for now )

 Disclaimer: I've made these scripts available in case someone may find them useful ( I'd be interested to hear of any improvements ).  I make no guarentees....
