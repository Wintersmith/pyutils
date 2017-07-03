#!/usr/bin/env python

from __future__ import print_function
import os
import sys
import json
from datetime import datetime
from shutil import copy

baseDir = os.getcwd()
journalJSON = os.path.join( baseDir, 'Journal.json' )
photosDir = os.path.join( baseDir, 'photos' )
entryPoints = [ 'weather', 'location', 'text', 'userActivity' ]

def writeEntry( journalEntry ):
    entryDate = datetime.strptime( journalEntry[ 'creationDate' ], '%Y-%m-%dT%H:%M:%SZ' )
    entryDir = os.path.join( baseDir, entryDate.strftime( '%Y/%m/%d/%H-%M' ) )
    try:
        try:
            os.makedirs( entryDir )
        except Exception:
            pass
        for indivSection in entryPoints:
            if indivSection in journalEntry:
                writeFile( os.path.join( entryDir, indivSection ), journalEntry[ indivSection ] )
        try:
            photoList = journalEntry[ 'photos' ]
            for indivPhoto in photoList:
                photoFile = os.path.join( photosDir, '%s.%s' % ( indivPhoto[ 'md5' ].lower(), indivPhoto[ 'type' ]  ) )
                if os.path.exists( photoFile ):
                    try:
                        copy( photoFile, entryDir )
                    except Exception as errMsg:
                        print( 'Unable To Copy %s To %s, %s' % ( photoFile, entryDir, errMsg ) )
        except KeyError:
            pass
    except Exception as errMsg:
        print( 'Encountered An Error With %s, %s' % ( journalEntry, errMsg ) )
    
def writeFile( fileName, fileContents ):
    try:
        with open( fileName, 'w' ) as fileHandle:
            fileHandle.write( str( fileContents ) )
    except Exception as errMsg:
        print( 'Failed To Write To %s, Reason: %s' % ( fileName, errMsg ) )
        
def main( ):
    if os.path.exists( journalJSON ):
        with open( journalJSON ) as jsonFH:
            for indivEntry in json.load( jsonFH )[ 'entries' ]:
                writeEntry( indivEntry )

if __name__ == '__main__':
    sys.exit( main() )