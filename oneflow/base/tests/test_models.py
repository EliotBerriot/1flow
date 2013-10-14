# -*- coding: utf-8 -*-
# pylint: disable=E1103,C0103

import uuid
import redis
import logging

from django.conf import settings
from django.test import TestCase  # TransactionTestCase

from ..utils import RedisSemaphore
from ..fields import RedisCachedDescriptor, IntRedisDescriptor

LOGGER = logging.getLogger(__file__)

TEST_REDIS = redis.StrictRedis(host=settings.REDIS_TEST_HOST,
                               port=settings.REDIS_TEST_PORT,
                               db=settings.REDIS_TEST_DB)

# Use the test database not to pollute the production/development one.
RedisSemaphore.REDIS = TEST_REDIS
RedisCachedDescriptor.REDIS = TEST_REDIS

TEST_REDIS.flushdb()


class RedisSemaphoreTests(TestCase):

    def setUp(self):
        #
        # NOTE: nose seems to run tests in any different order at each call.
        #       We thus have to start from scratch for each method.
        #       We wipe the REDIS test DB before starting, anyway.
        pass

    def test_simple_acquire_release(self):

        self.sem1 = RedisSemaphore('test1', 5)

        self.assertEquals(self.sem1.holders(), 0)

        res = self.sem1.acquire()

        self.assertEquals(res, True)

        self.sem1.acquire()

        self.assertEquals(self.sem1.holders(), 2)

        self.sem1.release()

        self.assertEquals(self.sem1.holders(), 1)

    def test_acquire_until_limit(self):

        self.sem1 = RedisSemaphore('test2', 5)

        self.assertEquals(self.sem1.holders(), 0)

        res = self.sem1.acquire()

        self.assertEquals(res, True)

        self.assertEquals(self.sem1.holders(), 1)

        self.sem1.acquire()
        self.sem1.acquire()
        self.sem1.acquire()
        self.sem1.acquire()

        self.assertEquals(self.sem1.holders(), 5)

    def test_acquire_after_limit(self):

        self.sem1 = RedisSemaphore('test3', 5)

        self.assertEquals(self.sem1.holders(), 0)

        # 5 get it
        self.sem1.acquire()
        self.sem1.acquire()
        self.sem1.acquire()
        self.sem1.acquire()
        self.sem1.acquire()

        self.assertEquals(self.sem1.holders(), 5)

        # The Sixth fails.
        res = self.sem1.acquire()

        self.assertEquals(res, False)

        self.assertEquals(self.sem1.holders(), 5)

    def test_release_until_zero(self):

        self.sem1 = RedisSemaphore('test4', 5)

        self.assertEquals(self.sem1.holders(), 0)

        # 5 get it
        self.sem1.acquire()
        self.sem1.acquire()
        self.sem1.acquire()
        self.sem1.acquire()
        self.sem1.acquire()

        self.assertEquals(self.sem1.holders(), 5)

        # 5 release it
        self.sem1.release()
        self.sem1.release()
        self.sem1.release()
        self.sem1.release()
        self.sem1.release()

        self.assertEquals(self.sem1.holders(), 0)

    def test_release_after_zero(self):

        self.sem1 = RedisSemaphore('test5', 5)

        self.assertEquals(self.sem1.holders(), 0)

        # 5 get it
        self.sem1.acquire()
        self.sem1.acquire()
        self.sem1.acquire()
        self.sem1.acquire()
        self.sem1.acquire()

        # 5 release it
        self.sem1.release()
        self.sem1.release()
        self.sem1.release()
        self.sem1.release()
        self.sem1.release()

        # 6th releases it
        res = self.sem1.release()

        self.assertEquals(res, False)

        self.assertEquals(self.sem1.holders(), 0)


class IntRedisCachedDescriptorTest(TestCase):

    def setUp(self):

        # Warning: not inheriting from `object`
        # in Python 2.7 makes the whole thing fail.
        class IRCDT(object):
            i1   = IntRedisDescriptor('test_redis_descr_1')
            imin = IntRedisDescriptor('test_redis_descr_min', min_value=0)
            imax = IntRedisDescriptor('test_redis_descr_max', max_value=100)

            def __init__(self, myid=None):
                self.id = myid

        self.IRCDT = IRCDT

    def int_redis_descriptor_test(self):

        tird = self.IRCDT()

        tird.i1 = 5
        self.assertEquals(tird.i1, 5)

        tird.i1 -= 15
        self.assertEquals(tird.i1, -10)

        tird.i1 += 22
        self.assertEquals(tird.i1, 12)

        del tird

    def test_min_value(self):

        tmin = self.IRCDT(uuid.uuid4().hex)

        tmin.imin = 5
        self.assertEquals(tmin.imin, 5)

        tmin.imin -= 1
        self.assertEquals(tmin.imin, 4)

        tmin.imin -= 5
        self.assertEquals(tmin.imin, 0)

        tmin.imin -= 5
        self.assertEquals(tmin.imin, 0)

        tmin.imin += 10
        self.assertEquals(tmin.imin, 10)

        del tmin

    def test_max_value(self):

        tmax = self.IRCDT(uuid.uuid4().hex)
        tmax.imax = 5

        self.assertEquals(tmax.imax, 5)

        tmax.imax += 150

        self.assertEquals(tmax.imax, 100)

        tmax.imax -= 200

        self.assertEquals(tmax.imax, -100)
