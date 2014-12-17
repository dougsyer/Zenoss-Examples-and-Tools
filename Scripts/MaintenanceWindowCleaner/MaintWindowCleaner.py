#!/usr/bin/env python
__version__ = "0.0.1"

import time
import Globals
from Products.ZenUtils.ZenScriptBase import ZenScriptBase
from Products.ZenUtils import unused
from ZODB.transact import transact
unused(Globals)


class MaintWindowCleaner(object):
    """  this class, when instantiated and run with an instance of dmd and logging
         will search for any maintenance windows that will never run again and deletes them
         loging can be found in $ZENHOME/zenscriptbase.log

         Part of this code was adapted from Schedule.py in Products/ZenEvents

         There is no display function but it would be easy to implement...this
         script is intended to be used with a cron job
         I perfer to try to keep dmd clean by removing stranded objects like
         old maint windows...
    """

    def __init__(self, dmd, log):
        self.dmd = dmd
        self.log = log

    def __call__(self):
        windows = self.getOldWindows(self.now(), self.getWindows())
        if windows:
            self.removeOldWindows(windows)
            return
        self.log.info('No maintenance windows needed to be removed')

    def now(self):
        return time.time()

    def getWindows(self):
        results = []
        catalog = getattr(self.dmd, 'maintenanceWindowSearch', None)
        for brain in catalog():
            results.append(brain.getObject())
        return results

    def getOldWindows(self, now, workList):
        """
        Removes maintenance windows that will never run again from dmd
        to do this it generates a list of tuples where 0 is the next time the
        window should run and the 1 index is the window itself.
        if index 0 is before the current time then the window is deleted
        """
        old_windows = []
        work = [(mw.nextEvent(now), mw) for mw in workList]
        work.sort()
        # note that None is less than any number of seconds
        while len(work):
            t, mw = work[0]
            if t: break
            if mw.enabled:
                old_windows.append(mw)
                self.log.info("Never going to run Maintenance "
                         "Window %s for %s again, adding to list for removal",
                               mw.getId(), mw.target().getId())
            work.pop(0)
        return old_windows

    @transact
    def removeOldWindows(self, windows):
        self.log.info('Removing %d Windows Now' % len(windows))
        for win in windows:
            winId = win.id
            parent = win.productionState()
            parent.manage_deleteMaintenanceWindow(maintenanceIds=(winId))


if __name__ == "__main__":
    mwcmd = ZenScriptBase(connect=True)
    mwcmd.setupLogging()
    mwcmd.log.info('Starting Maintenance mode Cleaning Script')
    MWC = MaintWindowCleaner(mwcmd.dmd, mwcmd.log)
    MWC()
    mwcmd.log.info('Maintenance Mode Cleaner completed sucessfully')
