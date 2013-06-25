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

from constance import config
from django.conf import settings
from django.contrib.auth import get_user_model

from .models.nonrel import Article

LOGGER = logging.getLogger(__name__)

REDIS = redis.StrictRedis(host=getattr(settings, 'MAIN_SERVER',
                          'localhost'), port=6379,
                          db=getattr(settings, 'REDIS_DB', 0))

User = get_user_model()

now     = datetime.datetime.now
ftstamp = datetime.datetime.fromtimestamp
today   = datetime.date.today

boolcast = {
    'True': True,
    'False': False,
    'None': None,
    # The real None is needed in case of a non-existing key.
    None: None
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

    def __init__(self, user_id):
        self.user_id  = user_id
        self.key_base = 'gri:{0}'.format(user_id)
        self._speeds  = None

    @property
    def is_active(self):
        return today() < config.GR_END_DATE \
            and Article.objects().count() < config.GR_STORAGE_LIMIT

    @property
    def can_import(self):
        if self.is_active:

            user = User.objects.get(id=self.user_id)

            try:
                return user.profile.data.get('GR_IMPORT_ALLOWED',
                                             config.GR_IMPORT_ALLOWED)

            except:
                LOGGER.exception(u'Could not get `data` from user %s profile, '
                                 u'returning configuration value %s.',
                                 user.username, config.GR_IMPORT_ALLOWED)
                return config.GR_IMPORT_ALLOWED

        return False

    @can_import.setter # NOQA
    def can_import(self, yes_no):
        user = User.objects.get(id=self.user_id)
        user.profile.data['GR_IMPORT_ALLOWED'] = bool(yes_no)
        user.profile.save()

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
            return int(REDIS.incr(key))

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

        key = self.key_base + ':run'

        # Just to be sure we need to cast…
        # LOGGER.warning('running: set=%s, value=%s type=%s',
        #                set_running, REDIS.get(self.key_base),
        #                type(REDIS.get(self.key_base)))

        if set_running is None:
            return boolcast[REDIS.get(key)]

        return REDIS.set(key, set_running)

    def start(self, set_time=False, user_infos=None):

        if set_time:
            #LOGGER.debug('start reset for %s', self)
            self.running(set_running=True)

            self.feeds('reset')
            self.reads('reset')
            self.starred('reset')
            self.articles('reset')

            self.total_feeds(0)
            self.total_reads(0)
            self.total_starred(0)

        if user_infos is not None:
            self.user_infos(user_infos)

        return GoogleReaderImport.__time_key(self.key_base + ':start', set_time)

    def end(self, set_time=False):

        if self.running():
            self.running(set_running=False)

        return GoogleReaderImport.__time_key(self.key_base + ':end', set_time)

    def reg_date(self, set_date=None):

        return GoogleReaderImport.__time_key(self.key_base + ':regd',
                                             set_time=set_date is not None,
                                             time_value=set_date)

    def star1_date(self, set_date=None):

        return GoogleReaderImport.__time_key(self.key_base + ':stad',
                                             set_time=set_date is not None,
                                             time_value=set_date)

    def incr_feeds(self):
        feeds = self.feeds(increment=True)

        if feeds == self.total_feeds():
            self.end(True)

        #LOGGER.debug('FEEDS: %s =? %s', feeds, self.total_feeds())

        return feeds

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
            self.key_base + ':sta', increment)

    def articles(self, increment=False):

        return GoogleReaderImport.__int_incr_key(
            self.key_base + ':arts', increment)

    def total_reads(self, set_total=None):

        return GoogleReaderImport.__int_set_key(
            self.key_base + ':trds', set_total)

    def total_starred(self, set_total=None):

        return GoogleReaderImport.__int_set_key(
            self.key_base + ':tsta', set_total)

    def speeds(self):

        def duration_since(start):
            delta = (now() if self.running() else self.end()) - start
            return delta.seconds + delta.microseconds / 1E6 + delta.days * 86400

        since_start = duration_since(self.start())

        self._speeds = {
            # We use 'or 1.0' to avoid division by zero errors
            'global' : (self.articles() / since_start) or 1.0,
            'starred': (self.starred()  / since_start) or 1.0,
            'time'   : time.time()  # used for expiration check
        }

        if self.reads() < self.total_reads():
            self._speeds['reads'] = (self.reads() / since_start) or 1.0

        return self._speeds

    def eta(self):
        """ If running, compute fetching speeds (if not already done in the
            last second), and return the worst to get a reliable enough ETA.

            If not running, don't compute anything and return ``None``.
        """

        if self.running():
            if self._speeds is None or time.time() - self._speeds['time'] > 1:
                self.speeds()

            seconds_starred = (self.total_starred() - self.starred()
                               ) / self._speeds['starred']
            maximums = (seconds_starred, )

            if 'reads' in self._speeds:
                seconds_reads = (self.total_reads() - self.reads()
                                 ) / self._speeds['reads']
                maximums += (seconds_reads, )
            else:
                maximums += (0.0, )

            return now() + datetime.timedelta(seconds=max(*maximums))
        else:
            return None
