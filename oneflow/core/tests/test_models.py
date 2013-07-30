# -*- coding: utf-8 -*-
# pylint: disable=E1103,C0103

import redis
import logging

from constance import config
from mongoengine.connection import connect, disconnect

from django.conf import settings
from django.test import TestCase  # TransactionTestCase
#from django.test.utils import override_settings

from oneflow.core.models import Feed, Article, Read, User, Tag
from oneflow.base.utils import RedisStatsCounter

LOGGER = logging.getLogger(__file__)

TEST_REDIS = redis.StrictRedis(host=settings.REDIS_TEST_HOST,
                               port=settings.REDIS_TEST_PORT,
                               db=settings.REDIS_TEST_DB)


# Use the test database not to pollute the production/development one.
RedisStatsCounter.REDIS = TEST_REDIS

TEST_REDIS.flushdb()

disconnect()
connect('oneflow_testsuite')


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
        User.drop_collection()
        Feed.drop_collection()

        self.article1 = Article(title='test1',
                                url='http://test.com/test1').save()
        self.article2 = Article(title='test2',
                                url='http://test.com/test2').save()
        self.article3 = Article(title='test3',
                                url='http://test.com/test3').save()

        # User & Reads creation
        for u in xrange(1, 6):
            u = User(django_user=u).save()
            Read(user=u, article=self.article1).save()

        for u in xrange(6, 11):
            u = User(django_user=u).save()
            Read(user=u, article=self.article2).save()

        # Feeds creation
        for f in xrange(1, 6):
            f = Feed(url='http://test-feed%s.com' % f).save()
            self.article1.update(add_to_set__feeds=f)
            self.article1.reload()

        for f in xrange(6, 11):
            f = Feed(url='http://test-feed%s.com' % f).save()
            self.article2.update(add_to_set__feeds=f)
            self.article2.reload()

    def test_register_duplicate_bare(self):

        self.assertEquals(Article.objects(
                          duplicate_of__exists=False).count(), 3)

        self.article1.register_duplicate(self.article2)

        self.assertEquals(self.article1.reads.count(), 10)

        self.assertEquals(self.article2.reads.count(), 0)

        self.assertEquals(len(self.article1.feeds), 10)

        self.assertEquals(len(self.article2.feeds), 5)

        self.assertEquals(self.article2.duplicate_of, self.article1)

        self.assertEquals(Article.objects(
                          duplicate_of__exists=True).count(), 1)
        self.assertEquals(Article.objects(
                          duplicate_of__exists=False).count(), 2)

    def test_register_duplicate_not_again(self):

        self.article1.register_duplicate(self.article2)

        self.assertEquals(self.article2.duplicate_of, self.article1)


class AbsolutizeTest(TestCase):

    def setUp(self):

        Article.drop_collection()
        Feed.drop_collection()

        self.article1 = Article(title=u'test1',
                                url=u'http://rss.feedsportal.com/c/707/f/9951/s/2b27496a/l/0L0Sreseaux0Etelecoms0Bnet0Cactualites0Clire0Elancement0Emondial0Edu0Esamsung0Egalaxy0Es40E25980A0Bhtml/story01.htm').save() # NOQA
        self.article2 = Article(title=u'test2',
                                url=u'http://feedproxy.google.com/~r/francaistechcrunch/~3/hEIhLwVyEEI/').save() # NOQA
        self.article3 = Article(title=u'test3',
                                url=u'http://obi.1flow.io/absolutize_test_401').save() # NOQA
        self.article4 = Article(title=u'test4',
                                url=u'http://host.non.exixstentz.com/absolutize_test').save() # NOQA
        self.article5 = Article(title=u'test5',
                                url=u'http://1flow.io/absolutize_test_404').save() # NOQA

    def test_absolutize(self):
        self.article1.absolutize_url()
        self.assertEquals(self.article1.url, u'http://www.reseaux-telecoms.net/actualites/lire-lancement-mondial-du-samsung-galaxy-s4-25980.html') # NOQA
        self.assertEquals(self.article1.url_absolute, True)
        self.assertEquals(self.article1.url_error, '')

        self.article2.absolutize_url()
        self.assertEquals(self.article2.url, u'http://techcrunch.com/2013/05/18/hell-no-tumblr-users-wont-go-to-yahoo/') # NOQA
        self.assertEquals(self.article2.url_absolute, True)
        self.assertEquals(self.article2.url_error, '')

    def test_absolutize_erros(self):
        self.article3.absolutize_url()
        self.assertEquals(self.article3.url, u'http://obi.1flow.io/absolutize_test_401') # NOQA
        self.assertEquals(self.article3.url_absolute, False)
        self.assertEquals(self.article3.url_error, u'HTTP Error 401 (Unauthorized) while resolving http://obi.1flow.io/absolutize_test_401.') # NOQA

        self.article5.absolutize_url()
        self.assertEquals(self.article5.url, u'http://1flow.io/absolutize_test_404') # NOQA
        self.assertEquals(self.article5.url_absolute, False)
        self.assertEquals(self.article5.url_error, u'HTTP Error 404 (NOT FOUND) while resolving http://1flow.io/absolutize_test_404.') # NOQA

        self.article4.absolutize_url()
        self.assertEquals(self.article4.url, u'http://host.non.exixstentz.com/absolutize_test') # NOQA
        self.assertEquals(self.article4.url_absolute, False)
        self.assertEquals(self.article4.url_error[:108], u"HTTPConnectionPool(host='host.non.exixstentz.com', port=80): Max retries exceeded with url: /absolutize_test") # NOQA


class TagsTest(TestCase):

    def setUp(self):

        Tag.drop_collection()

        self.t1 = Tag(name='test1').save()
        self.t2 = Tag(name='test2').save()
        self.t3 = Tag(name='test3').save()

    def test_add_parent(self):

        self.t2.add_parent(self.t1)
        self.t3.add_parent(self.t1)

        self.assertEquals(self.t1 in self.t2.parents, True)
        self.assertEquals(self.t1 in self.t3.parents, True)

        self.assertEquals(self.t2 in self.t1.children, True)
        self.assertEquals(self.t3 in self.t1.children, True)

    def test_add_child(self):

        self.t1.add_child(self.t2)
        self.t1.add_child(self.t3)

        self.assertEquals(self.t1 in self.t2.parents, True)
        self.assertEquals(self.t1 in self.t3.parents, True)

        self.assertEquals(self.t2 in self.t1.children, True)
        self.assertEquals(self.t3 in self.t1.children, True)
