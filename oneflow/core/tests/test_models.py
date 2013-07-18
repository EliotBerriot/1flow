# -*- coding: utf-8 -*-
# pylint: disable=E1103,C0103

import redis
import logging

from constance import config
from mongoengine.connection import connect, disconnect

from django.conf import settings
from django.test import TestCase  # TransactionTestCase
#from django.test.utils import override_settings

from oneflow.core.models import Feed, Article, FeedStatsCounter
from oneflow.base.utils import RedisStatsCounter

LOGGER = logging.getLogger(__file__)

TEST_REDIS = redis.StrictRedis(host=settings.REDIS_TEST_HOST,
                               port=settings.REDIS_TEST_PORT,
                               db=settings.REDIS_TEST_DB)


# Use the test database not to pollute the production/development one.
RedisStatsCounter.REDIS = TEST_REDIS
FeedStatsCounter.REDIS  = TEST_REDIS

TEST_REDIS.flushdb()

disconnect()
connect('oneflow_testsuite')


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


class ThrottleIntervalTest(TestCase):

    def test_lower_interval_with_etag_or_modified(self):

        t = Feed.throttle_fetch_interval

        some_news = 10
        no_dupe   = 0

        self.assertEquals(t(1000, some_news, no_dupe, 'etag', 'last_modified'),
                          666.6666666666666)
        self.assertEquals(t(1000, some_news, no_dupe, '', 'last_modified'),
                          666.6666666666666)
        self.assertEquals(t(1000, some_news, no_dupe, None, 'last_modified'),
                          666.6666666666666)

        self.assertEquals(t(1000, some_news, no_dupe, 'etag', ''),
                          666.6666666666666)
        self.assertEquals(t(1000, some_news, no_dupe, 'etag', None),
                          666.6666666666666)

    def test_raise_interval_with_etag_or_modified(self):

        t = Feed.throttle_fetch_interval

        some_news = 10
        no_news   = 0
        a_dupe    = 1

        # news, but a dupe > raise-

        self.assertEquals(t(1000, some_news, a_dupe, 'etag', 'last_modified'),
                          1125)
        self.assertEquals(t(1000, some_news, a_dupe, '', 'last_modified'),
                          1125)
        self.assertEquals(t(1000, some_news, a_dupe, None, 'last_modified'),
                          1125)

        self.assertEquals(t(1000, some_news, a_dupe, 'etag', ''),   1125)
        self.assertEquals(t(1000, some_news, a_dupe, 'etag', None), 1125)

        # no news, a dupe > raise+

        self.assertEquals(t(1000, no_news, a_dupe, 'etag', 'last_modified'),
                          1250)
        self.assertEquals(t(1000, no_news, a_dupe, '', 'last_modified'),
                          1250)
        self.assertEquals(t(1000, no_news, a_dupe, None, 'last_modified'),
                          1250)

        self.assertEquals(t(1000, no_news, a_dupe, 'etag', ''),   1250)
        self.assertEquals(t(1000, no_news, a_dupe, 'etag', None), 1250)

    def test_lowering_interval_without_etag_nor_modified(self):

        t = Feed.throttle_fetch_interval

        some_news = 10
        no_dupe   = 0

        # news, no dupes > raise+ (etag don't count)

        self.assertEquals(t(1000, some_news, no_dupe, '', ''),
                          666.6666666666666)
        self.assertEquals(t(1000, some_news, no_dupe, None, None),
                          666.6666666666666)

    def test_raising_interval_without_etag_nor_modified(self):

        t = Feed.throttle_fetch_interval

        some_news = 10
        no_news   = 0
        a_dupe    = 1

        self.assertEquals(t(1000, some_news, a_dupe, '', ''), 1250)
        self.assertEquals(t(1000, some_news, a_dupe, None, None), 1250)

        self.assertEquals(t(1000, no_news, a_dupe, '', ''), 1500)
        self.assertEquals(t(1000, no_news, a_dupe, None, None), 1500)

    def test_less_news(self):

        t = Feed.throttle_fetch_interval

        more_news = config.FEED_FETCH_RAISE_THRESHOLD + 5
        less_news = config.FEED_FETCH_RAISE_THRESHOLD - 5
        just_one  = 1

        a_dupe  = 1
        no_dupe = 0

        self.assertEquals(t(1000, just_one, a_dupe, 'etag', ''),   1125)
        self.assertEquals(t(1000, less_news, a_dupe, 'etag', None), 1125)
        self.assertEquals(t(1000, more_news, a_dupe, 'etag', None), 1125)

        self.assertEquals(t(1000, just_one, no_dupe, 'etag', ''),   800)
        self.assertEquals(t(1000, less_news, no_dupe, 'etag', None), 800)
        self.assertEquals(t(1000, more_news, no_dupe, 'etag', None),
                          666.6666666666666)

    def test_limits(self):

        t = Feed.throttle_fetch_interval

        some_news = 10
        no_news   = 0
        a_dupe    = 1
        no_dupe   = 0

        # new articles already at max stay at max.
        self.assertEquals(t(config.FEED_FETCH_MAX_INTERVAL, no_news, a_dupe,
                          '', ''), config.FEED_FETCH_MAX_INTERVAL)
        self.assertEquals(t(config.FEED_FETCH_MAX_INTERVAL, no_news, a_dupe,
                          'etag', ''), config.FEED_FETCH_MAX_INTERVAL)
        self.assertEquals(t(config.FEED_FETCH_MAX_INTERVAL, no_news, a_dupe,
                          None, 'last_mod'), config.FEED_FETCH_MAX_INTERVAL)

        # dupes at min stays at min
        self.assertEquals(t(config.FEED_FETCH_MIN_INTERVAL, some_news, no_dupe,
                          '', ''), config.FEED_FETCH_MIN_INTERVAL)
        self.assertEquals(t(config.FEED_FETCH_MIN_INTERVAL, some_news, no_dupe,
                          'etag', None), config.FEED_FETCH_MIN_INTERVAL)
        self.assertEquals(t(config.FEED_FETCH_MIN_INTERVAL, some_news, no_dupe,
                          '', 'last_mod'), config.FEED_FETCH_MIN_INTERVAL)


#
# Doesn't work because of https://github.com/celery/celery/issues/1478
#
# @override_settings(STATICFILES_STORAGE=
#                    'pipeline.storage.NonPackagingPipelineStorage',
#                    CELERY_EAGER_PROPAGATES_EXCEPTIONS=True,
#                    CELERY_ALWAYS_EAGER=True,
#                    BROKER_BACKEND='memory',)
#
class ArticleDuplicateTest(TestCase):

    def setUp(self):

        Article.drop_collection()

        self.article1 = Article(title='test1',
                                url='http://test.com/test1').save()
        self.article2 = Article(title='test2',
                                url='http://test.com/test2').save()
        self.article3 = Article(title='test3',
                                url='http://test.com/test3').save()

    def test_register_duplicate_bare(self):

        self.assertEquals(Article.objects(
                          duplicate_of__exists=False).count(), 3)

        self.article1.register_duplicate(self.article2)

        self.assertEquals(self.article2.duplicate_of, self.article1)

        self.assertEquals(Article.objects(
                          duplicate_of__exists=True).count(), 1)
        self.assertEquals(Article.objects(
                          duplicate_of__exists=False).count(), 2)

    def test_register_duplicate_not_again(self):

        self.article1.register_duplicate(self.article2)

        self.assertRaises(RuntimeError,
                          self.article1.register_duplicate,
                          self.article3)

        self.assertEquals(self.article2.duplicate_of, self.article1)
