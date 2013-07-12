# -*- coding: utf-8 -*-
# pylint: disable=E1103,C0103

import redis
import logging

from django.conf import settings
from django.test import TestCase  # TransactionTestCase

from oneflow.base.utils import RedisSemaphore

LOGGER = logging.getLogger(__file__)

TEST_REDIS = redis.StrictRedis(host=getattr(settings, 'MAIN_SERVER',
                               'localhost'), port=6379,
                               db=getattr(settings,
                                          'REDIS_TEST_DB', 9))
# Use the test database not to pollute the production/development one.
RedisSemaphore.REDIS = TEST_REDIS


class RedisSemaphoreTests(TestCase):

    def setUp(self):
        #
        # NOTE: nose seems to run tests in any different order at each call.
        #       We thus have to start from scratch for each method.
        #       We wipe the REDIS test DB before starting, anyway.

        TEST_REDIS.flushdb()

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
