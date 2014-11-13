#!/usr/bin/env python
import Globals
from Products.ZenUtils.ZenScriptBase import ZenScriptBase
from itertools import chain
from collections import Counter
from collections import defaultdict
from pprint import pprint



class SimpleScriptRunner(ZenScriptBase):
    """ quick script to output zenoss licensing info
        version 1.1
    """

    def buildOptions(self):
        super(SimpleScriptRunner, self).buildOptions()

    def printEventDetail(self, pup, reg, rule):
        print "%s ---- Regex: %s, Rule: %s" % (pup, reg, rule)

    def eventClassGen(self):
        for ec in self.dmd.Events.getSubOrganizers():
            yield ec

    def eventClassKeyGen(self):
        for ecK in self.dmd.Events.getInstances():
            yield ecK

    def eventOrganizersGen(self):
        for eo in chain(self.eventClassGen(), self.eventClassKeyGen()):
            yield eo

    def run(self):
        results = defaultdict(list)
        print "Running report\n\n...."

	print "Event Class Keys that have regexs"
        print "================================="
        for eck in self.eventClassKeyGen():
            if eck.regex:
                self.printEventDetail(eck.getPrimaryUrlPath(), eck.regex, eck.rule)

        print "\n\n"
        print "Regex Event Class Keys that dont have rules...."
        print "-------------------------------------"
        for eck in self.eventClassKeyGen():
            if eck.regex and not eck.rule:
                self.printEventDetail(eck.getPrimaryUrlPath(), eck.regex, eck.rule)

        print "\n\n"
        print "EventClasses and Keys set to drop that are not in /Ignore event class"
        for eck in self.eventOrganizersGen():
            # if it walks like a duck
            if 'Ignore' in eck.getPrimaryUrlPath():
                continue
   	
	    if eck.zEventAction == 'drop':
                print eck.getPrimaryUrlPath() 

        print "\n\n"
        print "Events in /Ignore that have action set to status"
        for eck in self.eventClassKeyGen():
            if eck.getEventClass().startswith('/Ignore'):
                if eck.zEventAction == 'status':
                    print eck.getPrimaryUrlPath()


	print "\n\n"
        print "Event classes and Keys that are set to Archive"
	for eck in self.eventOrganizersGen():
            if eck.zEventAction == 'history':
                print eck.getPrimaryUrlPath()

        print "\n\n"
        print "Events with zEventClearClasses Set"
        for eck in self.eventOrganizersGen():
            if eck.zEventClearClasses:
               print eck.getPrimaryUrlPath()
               print eck.zEventClearClasses

        print "\n\n"
        print "more than one event class key in zenoss"
        results = Counter()
        for eck in self.dmd.Events.getInstances():
            results.update((eck.eventClassKey, ))
        for maybeDups in results.elements():
	    if results[maybeDups] > 1 and maybeDups != 'defaultmapping':
               print maybeDups 

        """ NOT IMPLEMENTED YET
        print "\n\n"
        print "Event Transforms that Reference devices no longer in zenoss"
        for eck in self.dmd.Events.getInstances():
        """

        """ NOT IMPLEMENTED YET
        print "\n\n"
        print "Transforms or rules that reference device classes that no longer exist"
        """

if __name__ == '__main__':
    print "Connecting to DMD..."
    tool = SimpleScriptRunner(connect=True)
    tool.run()
