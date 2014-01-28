# -*- coding: utf-8 -*-
# pylint: disable=E1103,C0103
"""
    Copyright 2013-2014 Olivier Cortès <oc@1flow.io>

    This file is part of the 1flow project.

    1flow is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of
    the License, or (at your option) any later version.

    1flow is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public
    License along with 1flow.  If not, see http://www.gnu.org/licenses/

"""

import logging

from constance import config

from django.core import mail
from django.test import TestCase  # TransactionTestCase
from django.test.utils import override_settings
from django.contrib.auth import get_user_model

from oneflow.core.models import (Feed, Subscription, PseudoQuerySet,
                                 Article, Read, Folder, TreeCycleException,
                                 User, Group, Tag, WebSite, Author)
from oneflow.core.tasks import global_feeds_checker
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
Group.drop_collection()
Feed.drop_collection()
Tag.drop_collection()
Folder.drop_collection()
WebSite.drop_collection()
Author.drop_collection()


class ThrottleIntervalTest(TestCase):

    def test_lower_interval_with_etag_or_modified(self):

        t = Feed.throttle_fetch_interval

        some_news = 10
        no_dupe   = 0
        no_mutual = 0

        self.assertEquals(t(1000, some_news, no_mutual, no_dupe,
                          'etag', 'last_modified'), 540.0)
        self.assertEquals(t(1000, some_news, no_mutual, no_dupe,
                          '', 'last_modified'),  540.0)
        self.assertEquals(t(1000, some_news, no_mutual, no_dupe,
                          None, 'last_modified'), 540.0)

        self.assertEquals(t(1000, some_news, no_mutual, no_dupe, 'etag', ''),
                          540.0)
        self.assertEquals(t(1000, some_news, no_mutual, no_dupe, 'etag', None),
                          540.0)

    def test_lower_interval_with_etag_or_modified_and_mutualized(self):

        t = Feed.throttle_fetch_interval

        no_news   = 0
        no_dupe   = 0
        a_dupe    = 1
        a_mutual  = 1

        self.assertEquals(t(1000, no_news, a_mutual, no_dupe,
                          'etag', 'last_modified'), 800.0)
        self.assertEquals(t(1000, no_news, a_mutual, no_dupe,
                          '', 'last_modified'),  800.0)
        self.assertEquals(t(1000, no_news, a_mutual, no_dupe,
                          None, 'last_modified'), 800.0)

        self.assertEquals(t(1000, no_news, a_mutual, no_dupe, 'etag', ''),
                          800.0)
        self.assertEquals(t(1000, no_news, a_mutual, no_dupe, 'etag', None),
                          800.0)

        self.assertEquals(t(1000, no_news, a_mutual, a_dupe,
                          'etag', 'last_modified'), 900.0)
        self.assertEquals(t(1000, no_news, a_mutual, a_dupe,
                          '', 'last_modified'),  900.0)
        self.assertEquals(t(1000, no_news, a_mutual, a_dupe,
                          None, 'last_modified'), 900.0)

        self.assertEquals(t(1000, no_news, a_mutual, a_dupe, 'etag', ''),
                          900.0)
        self.assertEquals(t(1000, no_news, a_mutual, a_dupe, 'etag', None),
                          900.0)

    def test_raise_interval_with_etag_or_modified(self):

        t = Feed.throttle_fetch_interval

        some_news = 10
        no_news   = 0
        a_dupe    = 1
        no_mutual = 0

        # news, but a dupe > raise-

        self.assertEquals(t(1000, some_news, no_mutual, a_dupe,
                          'etag', 'last_modified'), 810.0)
        self.assertEquals(t(1000, some_news, no_mutual, a_dupe,
                          '', 'last_modified'), 810.0)
        self.assertEquals(t(1000, some_news, no_mutual, a_dupe,
                          None, 'last_modified'), 810.0)

        self.assertEquals(t(1000, some_news, no_mutual, a_dupe,
                          'etag', ''),   810.0)
        self.assertEquals(t(1000, some_news, no_mutual, a_dupe,
                          'etag', None), 810.0)

        # no news, a dupe > raise+

        self.assertEquals(t(1000, no_news, no_mutual, a_dupe,
                          'etag', 'last_modified'), 1250)
        self.assertEquals(t(1000, no_news, no_mutual, a_dupe,
                          '', 'last_modified'), 1250)
        self.assertEquals(t(1000, no_news, no_mutual, a_dupe,
                          None, 'last_modified'), 1250)

        self.assertEquals(t(1000, no_news, no_mutual, a_dupe,
                          'etag', ''),   1250)
        self.assertEquals(t(1000, no_news, no_mutual, a_dupe,
                          'etag', None), 1250)

    def test_lowering_interval_without_etag_nor_modified(self):

        t = Feed.throttle_fetch_interval

        some_news = 10
        no_dupe   = 0
        no_mutual = 0
        a_mutual  = 1

        # news, no dupes > raise+ (etag don't count)

        self.assertEquals(t(1000, some_news, no_mutual, no_dupe, '', ''),
                          540.0)
        self.assertEquals(t(1000, some_news, no_mutual, no_dupe, None, None),
                          540.0)

        self.assertEquals(t(1000, some_news, a_mutual, no_dupe, '', ''),
                          630.0)
        self.assertEquals(t(1000, some_news, a_mutual, no_dupe, None, None),
                          630.0)

    def test_raising_interval_without_etag_nor_modified(self):

        t = Feed.throttle_fetch_interval

        some_news = 10
        no_news   = 0
        a_dupe    = 1
        no_dupe   = 0
        no_mutual = 0
        a_mutual  = 1

        self.assertEquals(t(1000, some_news, no_mutual, no_dupe, '', ''),
                          540.0)
        self.assertEquals(t(1000, some_news, no_mutual, no_dupe,
                          None, None), 540.0)

        self.assertEquals(t(1000, some_news, a_mutual, no_dupe, '', ''),
                          630.0)
        self.assertEquals(t(1000, some_news, a_mutual, no_dupe,
                          None, None), 630.0)

        self.assertEquals(t(1000, some_news, no_mutual, a_dupe, '', ''),
                          810.0)
        self.assertEquals(t(1000, some_news, no_mutual, a_dupe,
                          None, None), 810.0)

        self.assertEquals(t(1000, some_news, a_mutual, a_dupe, '', ''),
                          720.0000000000001)
        self.assertEquals(t(1000, some_news, a_mutual, a_dupe,
                          None, None), 720.0000000000001)

        self.assertEquals(t(1000, no_news, no_mutual, no_dupe,
                          '', ''), 1000.0)
        self.assertEquals(t(1000, no_news, no_mutual, no_dupe,
                          None, None), 1000.0)

        self.assertEquals(t(1000, no_news, a_mutual, no_dupe,
                          '', ''), 800.0)
        self.assertEquals(t(1000, no_news, a_mutual, no_dupe,
                          None, None), 800.0)

        self.assertEquals(t(1000, no_news, a_mutual, a_dupe, '', ''), 900.0)
        self.assertEquals(t(1000, no_news, a_mutual, a_dupe, None, None), 900.0)

        self.assertEquals(t(1000, no_news, no_mutual, a_dupe, '', ''), 1125)
        self.assertEquals(t(1000, no_news, no_mutual, a_dupe, None, None), 1125)

    def test_less_news(self):

        t = Feed.throttle_fetch_interval

        more_news = config.FEED_FETCH_RAISE_THRESHOLD + 5
        less_news = config.FEED_FETCH_RAISE_THRESHOLD - 5
        just_one  = 1

        a_dupe  = 1
        no_dupe = 0
        no_mutual = 0

        self.assertEquals(t(1000, just_one, no_mutual, a_dupe,
                          'etag', ''), 900.0)
        self.assertEquals(t(1000, less_news, no_mutual, a_dupe,
                          'etag', None), 900.0)
        self.assertEquals(t(1000, more_news, no_mutual, a_dupe,
                          'etag', None), 810.0)

        self.assertEquals(t(1000, just_one, no_mutual, no_dupe,
                          'etag', ''), 600.0)
        self.assertEquals(t(1000, less_news, no_mutual, no_dupe,
                          'etag', None), 600.0)
        self.assertEquals(t(1000, more_news, no_mutual, no_dupe,
                          'etag', None), 540.0)

    def test_limits(self):

        t = Feed.throttle_fetch_interval

        some_news = 10
        no_news   = 0
        a_dupe    = 1
        no_dupe   = 0
        no_mutual = 0

        # new articles already at max stay at max.
        self.assertEquals(t(config.FEED_FETCH_MAX_INTERVAL, no_news,
                          no_mutual, a_dupe, '', ''),
                          config.FEED_FETCH_MAX_INTERVAL)
        self.assertEquals(t(config.FEED_FETCH_MAX_INTERVAL, no_news,
                          no_mutual, a_dupe, 'etag', ''),
                          config.FEED_FETCH_MAX_INTERVAL)
        self.assertEquals(t(config.FEED_FETCH_MAX_INTERVAL, no_news,
                          no_mutual, a_dupe, None, 'last_mod'),
                          config.FEED_FETCH_MAX_INTERVAL)

        # dupes at min stays at min
        self.assertEquals(t(config.FEED_FETCH_MIN_INTERVAL, some_news,
                          no_mutual, no_dupe, '', ''),
                          config.FEED_FETCH_MIN_INTERVAL)
        self.assertEquals(t(config.FEED_FETCH_MIN_INTERVAL, some_news,
                          no_mutual, no_dupe, 'etag', None),
                          config.FEED_FETCH_MIN_INTERVAL)
        self.assertEquals(t(config.FEED_FETCH_MIN_INTERVAL, some_news,
                          no_mutual, no_dupe, '', 'last_mod'),
                          config.FEED_FETCH_MIN_INTERVAL)


class PseudoQuerySetTest(TestCase):

    def test_append(self):

        q1 = PseudoQuerySet()
        q1.append(1)
        q1.append(2)
        q1.append(3)

        self.assertTrue(len(q1) == 3)
        self.assertTrue(1 in q1)
        self.assertTrue(2 in q1)
        self.assertTrue(3 in q1)

    def test_extend(self):

        q1 = PseudoQuerySet()
        q1.append(1)
        q1.append(2)
        q1.append(3)

        q2 = PseudoQuerySet()
        q2.append(4)
        q2.append(5)
        q2.append(6)

        #LOGGER.warning(q1)

        q1.extend(q2)

        #LOGGER.warning(q1)

        self.assertTrue(len(q1) == 6)
        self.assertTrue(4 in q1)
        self.assertTrue(5 in q1)
        self.assertTrue(6 in q1)

    def test_append_extend(self):

        q1 = PseudoQuerySet()
        q1.append(1)
        q1.append(2)

        q2 = PseudoQuerySet()
        q2.append(4)
        q2.append(5)

        q3 = PseudoQuerySet()
        q3.append(7)
        q3.append(8)
        #LOGGER.warning(q1)

        q1.append(3)
        q1.extend(q2)
        q1.append(6)
        q1.extend(q3)
        q1.append(9)

        #LOGGER.warning(q1)

        self.assertTrue(len(q1) == 9)
        self.assertTrue(4 in q1)
        self.assertTrue(6 in q1)
        self.assertTrue(8 in q1)


@override_settings(STATICFILES_STORAGE=
                   'pipeline.storage.NonPackagingPipelineStorage',
                   CELERY_EAGER_PROPAGATES_EXCEPTIONS=True,
                   CELERY_ALWAYS_EAGER=True,
                   BROKER_BACKEND='memory',)
class FeedsTest(TestCase):

    def setUp(self):

        # NOTE: we need real web pages, else the absolutization won't work or
        # will find duplicates and tests will fail for a real-life reason.
        self.article1 = Article(title='test1',
                                url='http://blog.1flow.io/post/'
                                '59410536612/1flow-blog-has-moved').save()

        self.feed = Feed(name='1flow test feed',
                         url='http://blog.1flow.io/rss').save()

        self.article1.update(add_to_set__feeds=self.feed)
        self.article1.reload()

        # User & Reads creation
        for index in xrange(1, 2):
            username = 'test_user_%s' % index
            du = DjangoUser.objects.create(username=username,
                                           email='%s@test.1flow.io' % username)
            # PG post_save() signal already created the MongoDB user.
            u = du.mongo
            Read(user=u, article=self.article1).save()
            Subscription(user=u, feed=self.feed).save()

        for index in xrange(2, 5):
            username = 'test_user_%s' % index
            du = DjangoUser.objects.create(username=username,
                                           email='%s@test.1flow.io' % username)

    def tearDown(self):
        Subscription.drop_collection()
        Feed.drop_collection()
        Read.drop_collection()
        Article.drop_collection()
        User.drop_collection()

    def test_close(self):

        closed_reason = u'closed for tests'

        self.feed.close(closed_reason)

        self.assertTrue(self.feed.closed)
        self.assertEquals(self.feed.closed_reason, closed_reason)
        self.assertFalse(self.feed.date_closed is None)

        global_feeds_checker()

        self.assertEquals(len(mail.outbox), 1)
        self.assertTrue(u'Reminder: 1 feed(s) closed in last'
                        in mail.outbox[0].subject)
        self.assertTrue(unicode(self.feed) in mail.outbox[0].body)

        #self.assertEqual( mail.outbox[0].to, [ "test@foo.bar" ] )
        #self.assertTrue( "test@foo.bar" in mail.outbox[0].to )

    def test_feeds_creation(self):

        # .setUp() creates one already.
        self.assertEquals(Feed._get_collection().count(), 1)

        feed, created = Feed.create_feeds_from_url(u'http://ntoll.org/')[0]
        self.assertTrue(created)
        self.assertEquals(feed.url, u'http://ntoll.org/rss.xml')
        self.assertEquals(Feed._get_collection().count(), 2)

        # Via the Home Page
        feed, created = Feed.create_feeds_from_url(u'http://www.zdnet.fr/')[0]
        self.assertTrue(created)
        self.assertEquals(feed.url, u'http://www.zdnet.fr/feeds/rss/')
        self.assertEquals(Feed._get_collection().count(), 3)

        # Via the RSS listing page
        feed, created = Feed.create_feeds_from_url(u'http://www.zdnet.fr/services/rss/')[0] # NOQA
        self.assertFalse(created)
        self.assertEquals(feed.url, u'http://www.zdnet.fr/feeds/rss/')
        self.assertEquals(Feed._get_collection().count(), 3)

        # Via the first RSS (raw)
        feed, created = Feed.create_feeds_from_url(u'http://www.zdnet.fr/feeds/rss/')[0] # NOQA
        self.assertFalse(created)
        self.assertEquals(feed.url, u'http://www.zdnet.fr/feeds/rss/')
        self.assertEquals(Feed._get_collection().count(), 3)

        feed, created = Feed.create_feeds_from_url(u'http://www.atlantico.fr/')[0] # NOQA
        self.assertTrue(created)
        self.assertEquals(feed.url, u'http://www.atlantico.fr/rss.xml')
        self.assertEquals(Feed._get_collection().count(), 4)

        feed, created = Feed.create_feeds_from_url(u'http://wordpress.org/')[0]
        self.assertTrue(created)
        self.assertEquals(feed.url, u'http://wordpress.org/news/feed/')
        self.assertEquals(Feed._get_collection().count(), 5)

        # Not created again, even from an article which has the comment feed.
        feed, created = Feed.create_feeds_from_url(u'http://ntoll.org/article/build-a-drogulus')[0] # NOQA
        self.assertFalse(created)
        self.assertEquals(feed.url, u'http://ntoll.org/rss.xml')
        self.assertEquals(Feed._get_collection().count(), 5)

        # This one has been created in .setUp()
        feed, created = Feed.create_feeds_from_url(u'http://blog.1flow.io/')[0]
        self.assertFalse(created)
        self.assertEquals(feed.url, u'http://blog.1flow.io/rss')
        self.assertEquals(Feed._get_collection().count(), 5)

        # No RSS in main page
        self.assertRaises(Exception, Feed.create_feeds_from_url,
                          u'http://www.bbc.co.uk/')
        self.assertEquals(Feed._get_collection().count(), 5)

        # This one has no RSS anywhere, it won't create anything
        self.assertRaises(Exception, Feed.create_feeds_from_url,
                          u'http://www.tumblr.com/blog/1flowio')
        self.assertEquals(Feed._get_collection().count(), 5)


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
                                url='http://blog.1flow.io/post/'
                                '59410536612/1flow-blog-has-moved').save()
        self.article2 = Article(title='test2',
                                url='http://obi.1flow.io/fr/').save()
        self.article3 = Article(title='test3',
                                url='http://obi.1flow.io/en/').save()

        # User & Reads creation
        for index in xrange(1, 6):
            username = 'test_user_%s' % index
            du = DjangoUser.objects.create(username=username,
                                           email='%s@test.1flow.io' % username)
            # NOTE: the mongoDB user is created automatically. If you
            # try to create one it will fail with duplicate index error.
            u = du.mongo
            Read(user=u, article=self.article1).save()

        for index in xrange(6, 11):
            username = 'test_user_%s' % index
            du = DjangoUser.objects.create(username=username,
                                           email='%s@test.1flow.io' % username)
            u = du.mongo
            Read(user=u, article=self.article2).save()

        # Feeds creation
        for index in xrange(1, 6):
            f = Feed(name='test feed #%s' % index,
                     url='http://test-feed%s.com' % index).save()
            self.article1.update(add_to_set__feeds=f)

            self.article1.reload()

        for index in xrange(6, 11):
            f = Feed(name='test feed #%s' % index,
                     url='http://test-feed%s.com' % index).save()
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

        # Auto-created on PG's post_save().
        self.mongodb_user = self.django_user.mongo

    def tearDown(self):
        User.drop_collection()

    def test_user_property(self):

        self.assertEquals(self.django_user.mongo, self.mongodb_user)

    def test_user_preferences(self):

        # We just want to be sure preferences are created when a new
        # user is, and all the embedded documents are created too.
        self.assertEquals(self.django_user.mongo.preferences.home.style, u'RL')


@override_settings(STATICFILES_STORAGE=
                   'pipeline.storage.NonPackagingPipelineStorage',
                   CELERY_EAGER_PROPAGATES_EXCEPTIONS=True,
                   CELERY_ALWAYS_EAGER=True,
                   BROKER_BACKEND='memory',)
class FoldersTest(TestCase):
    def setUp(self):

        self.django_user = DjangoUser.objects.create_user(
            username='testuser', password='testpass',
            email='test-ocE3f6VQqFaaAZ@1flow.io')

        # Auto-created on PG's post_save().
        self.mongodb_user = self.django_user.mongo

    def tearDown(self):
        User.drop_collection()
        Folder.drop_collection()

    def test_properties(self):

        user = self.mongodb_user

        self.assertEquals(len(user.folders), 0)

        # Be sure 2 calls to `Folder.get_root_for` don't create 2 folders.
        # The second call must return the

        root = Folder.get_root_for(user)

        # The root folder is kind of hidden and is not counted in folders.
        self.assertEquals(len(user.folders), 0)
        self.assertEquals(len(user.folders_tree), 0)

        self.assertEquals(root, user.root_folder)

    def test_parent_children_root(self):

        user = self.mongodb_user
        root = user.root_folder

        self.assertEquals(len(user.folders), 0)

        ftest1 = Folder.add_folder('test1', user)

        self.assertEquals(len(user.folders), 1)

        ftest2 = Folder.add_folder('test2', user)
        ftest3 = Folder.add_folder('test3', user)

        #We didn't pass "root" as argument. `Folder` class
        # updated the DB, but not our local instance.
        root.reload()

        self.assertEquals(len(root.children), 3)

        for folder in (ftest1, ftest2, ftest3):
            self.assertTrue(folder in root.children)
            self.assertTrue(folder.parent == root)

        self.assertEquals(len(user.folders), 3)

    def test_parent_children_multiple(self):

        user = self.mongodb_user
        root = user.root_folder

        ftest1 = Folder.add_folder('test1', user)

        self.assertEquals(len(user.folders), 1)

        ftest2 = Folder.add_folder('test2', user, ftest1)
        ftest3 = Folder.add_folder('test3', user, ftest1)

        # We didn't pass "root" as argument. `Folder` class
        # updated the DB, but not our local instance. This
        # will implicitely reload a full folder hierarchy
        # from the database.
        root.reload()

        self.assertEquals(len(root.children), 1)
        self.assertEquals(len(ftest1.children), 2)
        self.assertEquals(len(ftest2.children), 0)
        self.assertEquals(len(ftest3.children), 0)

        for folder in (ftest2, ftest3):
            self.assertFalse(folder in root.children)
            self.assertTrue(folder in root.children_tree)

            self.assertTrue(folder in ftest1.children)
            self.assertTrue(folder in ftest1.children_tree)
            self.assertTrue(folder.parent == ftest1)

            self.assertFalse(ftest1 in folder.children)
            self.assertFalse(root   in folder.children)
            self.assertFalse(ftest1 in folder.children_tree)
            self.assertFalse(root   in folder.children_tree)

        self.assertEquals(len(user.folders), 3)

        for folder in (ftest1, ftest2, ftest3):
            self.assertTrue(folder in user.folders)
            self.assertTrue(folder in user.folders_tree)
            self.assertTrue(folder in root.children_tree)

        # Move the folder in the hierarchy.
        ftest3.set_parent(ftest2)

        # HEADS UP: we need to reload ftest1 because
        # id(ftest2) != id(ftest1.children[0]) for some
        # obscure reason. This will implicitely reload
        # a full folder hierarchy from the database.
        ftest1.reload()

        # These are not necessary.
        #ftest2.reload()
        #ftest3.reload()

        self.assertEquals(len(root.children), 1)
        self.assertEquals(len(ftest1.children), 1)
        self.assertEquals(len(ftest2.children), 1)
        self.assertEquals(len(ftest3.children), 0)

        self.assertTrue(ftest3 in ftest2.children)
        self.assertFalse(ftest3 in ftest1.children)

        # HEADS UP: the result of this test depends on a user preference.
        self.assertFalse(ftest3 in user.folders_tree)

        user.preferences.selector.extended_folders_depth = True
        user.preferences.save()

        self.assertTrue(ftest3 in user.folders_tree)

        self.assertTrue(ftest3 in ftest2.children_tree)
        self.assertTrue(ftest3 in ftest1.children_tree)
        self.assertTrue(ftest3 in root.children_tree)

    def test_parent_chain_checking(self):

        user = self.mongodb_user
        root = user.root_folder

        ftest1 = Folder.add_folder('test1', user)
        ftest2 = Folder.add_folder('test2', user, ftest1)
        ftest3 = Folder.add_folder('test3', user, ftest2)

        # root
        self.assertTrue(root.is_parent_of(ftest1))
        self.assertTrue(root.is_parent_of(ftest2))
        self.assertTrue(root.is_parent_of(ftest3))

        self.assertFalse(root.is_parent_of(root))

        # ftest1
        self.assertTrue(ftest1.is_parent_of(ftest2))
        self.assertTrue(ftest1.is_parent_of(ftest3))

        self.assertFalse(ftest1.is_parent_of(ftest1))
        self.assertFalse(ftest1.is_parent_of(root))

        # ftest2
        self.assertTrue(ftest2.is_parent_of(ftest3))

        self.assertFalse(ftest2.is_parent_of(ftest2))
        self.assertFalse(ftest2.is_parent_of(ftest1))
        self.assertFalse(ftest2.is_parent_of(root))

        # ftest3
        self.assertFalse(ftest3.is_parent_of(ftest3))
        self.assertFalse(ftest3.is_parent_of(ftest2))
        self.assertFalse(ftest3.is_parent_of(ftest1))
        self.assertFalse(ftest3.is_parent_of(root))

    def test_avoid_cycles(self):

        user = self.mongodb_user
        root = user.root_folder

        ftest1 = Folder.add_folder('test1', user)
        ftest2 = Folder.add_folder('test2', user, ftest1)
        ftest3 = Folder.add_folder('test3', user, ftest2)

        self.assertTrue(ftest1.is_parent_of(ftest2))
        self.assertTrue(ftest1.is_parent_of(ftest3))

        self.assertFalse(ftest1.is_parent_of(ftest1))
        self.assertFalse(ftest1.is_parent_of(root))

        self.assertRaises(RuntimeError, ftest1.set_parent, ftest1)

        self.assertFalse(ftest1 in ftest1.children_tree)
        self.assertFalse(ftest1 in ftest2.children_tree)
        self.assertFalse(ftest1 in ftest3.children_tree)

        self.assertFalse(ftest2 in ftest2.children_tree)
        self.assertFalse(ftest2 in ftest3.children_tree)

        self.assertFalse(ftest3 in ftest3.children_tree)

        self.assertRaises(RuntimeError, ftest2.add_child, ftest2)

        self.assertRaises(TreeCycleException, ftest1.set_parent, ftest2)
        self.assertRaises(TreeCycleException, ftest1.set_parent, ftest3)
        self.assertRaises(TreeCycleException, ftest2.add_child,  ftest1)
        self.assertRaises(TreeCycleException, ftest3.add_child,  ftest1)
        self.assertRaises(TreeCycleException, ftest3.add_child,  ftest2)


@override_settings(STATICFILES_STORAGE=
                   'pipeline.storage.NonPackagingPipelineStorage',
                   CELERY_EAGER_PROPAGATES_EXCEPTIONS=True,
                   CELERY_ALWAYS_EAGER=True,
                   BROKER_BACKEND='memory',)
class GroupsTest(TestCase):
    def setUp(self):

        self.django_user1 = DjangoUser.objects.create_user(
            username='testuser1', password='testpass',
            email='test-ocE3f6VQqFaaAZ@1flow.io')

        self.django_user2 = DjangoUser.objects.create_user(
            username='testuser2', password='testpass',
            email='test-ocE3f6VQqFaaBZ@1flow.io')

        self.django_user3 = DjangoUser.objects.create_user(
            username='testuser3', password='testpass',
            email='test-ocE3f6VQqFaaCZ@1flow.io')

        # Auto-created on PG's post_save().
        self.alice = self.django_user1.mongo
        self.bob   = self.django_user2.mongo
        self.john  = self.django_user3.mongo

        self.alice_friends = Group(name="Alice's friends",
                                   creator=self.alice).save()
        self.alice_work = Group(name="Alice's co-workers",
                                   creator=self.alice).save()
        self.bob_friends   = Group(name="Bob's friends",
                                   creator=self.bob).save()
        self.john_friends  = Group(name="John's friends",
                                   creator=self.john).save()

    def tearDown(self):
        User.drop_collection()
        Group.drop_collection()

    def system_groups_are_always_here(self):

        self.assertEquals(self.alice.all_relations_group.__class__, Group)
        self.assertEquals(self.bob.all_relations_group.__class__, Group)
        self.assertEquals(self.john.all_relations_group.__class__, Group)

        self.assertEquals(self.alice.in_relations_of_group.__class__, Group)
        self.assertEquals(self.bob.in_relations_of_group.__class__, Group)
        self.assertEquals(self.john.in_relations_of_group.__class__, Group)

        self.assertEquals(self.alice.blocked_group.__class__, Group)
        self.assertEquals(self.bob.blocked_group.__class__, Group)
        self.assertEquals(self.john.blocked_group.__class__, Group)

    def basic_inter_relationships(self):

        alice         = self.alice
        bob           = self.bob
        alice_friends = self.alice_friends
        bob_friends   = self.bob_friends
        assertTrue    = self.assertTrue
        assertFalse   = self.assertFalse

        alice_friends.add_member(bob)

        assertTrue(bob in alice_friends)

        assertTrue(bob in alice.all_relations_group)
        assertFalse(bob in alice.in_relations_of_group)

        assertTrue(alice in bob.in_relations_of_group)
        assertFalse(alice in bob.all_relations_group)

        bob_friends.add_member(alice)

        assertTrue(alice in bob_friends)

        assertTrue(alice in bob.all_relations_group)     # Alice is "promoted"
        assertFalse(alice in bob.in_relations_of_group)  # (idem)

        assertTrue(bob in alice.all_relations_group)     # Bob doesn't move.
        assertFalse(bob in alice.in_relations_of_group)  # (idem)

    def unidirectional_relation_deletion(self):

        bob           = self.bob
        john          = self.john
        bob_friends   = self.bob_friends
        assertTrue    = self.assertTrue
        assertFalse   = self.assertFalse

        bob_friends.add_member(john)

        assertTrue(john in bob_friends)

        assertTrue(john in bob.all_relations_group)
        assertFalse(john in bob.in_relations_of_group)

        assertFalse(bob in john.all_relations_group)
        assertTrue(bob in john.in_relations_of_group)

        bob_friends.delete_member(john)

        assertFalse(john in bob_friends)

        assertFalse(john in bob.all_relations_group)
        assertFalse(john in bob.in_relations_of_group)

        assertFalse(bob in john.all_relations_group)
        assertFalse(bob in john.in_relations_of_group)

    def bidirectional_relation_deletion(self):

        bob           = self.bob
        john          = self.john
        bob_friends   = self.bob_friends
        john_friends  = self.john_friends
        assertTrue    = self.assertTrue
        assertFalse   = self.assertFalse

        bob_friends.add_member(john)

        assertTrue(john in bob_friends)

        assertTrue(john in bob.all_relations_group)
        assertFalse(john in bob.in_relations_of_group)

        assertFalse(bob in john.all_relations_group)
        assertTrue(bob in john.in_relations_of_group)

        john_friends.add_member(bob)

        assertTrue(bob in john_friends)

        assertTrue(bob in john.all_relations_group)
        assertFalse(bob in john.in_relations_of_group)

        assertTrue(bob in john.all_relations_group)    # Bob is "promoted"
        assertFalse(bob in john.in_relations_of_group)

        bob_friends.delete_member(john)

        assertFalse(john in bob_friends)

        assertFalse(john in bob.all_relations_group)
        assertTrue(john in bob.in_relations_of_group)   # The unidir-rel remains.

        assertTrue(bob in john.all_relations_group)     # (idem)
        assertFalse(bob in john.in_relations_of_group)

        john_friends.delete_member(bob)

        assertFalse(bob in john_friends)

        assertFalse(bob in john.all_relations_group)   # No trace left
        assertFalse(bob in john.in_relations_of_group)

        assertFalse(bob in john.all_relations_group)   # (idem)
        assertFalse(bob in john.in_relations_of_group)

    def multi_groups_relationships(self):

        alice = self.alice
        bob   = self.bob
        john  = self.john

        alice_friends = self.alice_friends
        alice_work    = self.alice_work
        bob_friends   = self.bob_friends
        john_friends  = self.john_friends

        assertTrue  = self.assertTrue
        assertFalse = self.assertFalse




    def blocking_consequences_in_groups(self):


        pass
