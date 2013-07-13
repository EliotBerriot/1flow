# -*- coding: utf-8 -*-
# pylint: disable=E1103,C0103

import redis
import logging

from django.conf import settings
from django.test import TestCase  # TransactionTestCase

from oneflow.core.models.nonrel import Feed, FeedStatsCounter
from oneflow.base.utils import RedisStatsCounter

LOGGER = logging.getLogger(__file__)

TEST_REDIS = redis.StrictRedis(host=getattr(settings, 'MAIN_SERVER',
                               'localhost'), port=6379,
                               db=getattr(settings,
                                          'REDIS_TEST_DB', 9))


# Use the test database not to pollute the production/development one.
RedisStatsCounter.REDIS = TEST_REDIS
FeedStatsCounter.REDIS  = TEST_REDIS

TEST_REDIS.flushdb()


class FeedStatsCounterTests(TestCase):

    def setUp(self):
        self.global_counter = FeedStatsCounter()
        self.t1 = FeedStatsCounter('test1')
        self.t2 = FeedStatsCounter('test2')
        self.t3 = FeedStatsCounter(Feed.objects()[0])
        self.t4 = FeedStatsCounter(Feed.objects()[1])

    def test_feed_stats_counters(self):

        current_value = self.global_counter.fetched()

        self.t1.incr_fetched()
        self.t1.incr_fetched()
        self.t1.incr_fetched()
        self.t1.incr_fetched()

        self.assertEquals(self.t1.fetched(), 4)

        self.t2.incr_fetched()
        self.t2.incr_fetched()
        self.t2.incr_fetched()

        self.assertEquals(self.t2.fetched(), 3)

        self.assertEquals(self.global_counter.fetched(), current_value + 7)

    def test_feed_stats_counters_reset(self):

        self.t1.fetched('reset')
        self.global_counter.fetched('reset')

        self.assertEquals(self.t1.fetched(), 0)
        self.assertEquals(self.global_counter.fetched(), 0)

        self.t2.incr_fetched()
        self.t2.incr_fetched()
        self.t2.incr_fetched()

        # t2 has not been reset since first test method. This is intended.
        self.assertEquals(self.t2.fetched(), 6)

        self.assertEquals(self.global_counter.fetched(), 3)
