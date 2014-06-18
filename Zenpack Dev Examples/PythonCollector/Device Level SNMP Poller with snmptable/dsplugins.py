import time

from Products.ZenEvents import ZenEventClasses
from pynetsnmp.twistedsnmp import AgentProxy
from Products.ZenEvents import ZenEventClasses

from ZenPacks.zenoss.PythonCollector.datasources.PythonDataSource \
    import PythonDataSourcePlugin

from collections import Counter, defaultdict

import logging
log = logging.getLogger('zen.mymessyzenpack')


def init_default_dict(type_, *args, **kwargs):
    """ used to create a default dict from a comprehension """
    d = defaultdict(type_)
    d.update(*args, **kwargs)
    return d


def get_index(idx, position):
    """ just return unique ipsec snmpindex from raw index given
        the position you care about, only accepts a single position,
        ie -1, not a list
    """
    return idx.split('.')[position]


def getSnmpV3Args(ds0):
    snmpV3Args = []
    if '3' in ds0.zSnmpVer:
        if ds0.zSnmpPrivType:
            snmpv3Args += ['-l', 'authPriv']
            snmpv3Args += ['-x', ds0.privType]
            snmpv3Args += ['-X', ds0.privPassword]
        elif ds0.authType:
            snmpv3Args += ['-l', 'authNoPriv']
        else:
            snmpv3Args += ['-l', 'noAuthNoPriv']
        if ds0.authType:
            snmpv3Args += ['-a', ds0.authType]
            snmpv3Args += ['-A', ds0.authPassword]
            snmpv3Args += ['-u', ds0.securityName]

    return snmpV3Args


class SampleSnmpDevicePlugin(PythonDataSourcePlugin):
    """This plugin polls stuff from snmp at a device level"""

    # as of python collector 1.3 the config is passed to init, hurray
    def __init__(self, config):
        self.ROWS = ['1.3.6.1.4.1.9.9.171.1.2.3.1.8']
        self.ds0 = config.datasources[0]
        self.p = self._getProxy(self.ds0, config)
        self.p.open()

    proxy_attributes = ('zMaxOIDPerRequest',
                        'zSnmpMonitorIgnore',
                        'zSnmpAuthPassword',
                        'zSnmpAuthType',
                        'zSnmpCommunity',
                        'zSnmpPort',
                        'zSnmpPrivPassword',
                        'zSnmpPrivType',
                        'zSnmpSecurityName',
                        'zSnmpTimeout',
                        'zSnmpTries',
                        'zSnmpVer',
                        'zMaxOIDPerRequest',
                        'getSnmpStatus',
                        'getCustomPropertyMethod',  # you can get a callable now, so you can add/monkey patch methods to get data
                        )

    def _getProxy(self, ds0, config):
        """ return a twisted AgentProxy deferred """

        snmpv3Args = getSnmpV3Args(ds0)

        return AgentProxy(config.manageIp,
                          port=int(ds0.zSnmpPort),
                          timeout=ds0.zSnmpTimeout,
                          snmpVersion=ds0.zSnmpVer,
                          community=ds0.zSnmpCommunity,
                          cmdLineArgs=snmpv3Args,
                          protocol=None,
                          allowCache=False
                          )

    def collect(self, config):
        """
        return deferred for table collection
        NOTE:  snmp table has a limitation of returning 1k "things"...
            to kind of get around it you can add in a list of rows
            and smoosh them all together...otherwise
        """
        return self.p.getTable(self.ROWS)

    def onSuccess(self, result, config):
        """
        Called only on success. After onResult, before onComplete.
        """

        collectionTime = time.time()

        # empty data structure for results, see zenpython collector docs
        data = self.new_data()


        # how to get data from the proxy
        existingStuffs = self.ds0.getCustomPropertyMethod
        polledResults1 = result.get(self.ROWS[0])

        # you can return nothing with the new python collectory...chet for president!
        if not polled_results1:
            log.debug('no stuffs!! found on %s' % config.id)
            return data

        # format returns looks like: {oid for each row:
        #                            {'snmpoid.snmpindex': 'value1', ..}}
        # assign a variable to a snmp row
        # ie it will be something like {'snmpoid.snmpindex': 'value', ..}

        # iterate through rows in a table and maybe do an event based on stuff you care about
        for index, row in polledResults1.items():

            # check stuff...
            # if you are sending an alert its something like:
            if somethingIsBroken:
                msg = "its getting kinda hecktic"
                data['events'].append({
                    'eventClassKey': 'hey_i_used_a_key',
                    'severity': ZenEventClasses.Critical,
                    'summary': msg,
                    'message': msg,
                    'component': aComponentVariable,
                    'mydetail': 'Down'           # can add custom details
                    })
                log.debug('something is broken on  device %s, %s is down' % (config.id, ike_id))
                continue

        # one way to send an event if there is no problem with your code
        good_poll_msg = 'Successful Poll for stuff...im so very smahhhht'
        data['events'].append({
            'summary': good_poll_msg,
            'message': good_poll_msg,
            'eventClassKey': 'my_poller_worked_its_a_miracle',
            'severity': ZenEventClasses.Clear,
            'component': 'THIS ISNT A REAL COMPONENT but i hate whitespace',
            })

        # if im doing something like checking alot of components, its kinda nice to log results to info something like this
        log.info('Checked %s things on %s against a current poll' % (len(existing_stuffs), config.id))
        log.info('Poll returned %s stuffs that we had to check on %s' % (len(polledResults1), % config.id))

        ev = Counter([ev['eventClassKey'] for ev in data.get('events')])
        log.info('Stuffs Poll completed on %s, status details:  %s' % (ev, config.id))

        return data

    def onError(self, result, config):
        """
        Called only on error. After onResult, before onComplete.
        """
        # empty data structure for results, see zenpython collector docs
        data = self.new_data()
        
        err_msg = result.getErrorMessage()
        
        log.error('time for debuggging, this poller failed on %s:  %s' % (err_msg, config.id))
        
        data['events'].append({
             'summary': 'Polling failed for my junk',
             'message': 'Error polling IKE VPN, debug info is : %s' % err_msg,
             'eventClassKey': 'the_key_of_fail',
             'severity': ZenEventClasses.Error,
             'component': 'argggg',
             })
        
        return data
        
            
    def _close(self):
        """
        Close down the connection to the remote device
        """
        if self.p:
            self.p.close()
        self.p = None

    def cleanup(self, config):
        return self._close()
        
