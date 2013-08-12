# -*- coding: utf-8 -*-

import uuid
import time
import redis
import logging

from django.conf import settings

from ..utils import RedisExpiringLock, AlreadyLockedException
from ..utils.dateutils import ftstamp

LOGGER = logging.getLogger(__name__)

REDIS = redis.StrictRedis(host=settings.REDIS_DESCRIPTORS_HOST,
                          port=settings.REDIS_DESCRIPTORS_PORT,
                          db=settings.REDIS_DESCRIPTORS_DB)


class RedisCachedDescriptor(object):
    """ A simple descriptor that uses values from a REDIS database.

        Besides the REDIS storage, it implements an instance-level cache
        to avoid the REDIS I/O on ``__get__`` calls if possible. This
        cache doesn't affect the ``__set__`` and ``__del__`` calls,
        which are always forwarded to REDIS.

        You can disable the cache by setting :param:`cache` to ``False``
        in the descriptor class (or any inherited class) constructor.

        .. note:: :param:`default` can be a callable. It will be passed
            the instance as first argument when it is called. In this
            particular case (and only this one), the ``default`` call
            will be protected by a network-wide re-entrant lock. Be aware
            that the :meth:`__get__` method call can eventually raise
            an ``AlreadyLockedException`` if there is any kind of race
            between callers. This should be quite rare, though. But you
            still need to cover the case.

        :param set_default: in case there is no value and the default is
            returned, store it as the new current value. Useful if your
            default is a callable that does a lot of computations, and
            you want to set it as a base value at some point in time.
            Not enabled by default (eg. the default value is returned
            but not stored).
    """

    REDIS = None

    def __init__(self, attr_name, cls_name=None, default=None,
                 cache=True, set_default=False):

        #
        # As MongoDB IDs are unique accross databases and objects,
        # the current descriptor doesn't need class name for unicity
        # guaranties.
        #
        # TODO: find a way to check if the class we are attaching on is
        #   a MongoDB document or not, or any way to be sure `self.key_name`
        #   is unique accross the application, to avoid nasty clashes.
        #
        self.default     = default
        self.cache       = cache
        self.set_default = set_default
        self.uuid        = uuid.uuid4().hex

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
                if callable(self.default):
                    # We are in a Multi-node environment. Protect the default
                    # value computation against parallel execution, else the
                    # callers could get bad results.
                    val = self.__protected_default(instance)

                    if self.set_default:
                        self.__set__(instance, val)

                    return val

                if self.set_default:
                    self.__set__(instance, self.default)

                return self.default

            return self.to_python(val)

    def __protected_default(self, instance):
        """ This method is the only part which uses a network-enabled
            re-entrant lock, to avoid the extra resources cost in case
            of a non-callable default value. """

        my_lock = RedisExpiringLock(instance, lock_name=self.cache_key,
                                    lock_value=self.uuid)

        if my_lock.acquire(reentrant_id=self.uuid):
            try:
                return self.default(instance)

            finally:
                my_lock.release()
        else:
            # Gosh, the lock is taken. Wait for release() and return
            # another __get__() call once the holder releases it. The new
            # __get__() will either return the database value if now set,
            # or re-run a default() call if we are not lucky. But in this
            # particular case, we will have protected ourselves with the
            # re-entrant lock to be sure this will succeed.

            while my_lock.is_locked():
                # The lock *will* expire at some time.
                # No need for complex conditions here.
                time.sleep(0.5)

            # Be sure that we don't get into a dead-lock, or any bad loop.
            if my_lock.acquire(reentrant_id=self.uuid):
                try:
                    return self.__get__(instance)
                finally:
                    my_lock.release()
            else:
                raise AlreadyLockedException(
                    'Too much effort required to get the lock.')

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


class IntRedisDescriptor(RedisCachedDescriptor):
    """ Integer specific version of the
        generic :class:`RedisCachedDescriptor`.

        See :class:`RedisCachedDescriptor` for generic descriptor information
        (like callable default values and network-wide locking semantics).
    """

    def to_python(self, value):

        try:
            return int(value)

        except TypeError:
            return None

    #
    # NOTE: no need for a to_redis() method.
    #       Already covered by base class.
    #


class DatetimeRedisDescriptor(RedisCachedDescriptor):
    """ Datetime specific version of the
        generic :class:`RedisCachedDescriptor`.

        See :class:`RedisCachedDescriptor` for generic descriptor information
        (like callable default values and network-wide locking semantics).
    """

    def to_python(self, value):

        try:
            return ftstamp(float(value))

        except TypeError:
            return None

    def to_redis(self, value):

        return time.mktime(value.timetuple())


class ListRedisProxy(list):

    def __init__(self, parent_descriptor, hydrate_func=lambda x: x,
                 dehydrate_func=lambda x: x):
        self.parent = parent_descriptor

    def append(self, value):
        pass

    def remove(self, value):
        pass

    def __len__(self):
        return self.parent.REDIS.llen()


class ListRedisDescriptor(RedisCachedDescriptor):

    PROXY = ListRedisProxy

    def to_python(self, value):
        return self.PROXY(self).to_python(value)

    def to_redis(self, value):
        return [self.to_redis_one(x) for x in value]
