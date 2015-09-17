#!/usr/bin/env python
__version__ = "0.0.1"

import datetime
import Globals
from Products.ZenUtils.ZenScriptBase import ZenScriptBase
from Products.ZenUtils import unused
from ZODB.transact import transact
unused(Globals)


class OldJobsCleaner(object):
    """ deletes old jobs > 3 months old  """

    def __init__(self, dmd, log):
        self.dmd = dmd
        self.jm = dmd.JobManager
        self.log = log
        self.clean_older_than_days = 95

    def __call__(self):
        now = datetime.datetime.now()
        delta = datetime.timedelta(self.clean_older_than_days)        
        x_days_ago = now - delta

        jobs_to_go = [job.id for job in self.jm.getAllJobs() if job.finished and job.finished < x_days_ago]

        if jobs_to_go:
            self.log.info('Deleting %s Jobs', len(jobs_to_go))
            self.deleteOldJobs(jobs_to_go)
            return

        self.log.info('No maintenance windows needed to be removed')

    @transact
    def deleteOldJobs(self, jobs):
        self.log.info('Removing %d jobs', len(jobs))
        map(self.jm.deleteJob, jobs)

if __name__ == "__main__":
    jccmd = ZenScriptBase(connect=True)
    jccmd.setupLogging()
    jccmd.log.info('OldJobsClaner  Cleanup Script running')
    JOB_CLEANER = OldJobsCleaner(jccmd.dmd, jccmd.log)
    JOB_CLEANER()
    jccmd.log.info('Old Job Cleaner completed sucessfully')
