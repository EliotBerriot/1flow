# -*- coding: utf-8 -*-
# pylint: disable=E1103,C0103

import logging

from django.test import TestCase  # TransactionTestCase
from django.test.utils import override_settings
from django.test.client import Client
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse, NoReverseMatch

from oneflow.core.models.nonrel import (Feed, Article, Read, User, Tag,
                                        WebSite, Author, HOME_STYLE_CHOICES)
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

        self.mongodb_user = User(django_user=self.django_user.id,
                                 username='test_user').save()

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
