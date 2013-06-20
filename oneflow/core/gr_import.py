# -*- coding: utf-8 -*-
"""
    1flow "core" application. It's an Ember.JS based application, which
    explains why we don't have much things here. Everything takes place
    in the static/ and templates/ directories.

"""

import time
import redis
import logging
import datetime
import simplejson as json

from humanize.time import naturaldelta

from django.conf import settings

LOGGER = logging.getLogger(__name__)

REDIS = redis.StrictRedis(host=getattr(settings, 'MAIN_SERVER',
                          'localhost'), port=6379,
                          db=getattr(settings, 'REDIS_DB', 0))

ftstamp = datetime.datetime.fromtimestamp
boolcast = {
    'True': True,
    'False': False,
    'None': None
}


class GoogleReaderImport(object):
    """ A small wrapper to get cached and up-to-date results from a GR import.

        We explicitely need to cast return values.

        See http://stackoverflow.com/a/13060733/654755 for details.

        It should normally not be needed (cf.
        https://github.com/andymccurdy/redis-py#response-callbacks) but
        for an unknown reason it made me crazy and I finally re-casted
        them again to make the whole thing work.
    """

    def __init__(self, user):
        self.key_base = 'gri:{0}'.format(user.id)

    @classmethod
    def __time_key(cls, key, set_time=False, time_value=None):

        if set_time:
            return REDIS.set(key, time.time()
                             if time_value is None else time_value)

        return ftstamp(float(REDIS.get(key) or 0.0))

    @classmethod
    def __int_incr_key(cls, key, increment=False):

        if increment == 'reset':
            # return, else we increment to 1…
            return REDIS.delete(key)

        if increment:
            return REDIS.incr(key)

        return int(REDIS.get(key) or 0)

    @classmethod
    def __int_set_key(cls, key, set_value=None):

        if set_value is None:
            return int(REDIS.get(key) or 0)

        return REDIS.set(key, set_value)

    def user_infos(self, infos=None):

        key = self.key_base + ':uif'

        if infos is None:
            return REDIS.get(key)

        return REDIS.set(key, json.dumps(infos))

    def running(self, set_running=None):

        # Just to be sure we need to cast…
        # LOGGER.warning('running: set=%s, value=%s type=%s',
        #                set_running, REDIS.get(self.key_base),
        #                type(REDIS.get(self.key_base)))

        if set_running is None:
            return boolcast[REDIS.get(self.key_base)]

        return REDIS.set(self.key_base, set_running)

    def start(self, set_time=False, user_infos=None):

        if set_time:
            LOGGER.debug('start reset for %s', self)
            self.running(set_running=True)

            self.feeds('reset')
            self.reads('reset')
            self.starred('reset')
            self.articles('reset')

            self.total_feeds(0)
            self.total_reads(0)

        if user_infos is not None:
            self.user_infos(user_infos)

        return GoogleReaderImport.__time_key(self.key_base + ':start', set_time)

    def end(self, set_time=False):

        if self.running():
            self.running(set_running=False)
            return GoogleReaderImport.__time_key(self.key_base + ':end',
                                                 set_time)

            LOGGER.info(u'Import statistics: %s article(s), %s read, '
                        u'%s starred, %s feed(s) in %s).',
                        self.articles(), self.reads(), self.starred(),
                        self.feeds(), naturaldelta(self.end() - self.start()))

        return GoogleReaderImport.__time_key(self.key_base + ':end', False)

    def reg_date(self, set_date=None):

        date = GoogleReaderImport.__time_key(self.key_base + ':rd',
                                             set_time=set_date is not None,
                                             time_value=set_date)

        if set_date is None:
            return ftstamp(float(date or 0.0))

        return date

    def must_stop(self, set_stop=None):
        # NOT USED ?
        return GoogleReaderImport.__int_set_key(
            self.key_base + ':stp',
            {None: None, False: 0, True: 1}[set_stop])

    def incr_feeds(self):
        return self.feeds(increment=True)

    def feeds(self, increment=False):

        return GoogleReaderImport.__int_incr_key(
            self.key_base + ':fds', increment)

    def total_feeds(self, set_total=None):

        return GoogleReaderImport.__int_set_key(
            self.key_base + ':tfs', set_total)

    def incr_reads(self):
        return self.reads(increment=True)

    def incr_starred(self):
        return self.starred(increment=True)

    def incr_articles(self):
        return self.articles(increment=True)

    def reads(self, increment=False):

        return GoogleReaderImport.__int_incr_key(
            self.key_base + ':rds', increment)

    def starred(self, increment=False):

        return GoogleReaderImport.__int_incr_key(
            self.key_base + ':str', increment)

    def articles(self, increment=False):

        return GoogleReaderImport.__int_incr_key(
            self.key_base + ':arts', increment)

    def total_reads(self, set_total=None):

        return GoogleReaderImport.__int_set_key(
            self.key_base + ':trds', set_total)
