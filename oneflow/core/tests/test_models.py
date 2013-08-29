# -*- coding: utf-8 -*-
# pylint: disable=E1103,C0103

import logging

from constance import config

from django.test import TestCase  # TransactionTestCase
from django.test.utils import override_settings
from django.contrib.auth import get_user_model

from oneflow.core.models import Feed, Article, Read, User, Tag, WebSite, Author
from oneflow.base.utils import RedisStatsCounter
from oneflow.base.tests import (connect_mongodb_testsuite, TEST_REDIS)

DjangoUser = get_user_model()
LOGGER     = logging.getLogger(__file__)

# Use the test database not to pollute the production/development one.
RedisStatsCounter.REDIS = TEST_REDIS

TEST_REDIS.flushdb()

connect_mongodb_testsuite()

# Empty the database before starting in case an old test failed to tearDown().
Article.drop_collection()
Read.drop_collection()
User.drop_collection()
Feed.drop_collection()
Tag.drop_collection()
WebSite.drop_collection()
Author.drop_collection()


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


@override_settings(STATICFILES_STORAGE=
                   'pipeline.storage.NonPackagingPipelineStorage',
                   CELERY_EAGER_PROPAGATES_EXCEPTIONS=True,
                   CELERY_ALWAYS_EAGER=True,
                   BROKER_BACKEND='memory',)
class ArticleDuplicateTest(TestCase):

    def setUp(self):

        # NOTE: we need real web pages, else the absolutization won't work or
        # will find duplicates and tests will fail for a real-life reason.
        self.article1 = Article(title='test1',
                                url='http://blog.1flow.io/post/59410536612/1flow-blog-has-moved').save() # NOQA
        self.article2 = Article(title='test2',
                                url='http://obi.1flow.io/fr/').save()
        self.article3 = Article(title='test3',
                                url='http://obi.1flow.io/en/').save()

        # User & Reads creation
        for u in xrange(1, 6):
            u = User(django_user=u, username='test_user_%s' % u).save()
            Read(user=u, article=self.article1).save()

        for u in xrange(6, 11):
            u = User(django_user=u, username='test_user_%s' % u).save()
            Read(user=u, article=self.article2).save()

        # Feeds creation
        for f in xrange(1, 6):
            f = Feed(name='test feed #%s' % f,
                     url='http://test-feed%s.com' % f).save()
            self.article1.update(add_to_set__feeds=f)

            self.article1.reload()

        for f in xrange(6, 11):
            f = Feed(name='test feed #%s' % f,
                     url='http://test-feed%s.com' % f).save()
            self.article2.update(add_to_set__feeds=f)

            self.article2.reload()

    def tearDown(self):
        Article.drop_collection()
        User.drop_collection()
        Read.drop_collection()
        Feed.drop_collection()

    def test_register_duplicate_bare(self):

        self.assertEquals(Article.objects(
                          duplicate_of__exists=False).count(), 3)

        self.article1.register_duplicate(self.article2)

        # needed because feeds are modified in another instance of the
        # same dabase record, via the celery task.
        self.article1.safe_reload()

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
        self.article1.safe_reload()

        self.assertEquals(self.article2.duplicate_of, self.article1)

        #
        # TODO: finish this test case.
        #


@override_settings(STATICFILES_STORAGE=
                   'pipeline.storage.NonPackagingPipelineStorage',
                   CELERY_EAGER_PROPAGATES_EXCEPTIONS=True,
                   CELERY_ALWAYS_EAGER=True,
                   BROKER_BACKEND='memory',)
class AbsolutizeTest(TestCase):

    def setUp(self):

        #Article.drop_collection()
        #Feed.drop_collection()

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

    def tearDown(self):
        Article.drop_collection()
        Feed.drop_collection()

    def test_absolutize(self):
        self.article1.absolutize_url()
        self.assertEquals(self.article1.url, u'http://www.reseaux-telecoms.net/actualites/lire-lancement-mondial-du-samsung-galaxy-s4-25980.html') # NOQA
        self.assertEquals(self.article1.url_absolute, True)
        self.assertEquals(self.article1.url_error, '')

        self.article2.absolutize_url()
        self.assertEquals(self.article2.url, u'http://techcrunch.com/2013/05/18/hell-no-tumblr-users-wont-go-to-yahoo/') # NOQA
        self.assertEquals(self.article2.url_absolute, True)
        self.assertEquals(self.article2.url_error, '')

    def test_absolutize_errors(self):

        #
        # NOTE: if a PROXY is set, the reasons word cases can vary.
        # eg. 'Not Found' (via Squid) instead of 'NOT FOUND' (direct answer).
        #

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


@override_settings(STATICFILES_STORAGE=
                   'pipeline.storage.NonPackagingPipelineStorage',
                   CELERY_EAGER_PROPAGATES_EXCEPTIONS=True,
                   CELERY_ALWAYS_EAGER=True,
                   BROKER_BACKEND='memory',)
class TagsTest(TestCase):

    def setUp(self):

        self.t1 = Tag(name='test1').save()
        self.t2 = Tag(name='test2').save()
        self.t3 = Tag(name='test3').save()

    def tearDown(self):
        Tag.drop_collection()

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


@override_settings(STATICFILES_STORAGE=
                   'pipeline.storage.NonPackagingPipelineStorage',
                   CELERY_EAGER_PROPAGATES_EXCEPTIONS=True,
                   CELERY_ALWAYS_EAGER=True,
                   BROKER_BACKEND='memory',)
class WebSitesTest(TestCase):
    def setUp(self):

        WebSite.drop_collection()
        Article.drop_collection()

        self.ws1 = WebSite(url='http://test1.com').save()
        self.ws2 = WebSite(url='http://test2.com').save()

    def tearDown(self):
        WebSite.drop_collection()
        Article.drop_collection()

    def test_get_or_create_website(self):

        wt1, created = WebSite.get_or_create_website('http://test1.com')

        self.assertFalse(created)
        self.assertEquals(wt1, self.ws1)

        wt3, created = WebSite.get_or_create_website('http://test3.com')

        self.assertTrue(created)
        self.assertNotEquals(wt3, self.ws1)
        self.assertNotEquals(wt3, self.ws2)

        wt4, created = WebSite.get_or_create_website('http://test3.com')

        self.assertFalse(created)
        self.assertEquals(wt3, wt4)

        wt5, created = WebSite.get_or_create_website('http://test3.com/')

        self.assertTrue(created)
        self.assertNotEquals(wt5, wt4)

    def test_get_from_url(self):

        wt1 = WebSite.get_from_url('http://test1.com/example-article')
        wt2 = WebSite.get_from_url('http://test1.com/example-article2')

        self.assertEquals(wt1, self.ws1)
        self.assertEquals(wt1, self.ws1)
        self.assertEquals(wt1, wt2)

    def test_register_duplicate_not_again(self):

        wt1, created = WebSite.get_or_create_website('http://other.test1.com')

        self.ws1.register_duplicate(wt1)

        self.assertTrue(created)
        self.assertEquals(wt1.duplicate_of, self.ws1)

        wt2, created = WebSite.get_or_create_website('http://other.test1.com')

        self.assertFalse(created)
        self.assertNotEquals(wt2, wt1)
        self.assertEquals(wt2, self.ws1)

        # should fail.
        #self.ws2.register_duplicate(wt1)

        #
        # TODO: finish this test case.
        #

    def test_websites_duplicates(self):
        pass


@override_settings(STATICFILES_STORAGE=
                   'pipeline.storage.NonPackagingPipelineStorage',
                   CELERY_EAGER_PROPAGATES_EXCEPTIONS=True,
                   CELERY_ALWAYS_EAGER=True,
                   BROKER_BACKEND='memory',)
class AuthorsTest(TestCase):
    pass


@override_settings(STATICFILES_STORAGE=
                   'pipeline.storage.NonPackagingPipelineStorage',
                   CELERY_EAGER_PROPAGATES_EXCEPTIONS=True,
                   CELERY_ALWAYS_EAGER=True,
                   BROKER_BACKEND='memory',)
class UsersTest(TestCase):
    def setUp(self):

        self.django_user = DjangoUser.objects.create_user(
            username='testuser', password='testpass',
            email='test-ocE3f6VQqFaaAZ@1flow.io')

        self.mongodb_user = User(django_user=self.django_user.id,
                                 username='test_user').save()

    def tearDown(self):
        User.drop_collection()

    def test_user_property(self):

        self.assertEquals(self.django_user.mongo, self.mongodb_user)

    def test_user_preferences(self):

        # We just want to be sure preferences are created when a new
        # user is, and all the embedded documents are created too.
        self.assertEquals(self.django_user.mongo.preferences.home.style, None)
