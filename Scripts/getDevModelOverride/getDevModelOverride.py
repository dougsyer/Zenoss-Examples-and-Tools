#!/usr/bin/env python
import Globals
from sys import exc_info
from Products.ZenUtils.ZenScriptBase import ZenScriptBase
from ZODB.transact import transact
from subprocess import call
from pprint import pprint
from prettytable import PrettyTable
import sys

class script_runner(ZenScriptBase):
    """ prints a list of all devices that have overriden modeler plugins on the device
    """

    def buildOptions(self):
        super(script_runner, self).buildOptions()

        self.parser.add_option(
            '--pretty',
            dest='output_format',
            action='store_true',
            help='print to screen via pretty table')
        self.parser.set_defaults(pretty=True)

    def p_table_izer(self, results):
        ints = PrettyTable(["Device ID", "Device Title","Device Class"], sortby='Device Class')
        ints.align["Device ID", "Device Title", "Device Class"] = "l"  # Left align
        for result in results:
            ints.add_row(result[0], result[1], result[2])
        print ints

        def run(self):
        results = []


        print "searching for devices with overriden modeller plugins"
        devs = self.dmd.Devices
        for d in devs.getSubDevicesGen():
            if d.getProdState() != 'Production':
                continue
            if d.isLocal('zCollectorPlugins'):
               print d.id, d.title, d.getDeviceClassName()
               results.extend((d.id, d.title, d.getDeviceClassName()),)

        print
        print "Formatting Output..."
        if self.options.output_format:
            self.p_table_izer(results)

if __name__ == '__main__':
    print "Connecting to DMD..."
    tool = script_runner(connect=True)
    tool.run()
