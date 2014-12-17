Zenoss-Examples-and-Tools
=========================

Public repo to share zenoss tools and examples

ZenPack Examples
----------------

dsplugions.py Example ZenPython Device Level Daemon Plugin using snmp


Scripts
-------

evexporter.py -> export events cleanly into csv format:
    
    exports events into csv format cleanly...with some options
    
    WARNING:  careful, you can fill up your drives, CSVs can be huge
    
    example usage:
    1.  evexporter --csv
        exports all events in event status table to datetime stamped csv file
    2.  evexporter --csv --device MYDEVICE
        exports all events in event status table for device id MYDEVICE
    3.  evexporter --screen --severity 4,5 --archive
        export all error and critical messages from the event archive
    4.  evexporter --csv -f myfile --first_time 2014-05-15=12:00:35,2014-05-17=13:00:50
        export all events from status where first time is between 12:00 on 5/15 and 13:00 on 5/17
    5.  evexporter --screen --unixtimestamps
        exports to screen but uses unix time stamps instead of iso time format(more precision)
    6.  evexporter --archive --csv --first_time 2014-04-15:12:00:00
        export events from archive where first seen is from date/time specified to now
        
checkEventMisconfig.py

    Checks some things that **could indicate issues with your transforms/mappings.  For sure not everyting
    printed is an issue but when you have alot of transforms mappings I find it useful to periodically check this.
    
    just run the tool as the zenoss user
    
MaintWindowCleaner.py

    removes maintenance windows from dmd that where scheduled but will never run again.  
    just run the tool as the zenoss user..
