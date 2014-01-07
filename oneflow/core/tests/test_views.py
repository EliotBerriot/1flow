# -*- coding: utf-8 -*-
# pylint: disable=E1103,C0103

import logging

from django.test import TestCase  # TransactionTestCase
from django.test.utils import override_settings
from django.test.client import Client
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse, NoReverseMatch

from oneflow.core.models.nonrel import (Feed, Article, Read, User, Tag,
                                        WebSite, Author, HOME_STYLE_CHOICES,
                                        Subscription, Folder, Preferences)
from oneflow.base.utils import RedisStatsCounter
from oneflow.base.tests import (connect_mongodb_testsuite, TEST_REDIS)

#from unittest import skip

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


@override_settings(STATICFILES_STORAGE=
                   'pipeline.storage.NonPackagingPipelineStorage',
                   CELERY_EAGER_PROPAGATES_EXCEPTIONS=True,
                   CELERY_ALWAYS_EAGER=True,
                   BROKER_BACKEND='memory',)
class HomeAndPreferencesViewTest(TestCase):

    def setUp(self):
        self.client = Client()

        self.django_user = DjangoUser.objects.create_user(
            username='testuser', password='testpass',
            email='test-ocE3f6VQqFaaAZ@1flow.io')

        # MongoDB user has been auto created.
        self.mongodb_user = self.django_user.mongo

    def tearDown(self):
        User.drop_collection()
        self.client.logout()

    def test_home_works(self):

        response = self.client.get(reverse('home'), follow=True)

        self.assertEquals(response.context[u'mongodb_user'], None)

        login = self.client.login(username='testuser', password='testpass')

        self.assertTrue(login)

        response = self.client.get(reverse('home'), follow=True)

        self.assertEquals(response.context[u'mongodb_user'], self.mongodb_user)

        self.assertContains(response, u'Welcome to 1flow,')

    def test_profile_works(self):

        response = self.client.get(reverse('profile'), follow=True)

        self.assertEqual(response.status_code, 200)

        self.assertNotContains(response, u"Your profile")

        login = self.client.login(username='testuser', password='testpass')

        self.assertTrue(login)

        response = self.client.get(reverse('profile'), follow=True)

        self.assertContains(response, u"Your profile")

        self.assertContains(response, u"testuser")

    def test_set_preference(self):

        self.client.login(username='testuser', password='testpass')

        self.assertRaises(NoReverseMatch, reverse, 'set_preference', kwargs={
                          'base': 'blah',
                          })

        self.assertRaises(NoReverseMatch, reverse, 'set_preference', kwargs={
                          'base': 'blah',
                          'sub': 'test',
                          })

        self.assertRaises(NoReverseMatch, reverse, 'set_preference', kwargs={
                          'base': 'blah',
                          'sub': 'test',
                          'value': ''
                          })

        self.assertRaises(NoReverseMatch, reverse, 'set_preference', kwargs={
                          'base': 'blah',
                          'sub': 'test',
                          'value': '+1'
                          })

        # In fact, this preference name doesn't exist in database
        response = self.client.get(reverse('set_preference', kwargs={
                                   'base': 'blah',
                                   'sub': 'test',
                                   'value': '11'
                                   }), follow=True)

        self.assertEqual(response.status_code, 400)

        response = self.client.get(reverse('set_preference', kwargs={
                                   'base': 'home',
                                   'sub': 'style',
                                   'value': 'TEST'
                                   }), follow=True)

        self.assertEqual(response.status_code, 503)

        for code, style in HOME_STYLE_CHOICES:

            response = self.client.get(reverse('set_preference', kwargs={
                                       'base': 'home',
                                       'sub': 'style',
                                       'value': code
                                       }), follow=True)

            self.assertEqual(response.status_code, 200)

            self.mongodb_user.preferences.reload()

            self.assertEquals(self.mongodb_user.preferences.home.style, code)

    def test_read_works(self):

        login = self.client.login(username='testuser', password='testpass')
        self.assertTrue(login)

        response = self.client.get(reverse('read'), follow=True)

        self.assertEquals(response.context[u'mongodb_user'], self.mongodb_user)

        self.assertContains(response, u' articles')


@override_settings(STATICFILES_STORAGE=
                   'pipeline.storage.NonPackagingPipelineStorage',
                   CELERY_EAGER_PROPAGATES_EXCEPTIONS=True,
                   CELERY_ALWAYS_EAGER=True,
                   BROKER_BACKEND='memory',)
class SelectorViewTest(TestCase):

    @classmethod
    def setUpClass(cls):

        cls.feeds = []

        for feed_name, feed_url in ((u'My Cool Feed',
                                     u'http://blog.1flow.io/rss'), ):
                                    # (u'Another Feed',
                                    #  u'http://www.w3sh.com/feed/'),
                                    # (u'This Third Feed',
                                    #  u'http://feeds.feedburner.com/bashfr?format=xml')): # NOQA
            feed = Feed(name=feed_name, url=feed_url).save()
            cls.feeds.append(feed)

    def setUp(self):
        self.client = Client()

        # WARNING: it doesn't work as expected
        # when this user is created in setUpClass().
        self.django_user = DjangoUser.objects.create_user(
            username='testuser', password='testpass',
            email='test-ocE3f6VQqFaaAZ@1flow.io')

        # MongoDB user has been auto created.
        self.mongodb_user = self.django_user.mongo

        self.subscriptions = []
        self.folders       = []

        for feed in self.feeds:
            self.subscriptions.append(
                Subscription.subscribe_user_to_feed(self.mongodb_user, feed)
            )

        for folder_name in (u'Folder #1', u'Folder #2', u'Folder #3',
                            u'Folder #4', u'Folder #5', u'Folder #6'):
            self.folders.append(
                Folder.add_folder(folder_name, self.mongodb_user)
            )

    @classmethod
    def tearDownClass(cls):
        Article.drop_collection()
        Feed.drop_collection()

    def tearDown(self):
        self.client.logout()

        Subscription.drop_collection()
        Read.drop_collection()
        Folder.drop_collection()
        Preferences.drop_collection()
        User.drop_collection()

    def selector_lists_subscriptions_test(self):

        login = self.client.login(username='testuser', password='testpass')
        self.assertTrue(login)

        response = self.client.get(reverse('source_selector'), follow=True)

        #LOGGER.warning(response.context['mongodb_user'])
        #LOGGER.warning(self.mongodb_user.top_folders)
        #LOGGER.warning(self.mongodb_user.top_folders)
        #LOGGER.warning(response)

        for folder in self.folders:
            self.assertContains(response, folder.name)

        self.assertContains(response, u'Unclassified information streams')

        for subscription in self.subscriptions:
            self.assertContains(response, subscription.name)

    def nest_folders_tests(self):

        login = self.client.login(username='testuser', password='testpass')
        self.assertTrue(login)

        #LOGGER.warning(self.mongodb_user.get_folders_tree(for_parent=True))

        # Make Folder #2 a child of Folder #1, and rename it.
        response = self.client.post(
            reverse('edit_folder', kwargs={
                    'folder': str(self.folders[1].id)
                    }),
            {
                'parent': str(self.folders[0].id),
                'name': u'NEW NAME #2'
            }, follow=True
        )

        self.assertNotContains(response, u'Folder #2')
        self.assertContains(response, u'NEW NAME #2')

        for subscription in self.subscriptions:
            self.assertContains(response, subscription.name)

        for folder in self.folders:
            folder.reload()
            self.assertContains(response, folder.name)

        response = self.client.get(
            reverse('edit_folder', kwargs={
                    'folder': str(self.folders[1].id)
                    }),
            follow=True,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )

        # These 2 should be visible in the modal body,
        # and excluded from the <select> <option>'s.
        self.assertContains(response, self.folders[0].name)
        self.assertContains(response, self.folders[1].name)

        # Current parent is in the list, selected
        self.assertContains(response, self.folders[0].name + u'</option>')

        # Self-folder is not in the list to avoid cycles.
        self.assertNotContains(response, self.folders[1].name + u'</option>')

        # Others are here too.
        self.assertContains(response, self.folders[2].name + u'</option>')
        self.assertContains(response, self.folders[3].name + u'</option>')
        self.assertContains(response, self.folders[4].name + u'</option>')
        self.assertContains(response, self.folders[5].name + u'</option>')

        # Make Folder #3 a child of Folder #2
        # and rename it; Now #1, #2 #3 are a chain.
        response = self.client.post(
            reverse('edit_folder', kwargs={
                    'folder': str(self.folders[2].id)
                    }),
            {
                'parent': str(self.folders[1].id),
                'name': u'NEW NAME #3'
            }, follow=True
        )

        # Get back my new name from database.
        self.folders[2].reload()

        # Make Folder #4 a child of Folder #2
        # and rename it; Now #3 and #4 are sibling.
        response = self.client.post(
            reverse('edit_folder', kwargs={
                    'folder': str(self.folders[3].id)
                    }),
            {
                'parent': str(self.folders[1].id),
                'name': u'NEW NAME #4'
            }, follow=True
        )

        # Get back my new name from database.
        self.folders[3].reload()

        response = self.client.get(
            reverse('edit_folder', kwargs={
                    'folder': str(self.folders[2].id)
                    }),
            follow=True,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )

        self.assertContains(response, self.folders[1].name)
        self.assertContains(response, self.folders[2].name)

        # This one should not appear anywhere in the modal,
        # it's a sibling of the one being edited.
        self.assertNotContains(response, self.folders[3].name)

        # Current parent is in the list, selected
        self.assertContains(response, self.folders[0].name + u'</option>')
        self.assertContains(response, self.folders[1].name + u'</option>')

        # Self-folder and sibling are not in the list to avoid cycles.
        self.assertNotContains(response, self.folders[2].name + u'</option>')

        # Others are here too.
        self.assertContains(response, self.folders[4].name + u'</option>')
        self.assertContains(response, self.folders[5].name + u'</option>')

        # Folder #1 should not have any of direct
        # and indirect children settable as parent.
        response = self.client.get(
            reverse('edit_folder', kwargs={
                    'folder': str(self.folders[0].id)
                    }),
            follow=True,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )

        self.assertContains(response, self.folders[0].name)

        # Direct and indirect children should not appear
        # anywhere in the modal, to avoid cycles.
        self.assertNotContains(response, self.folders[1].name)
        self.assertNotContains(response, self.folders[2].name)
        self.assertNotContains(response, self.folders[3].name)

        # Remaining should be there, settable as parent.
        self.assertContains(response, self.folders[4].name + u'</option>')
        self.assertContains(response, self.folders[5].name + u'</option>')
