# -*- coding: utf-8 -*-
# pylint: disable=E1103,C0103

import time
import logging

from django.test import TestCase
from django.test import TransactionTestCase
from django.test.client import Client
from django.test.utils import override_settings
from django.core.urlresolvers import reverse

#from ..base.utils import send_email_with_db_content

LOGGER = logging.getLogger(__file__)


#http://stackoverflow.com/questions/12816941/unit-testing-with-django-pipeline
@override_settings(STATICFILES_STORAGE=
                   'pipeline.storage.NonPackagingPipelineStorage',
                   #CELERY_EAGER_PROPAGATES_EXCEPTIONS=True,
                   #CELERY_ALWAYS_EAGER=True,
                   BROKER_BACKEND='memory',)
class LandingTests(TestCase):

    fixtures = ['base_2013-05-14_final-before-beta-opening',
                'landing_2013-05-14_final-before-beta-opening']

    def setUp(self):
        self.client = Client()
        self.http_headers = {
            "HTTP_ACCEPT_LANGUAGE": "fr-FR,fr;q=0.8,en-US;q=0.5,en;q=0.3",
            "HTTP_USER_AGENT": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.8; "
            "rv:21.0) Gecko/20100101 Firefox/21.0"}
        self.test_email = 'test-ocE3f6VQqFaaAZ@1flow.io'

    def test_no_empty_mail(self):
        """ """

        response = self.client.post(
            reverse('landing_home'), {'email': self.test_email},
            follow=True
        )
        self.assertEqual(response.status_code, 200)
        #self.assert

    def test_request_invite_nolang(self):
        """ This should send a mail. """

        response = self.client.post(
            reverse('landing_home'), {'email': self.test_email},
            follow=True
        )
        self.assertEqual(response.status_code, 200)
        time.sleep(6)

    def test_request_invite_lang_fr(self):
        """ This should send a mail in French. """

        response = self.client.post(
            reverse('landing_home'), {'email': self.test_email},
            follow=True, **self.http_headers)
        self.assertEqual(response.status_code, 200)
        time.sleep(6)
