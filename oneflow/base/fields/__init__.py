# -*- coding: utf-8 -*-

import time
import redis
import logging
import datetime

from django.conf import settings

LOGGER = logging.getLogger(__name__)

REDIS = redis.StrictRedis(host=getattr(settings, 'MAIN_SERVER',
                                       'localhost'), port=6379,
                          db=getattr(settings, 'REDIS_DESCRIPTORS_DB', 3))

now     = datetime.datetime.now
ftstamp = datetime.datetime.fromtimestamp
today   = datetime.date.today


class RedisCachedDescriptor(object):
    """ A simple descriptor that uses values from a REDIS database.

        Besides the REDIS storage, it implements an instance-level cache
        to avoid the REDIS I/O on ``__get__`` calls if possible. This
        cache doesn't affect the ``__set__`` and ``__del__`` calls,
        which are always forwarded to REDIS.

        You can disable the cache by setting :param:`cache` to ``False``
        in the descriptor class (or any inherited class) constructor.
    """

    REDIS = None

    def __init__(self, attr_name, cls_name=None, default=None, cache=True):

        #
        # As MongoDB IDs are unique accross databases and objects,
        # the current descriptor doesn't need class name for unicity
        # guaranties.
        #
        # TODO: find a way to check if the class we are attaching on is
        #   a MongoDB document or not, or any way to be sure `self.key_name`
        #   is unique accross the application, to avoid nasty clashes.
        #
        self.default  = default
        self.cache    = cache

        # NOTE: we use '_' instead of the classic ':' to be compatible
        # with the instance cache, which is a standard Python attribute.
        self.cache_key = '%s%s_' % ((cls_name.replace(
                                    '.', '_').replace(':', '_')
                                        + '_') if cls_name else '',
                                    attr_name.replace(
                                    '.', '_').replace(':', '_'))
        self.key_name = '%s%%s' % self.cache_key

        # LOGGER.warning('INIT: %s > %s, cache: %s, default: %s',
        #                self.cache_key, self.key_name, cache, default)

    def __get__(self, instance, objtype=None):

        if instance is None:
            raise AttributeError('Can only be accessed via an instance.')

        if self.cache:
            # LOGGER.warning('GET-cache: %s %s', instance,
            #                '_r_c_d_' + self.cache_key)

            try:
                # Avoid the REDIS I/O if possible.
                return getattr(instance, '_r_c_d_' + self.cache_key)

            except AttributeError:
                # NAH. first-time __get__?
                key_name = '_r_c_d_' + self.cache_key
                value    = self.__get_internal(instance, objtype)

                setattr(instance, key_name, value)

                # LOGGER.warning('CREATE-cache: %s %s %s',
                #                instance, key_name, value)

                return getattr(instance, key_name)

        else:
            return self.__get_internal(instance)

    def to_python(self, value):

        # for the default descriptor, this is the identity method.
        return value

    def to_redis(self, value):

        return value

    def __get_internal(self, instance, objtype=None):

        #LOGGER.warning('GET-redis: %s', self.key_name % instance.id)

        if self.default is None:

            # Let REDIS return None, anyway.
            return self.to_python(self.REDIS.get(self.key_name % instance.id))

        else:
            val = self.REDIS.get(self.key_name % instance.id)

            if val is None:
                # could be 'return self.default or None', but
                # default is already None if there is no default…
                return self.default

            return self.to_python(val)

    def __set__(self, instance, value):

        #LOGGER.warning('SET-redis: %s %s', self.key_name % instance.id, value)

        # Always store into REDIS, whatever the cache. We need persistence.
        self.REDIS.set(self.key_name % instance.id, self.to_redis(value))

        if self.cache:
            # LOGGER.warning('SET-cache: %s %s %s', instance,
            #                '_r_c_d_' + self.key_name, value)

            # But next __get__ should benefit from the cache.
            setattr(instance, '_r_c_d_' + self.cache_key, value)

    def __delete__(self, instance):

        #LOGGER.warning('DELETE-redis: %s', self.key_name % instance.id)

        self.REDIS.delete(self.key_name % instance.id)

        if self.cache:
            # LOGGER.warning('DELETE-cache: %s %s', instance,
            #                '_r_c_d_' + self.cache_key)
            delattr(instance, '_r_c_d_' + self.cache_key)

# Allow to override this in tests
RedisCachedDescriptor.REDIS = REDIS


class DatetimeRedisDescriptor(RedisCachedDescriptor):
    """ Datetime specific version of the
        generic :class:`RedisCachedDescriptor`. """

    def to_python(self, value):

        try:
            return ftstamp(float(value))

        except TypeError:
            return None

    def to_redis(self, value):

        return time.mktime(value.timetuple())
