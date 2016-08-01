DROP TABLE IF EXISTS CronEntries;
CREATE TABLE CronEntries (
  cronID int(10) unsigned NOT NULL auto_increment,
  cronHost int(10) unsigned default NULL,
  cronMinute varchar(64) default NULL,
  cronHour varchar(64) default NULL,
  cronDayOfMonth varchar(64) default NULL,
  cronMonth varchar(64) default NULL,
  cronDayOfWeek varchar(64) default NULL,
  cronCommandLine varchar(255) default NULL,
  cronActive tinyint(1) default NULL,
  cronComment varchar(255) default NULL,
  cronUID smallint(6) default NULL,
  cronGID smallint(6) default NULL,
  PRIMARY KEY  (cronID),
  KEY CronByHost (cronHost)
) ENGINE=MyISAM;

DROP TABLE IF EXISTS Hosts;
CREATE TABLE Hosts (
  hostID int(10) unsigned NOT NULL auto_increment,
  hostName varchar(64) default NULL,
  PRIMARY KEY  (hostID),
  KEY HostByName (hostName)
) ENGINE=MyISAM;

DROP TABLE IF EXISTS Users;
CREATE TABLE Users (
  userID smallint unsigned int not null auto_increment,
  userName varchar( 32 ),
  userPassWord varchar( 256 ),
  PRIMARY KEY ( userID ),
  KEY userByName ( userName )
) ENGINE=MyISAM;

DROP TABLE IF EXISTS CronGroup;
CREATE TABLE CronGroup (
  groupID int(10) unsigned NOT NULL auto_increment,
  groupDesc varchar(64) default NULL,
  groupMaster int(10) default NULL,
  PRIMARY KEY  ( groupID )
) ENGINE=MyISAM;
