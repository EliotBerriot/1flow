# -*- coding: utf-8 -*-
"""
    1flow "core" application. It's an Ember.JS based application, which
    explains why we don't have much things here. Everything takes place
    in the static/ and templates/ directories.

"""
import time
import redis
import logging
import simplejson as json

from django.conf import settings

LOGGER = logging.getLogger(__name__)

REDIS = redis.StrictRedis(host=getattr(settings, 'MAIN_SERVER',
                          'localhost'), port=6379,
                          db=getattr(settings, 'REDIS_DB', 0))


class GoogleReaderImport(object):

    def __init__(self, user):
        self.key_base = 'gri:{0}'.format(user.id)

    @classmethod
    def __time_key(cls, key, set_time=False):

        if set_time:
            return REDIS.set(key, time.time())

        return REDIS.get(key)

    @classmethod
    def __int_incr_key(cls, key, increment=False):

        if increment == 'reset':
            # return, else we increment to 1…
            return REDIS.delete(key)

        if increment:
            return REDIS.incr(key)

        return REDIS.get(key)

    @classmethod
    def __int_set_key(cls, key, set_value=None):

        if set_value is None:
            return REDIS.get(key)

        return REDIS.set(key, set_value)

    def user_infos(self, infos=None):

        key = self.key_base + ':i'

        if infos is None:
            return REDIS.get(key)

        return REDIS.set(key, json.dumps(infos))

    def running(self, set_running=None):

        if set_running is None:
            return REDIS.get(self.key_base)

        return REDIS.set(self.key_base, set_running)

    def start(self, set_time=False, user_infos=None):

        if set_time:
            LOGGER.debug('start reset for %s', self)
            self.running(set_running=True)
            self.articles('reset')
            self.feeds('reset')
            self.total_articles(0)
            self.total_feeds(0)

        if user_infos is not None:
            self.user_infos(user_infos)

        return GoogleReaderImport.__time_key(self.key_base + ':s', set_time)

    def end(self, set_time=False):

        self.running(set_running=False)

        return GoogleReaderImport.__time_key(self.key_base + ':e', set_time)

    def incr_feeds(self):
        return self.feeds(increment=True)

    def feeds(self, increment=False):

        return GoogleReaderImport.__int_incr_key(
            self.key_base + ':f', increment)

    def total_feeds(self, set_total=None):

        return GoogleReaderImport.__int_set_key(
            self.key_base + ':tf', set_total)

    def incr_articles(self):
        return self.articles(increment=True)

    def articles(self, increment=False):

        return GoogleReaderImport.__int_incr_key(
            self.key_base + ':a', increment)

    def total_articles(self, set_total=None):

        return GoogleReaderImport.__int_set_key(
            self.key_base + ':ta', set_total)
