#!/usr/bin/env python
"""
Version 1.3

"""
import Globals
from sys import exc_info
from Products.ZenUtils.ZenScriptBase import ZenScriptBase
from ZODB.transact import transact
from subprocess import call
from pprint import pprint
import sys
from Products.Zuul import getFacade, listFacades
from zenoss.protocols.jsonformat import from_dict
from zenoss.protocols.protobufs.zep_pb2 import EventSummary
from Products.ZenEvents.events2.proxy import EventSummaryProxy
import csv
import datetime
import time
from itertools import chain
from collections import OrderedDict
import re


class simple_script_runner(ZenScriptBase):
    """ get a list of all devices with no interfaces monitored

        for reference, raw events look like this:

        {'count': 1,
         'first_seen_time': 1385328320000L,
         'last_seen_time': 1385328320000L,
         'notes': [{'created_time': 1393341664597L,
            'message': u'NWN00000',
            'user_name': u'admindsyer2@inframax.local',
            'user_uuid': u'610ededd-280c-4f21-83f9-4cf411fe6a8f',
            'uuid': u'005056b6-81c3-b577-11e3-9e3071320898'}],
         'occurrence': [{'actor': {'element_identifier': u'nwn-dc',
                           'element_sub_identifier': u'VirtualMachine_vm-100',
                           'element_sub_title': u'WMAFILE01.nwnit.corp',
                           'element_sub_type_id': 2,
                           'element_sub_uuid': u'2c5f4063-e7f9-4757-a8f8-8aab07f147a3',
                           'element_title': u'nwn-dc',
                           'element_type_id': 1,
                           'element_uuid': u'2f1b5748-bbd7-48bf-8b17-2e5751810612'},
                 'agent': u'zenvsphere',
                 'created_time': 1385328320000L,
                 'details': [{'name': u'description', 'value': [u'']},
                             {'name': u'manager',
                              'value': [u'imax-zns-dougdev2.inframax.local']},
                             {'name': u'iprealm', 'value': [u'default']},
                             {'name': u'zenoss.device.production_state',
                              'value': [u'1000']},
                             {'name': u'zenoss.device.priority',
                              'value': [u'3']},
                             {'name': u'zenoss.device.device_class',
                              'value': [u'/vSphere']},
                             {'name': u'eventClassMapping',
                              'value': [u'/vSphere/vSphere Default Mapping']}],
                 'event_class': u'/vSphere',
                 'event_class_key': u'com.vmware.vcIntegrity.ScanStart',
                 'event_class_mapping_uuid': u'a03b5abd-90c3-48db-87a4-5a36391c2f79',
                 'event_key': u'',
                 'fingerprint': u'nwn-dc|VirtualMachine_vm-100|/vSphere|2|Scanning object WMAFILE01.nwnit.corp.',
                 'message': u'Scanning object WMAFILE01.nwnit.corp.',
                 'monitor': u'localhost',
                 'severity': 2,
                 'summary': u'Scanning object WMAFILE01.nwnit.corp.',
                 'tags': [{'type': u'zenoss.device.device_class'Traceback (most recent call last):
                 'status': 0,
                 'status_change_time': 1385300319047L,
                 'update_time': 1385522990997L,
                 'uuid': u'00505696-07c8-8c34-11e3-45cd458a4b34'} 

       createEventFilter(self, 
           severity=(), 
           status=(), 
           event_class=(),
           first_seen=None,
           last_seen=None,
           status_change=None,
           update_time=None,
           count_range=None,
           element_identifier=(),
           element_title=(),
           element_sub_identifier=(),
           element_sub_title=(),
           uuid=(),
           event_summary=None,
           tags=(),
           fingerprint=(),
           agent=(),
           monitor=(),
           event_key=(),
           current_user_name=(),
           subfilter=(),
           operator=None,
           details=None,
           event_class_key=(),
           event_group=(),
           message=())

           note - des = time fields are entered as a tuple and unix time stamps
                  for example (1386276287000,) or (1386276287000, 1386276287000)

           Creates a filter based on passed arguments.
           Caller is responsible for handling the include-zero-items case.
           For example, passing an empty uuid tuple will not filter by uuid so includes everything.
    """

    # compiled regexes
    remove_whitespacer = re.compile('\s+')
    comma_remover = re.compile(',')
    group_client_getter = re.compile(r"^/Clients/(.*?)$")

    def buildOptions(self):
        super(simple_script_runner, self).buildOptions()

        self.parser.add_option(
            '--screen',
            dest='screen_output_format',
            action='store_true',
            help='print to screen')

        self.parser.add_option(
            '--archive',
            dest='get_archived_events',
            action='store_true',
            help='extract events from archive - default is False=extract from active events')

        self.parser.add_option(
            '--incl_create_time',
            dest='include_created_time',
            action='store_true',
            help='include created time in export, default is false')

        self.parser.add_option(
            '--csv',
            dest='csv_output_format',
            action='store_true',
            help='output to csv events-export.csv, optionally add in -f to add a file name')
        self.parser.set_defaults(csv_output_format=False)

        self.parser.add_option(
            '--device',
            dest='device_filter',
            action='store',
            help='extract events for device only')
        self.parser.set_defaults(device_filter='')
             
        self.parser.add_option(
            '--unixtimestamps',
            dest='unix_time_stamp',
            action='store_true',
            help='add additional fields populated with more precise unix timestamp fields to export can get to microseconds')

        self.parser.add_option(
            '--severity',
            dest='severity_filter',
            action='store',
            help='severities you want to export, in list format ie 5,4 is all critical errors, default is all severities')
        self.parser.set_defaults(severity_filter='0,1,2,3,4,5')

        self.parser.add_option(
            '--first_time',
            dest='first_time_filter',
            action='store',
            help='export events first seen as of this time to the current time,\
                 format is YYYY-MM-DD=HH:MM:SS,YYYY-MM-DD=HH:MM:SS for start,end time\
                 if only one value is passed it takes the time enterted to the current time')
        self.parser.set_defaults(first_time_filter='1980-01-01=00:00:00')

        self.parser.add_option(
            '--customer_name',
            dest='customer_filter',
            action='store',
            help='regex used to exclude any customers that do not match the filter')
        self.parser.set_defaults(customer_filter='')

    def event_keys(self, ekeys, *args):
        """ adds a list of keys to a set or returns existing set if
            new keys are not passed """
        for i in args:
            if len(args) > 0:
                ekeys.update([a for a in args[1:]])
        return ekeys
 
    def get_me_filter_maytee(self, zep, dev, sev, ft):
        print self.get_unix_time(tuple(ft.split(',')))
        return zep.createEventFilter(
            element_identifier=dev, 
            severity = sev,
            first_seen = self.get_unix_time(tuple(ft.split(','))),
            details = {'zenoss.device.production_state':1000})

    def convert_severity_codes(self, code):
        return {0: 'clear',
                1: 'debug',
                2: 'informational',
                3: 'warning',
                4: 'error',
                5: 'critical'}.get(code)

    def convert_device_priority(self, code):
        return unicode({'5': 'Highest',
                        '4': 'High',
                        '3': 'Normal',
                        '2': 'Low',
                        '1': 'Lowest',
                        '0': 'Trivial'}.get(code))

    def convert_event_status(self, status_code):
        return {-1: 'NA',  # used just in case
                0: 'New',
                1: 'Acknowledged',
                2: 'Suppressed',
                3: 'Closed',
                4: 'Cleared',
                5: 'Dropped',
                6: 'Aged'}.get(status_code)

    def convert_production_states(self, state):
        """ given a production code return textual
            representation of production state
            to do:  look this up in zenoss instead because
                    the prod states can change
        """
        return {'1000': u'Production',
                '500': u'Pre-Production',
                '400': u'Test',
                '300': u'Maintenance',
                '-1': u'Decomissioned',
                '-10': u'TempShutoff'}.get(state, 'Unknown')

    def return_formatted_field(self, field):
        """ returns a new event field name if its in the list here, otherwise returns 
            orig name 
        """
        return {'element_identifier': 'device_id',
                'element_title':  'device_title',
                'element_sub_identifier': 'component_id',
                'element_sub_title': 'component_title',
                'first_time_seen': 'first_time',
                'last_time_seen': 'last_time',
                'zenoss.device.production_state': 'production_state',
                'zenoss.device.priority': 'device_priority',
                'zenoss.device.device_class': 'device_class',
                'zenoss.device.ip_address': 'device_ip_address',
                'zenoss.device.systems': 'device_systems',
                'zenoss.device.groups': 'device_groups',
                'zenoss.device.location': 'device_location',
                'fingerprint': 'dedupid',
                }.get(field, field)

    def cleanup_textfield(self, field):
        if isinstance(field, (int, long, float)):
            return field
        elif field is None:
            return 'none'
        """ remove commas. LF, CR from fields"""
        field = self.remove_whitespacer.sub(' ', field)
        field = self.comma_remover.sub('', field)
        return field

    # given a filename return the filename with a current date time stamp
    def simple_timeStamped(self, fname):
        return "%s_%s" % (datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S'), fname)

    def format_time(self, timestamp):
       return time.strftime("%m/%d/%Y %H:%M:%S", time.localtime(int(timestamp/1e3)))  

    def get_unix_time(self, timestamp):
        """ given a time entry in the form of tuple(start, end)
            with date and time format of YYYY-MM-DD=HH:MM:SS
            return full unix time stamp in a tuple"""
        if len(timestamp) == 1:
            return (int(time.mktime(time.strptime(timestamp[0], '%Y-%m-%d=%H:%M:%S'))*1000), 
                    int(time.mktime(time.localtime()))*1000, )
        if len(timestamp) == 2:
            return (int(time.mktime(time.strptime(timestamp[0], '%Y-%m-%d=%H:%M:%S'))*1000), 
                    int(time.mktime(time.strptime(timestamp[1], '%Y-%m-%d=%H:%M:%S'))*1000), )

    def get_std_export_fields(self):
        """ return an ordered dict of the fields as you
            want the columns sorted
            note:  you cant create a sorted dict by passing
                   a dict because it doesnt get sorted so we 
                   pass it the way you see here
	"""
        return OrderedDict([
            ('customer_name', 'none'),
            ('monitor', 'none'),
            ('device_id', 'none'),
            ('device_title', 'none'),
            ('device_class', 'none'),
            ('component_id', 'none'),
            ('component_title', 'none'),
            ('severity', 'none'),
            ('status', 'none'),
            ('summary', 'none'),
            ('message', 'none'),
            ('first_time', 'none'),
            ('last_time', 'none'),
            ('created_time', 'none'),
	    ('agent', 'none'),
	    ('count', '0'),
            ('event_class', 'none'),
            ('event_class_key', 'none'),
	    ('eventClassMapping', 'none'),
	    ('event_key', 'none'),
	    ('dedupid', 'none'),
	    ('iprealm', 'none'),
	    ('production_state', 'none'),
	    ('status_change_time', 'none'),
            ('device_groups', 'none'),
            ('device_location', 'none'),
            ('device_systems', 'none'),
            ('device_priority', 'none'),
            ('manager', 'none'),
            ('event_id', 'none'),
            ('ticket', 'none'),
            ('last_action', 'none'),
            ('current_user_name', 'none'),
	])

    def format_event(self, r_event, dont_export_fields):

        event = {}

        # just for convenience
        occurrence = r_event['occurrence'][0]
        notes_list = r_event['notes'] if r_event.get('notes', None) else None
        
        audit_log = r_event.get('audit_log', None)
        dev_stuff = occurrence.get('actor')
        details_list = occurrence.get('details')

        # get device and component data
        event = {unicode(self.return_formatted_field(name)): value for name, value in dev_stuff.iteritems()
            if name not in dont_export_fields}

        # add event context stuff except details
        for ev_field, value in occurrence.iteritems():
            if ev_field not in ('actor', 'details', 'tags') and ev_field not in dont_export_fields:
                event[unicode(self.return_formatted_field(ev_field))] = value

            if ev_field == 'severity':
                event[ev_field] = unicode(self.convert_severity_codes(value))

            # not sure what created time is yet, but if we enable it in options
            # format it correactly and in option for timestamps
            if ev_field == 'created_time':
                if self.options.include_created_time:
                    if self.options.unix_time_stamp:
                        event['created_time_stamp'] = event[ev_field]
                    else:
                        event[ev_field] = self.format_time(value) if event[ev_field] else 'Not Stored'
                else:
                    del event[ev_field]

        # handle top level fields
        event[u'count'] = str(r_event.get('count'))
        event[u'first_time'] = self.format_time(r_event.get('first_seen_time'))
        event[u'last_time'] = self.format_time(r_event.get('last_seen_time'))
        event[u'current_user_name'] = r_event.get('current_user_name')

        if self.options.unix_time_stamp:
            event[u'first_time_timestamp'] = r_event.get('first_seen_time')
            event[u'last_time_timestamp'] = r_event.get('last_seen_time')


        event[u'status_change_time'] = self.format_time(r_event.get('status_change_time'))
        event[u'event_id'] = r_event.get('uuid')
        event[u'count'] = r_event.get('count')
        event[u'status'] = self.convert_event_status(r_event.get('status'))

        # get event details
        for detail in chain(details_list):
            detail_key = unicode(self.return_formatted_field(detail.get('name')))

            # there is an event detail called status
            # ignore this
            if detail_key == u'status':
                continue

            detail_value = detail.get('value')
            # some detail value fields are represented as lists but i dont think at least now they
            # ever have more than one value
            if detail_value == None:
                detail_value = 'none'
            elif isinstance(detail_value, (int, long, basestring)):
                detail_value = str(detail_value)
            else:
                detail_value = "|".join(detail_value)

            event[detail_key] = detail_value

            if detail_key == 'production_state':
                event[detail_key] = self.convert_production_states(detail_value)

            if detail_key == 'device_priority':
                event[detail_key] = self.convert_device_priority(detail_value)

            # attempt to determine customer name by parsing groups
            if detail_key == 'device_groups':
                groups = event[detail_key].split('|')
                for g in groups:
                    grp = self.group_client_getter.search(g)
                    if grp:
                        event[u'customer_name'] = grp.groups()[0]
                        break

            # fird a ticket number in the notes, if found
            # return it otherwise return 'NA'
            event[u'ticket'] = u'NA'
            if notes_list:
                for note in notes_list:
                    note_message = note.get('message')
                    if note_message.startswith('<p>INC') or  note_message.startswith('NWN'):
                        event['ticket'] = note.get('message').lstrip('<p>').rstrip('</p>')
                        break
            
            if audit_log: 
                event[u'last_action'] = self.convert_event_status(audit_log[0].get('new_status', -1))
                # when you close an event apparently it doesnt set the owner field so extract it here
                if event['last_action'] == 'Closed':
                    event[u'current_user_name'] = audit_log[0].get('user_name')


        return event

    def run(self):
        #evt_keys = set()
        dmd = self.dmd
        zep = getFacade('zep')
        export_counter = 0
        formatted_event = None
 
        # calls method to clean up some command line options to turn into parameters
        zep_archive_gen = zep.getEventSummariesGenerator(self.get_me_filter_maytee(
            zep, 
            self.options.device_filter,
            map(int, self.options.severity_filter.split(',')),
            self.options.first_time_filter,),
            archive = self.options.get_archived_events)

       zep_status_gen = zep.getEventSummariesGenerator(self.get_me_filter_maytee(
            zep,
            self.options.device_filter,
            map(int, self.options.severity_filter.split(',')),
            self.options.first_time_filter,))

       zep_gen = chain(zep_archive_gen, zep_status_gen)

        no_export_fields = ('element_type_id',
                            'element_sub_type_id',
                            'element_sub_uuid',
                            'element_uuid',
                            'event_class_mapping_uuid')


        print "Starting Event Export"

        if self.options.device_filter:
            print "For Device %s" % self.options.device_filter
        else:
            print "For all Events in Zenoss"

        # set up headers for the csv file
        if self.options.csv_output_format:
            outf = open(self.simple_timeStamped('event_export.csv'), 'wb')
            header = self.get_std_export_fields().keys()
            csvwriter = csv.DictWriter(outf, delimiter=",", fieldnames=header) 
            csvwriter.writeheader()
            print "Exporting Events to CSV File %s" %outf

        # start iterating though events
        for raw_event in zep_gen:

            formatted_event = self.format_event(raw_event, no_export_fields)

            if formatted_event:
                export_counter += 1

            # this isnt used right now, was using it to get a list of keys for events
            # but since we are defining the fields for csv dont need it now
            # but would need it if we were exporting event details because there
            # are duplicate keys when they are exported
            #evt_keys.update(formatted_event.keys())

            # to do add this as an exclusion to the query
            if self.options.customer_filter:
                customer_filter=re.compile(r'%s' % self.options.customer_filter, flags=re.IGNORECASE)
                customer = formatted_event.get('customer_name', False)
                if not customer or not customer_filter.search(customer):
                    export_counter -= 1
                    continue

            if self.options.screen_output_format:
                pprint(formatted_event)
            
            if self.options.csv_output_format:
                # merge the default fields defined in get_std_export_fields method
                # with the values returned by the event search 
                export_events = self.get_std_export_fields()
                for k in export_events.keys():
                    if formatted_event.get(k, None) is not None:
                        export_events[k] = self.cleanup_textfield(formatted_event.get(k))
                    else:
                        export_events[k] = 'none'
                csvwriter.writerow(export_events)

        if not formatted_event:
            print "No Events found for filter criteria"

        if self.options.csv_output_format:
            outf.close()
            print "Exported %s Events" % export_counter

if __name__ == '__main__':
    print "Connecting to DMD..."
    tool = simple_script_runner(connect=True)
    tool.run()
