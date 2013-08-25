# -*- coding: utf-8 -*-
# pylint: disable=E1103,C0103

import logging

from django.test import TestCase

from oneflow.base.tests import connect_mongodb_testsuite
from oneflow.core.models import Article
from oneflow.core.stats import (PythonErrorClassifier, GenericErrorClassifier,
                                UrlErrorClassifier, ContentErrorClassifier)

LOGGER = logging.getLogger(__file__)

connect_mongodb_testsuite()


class ErrorClassifierTests(TestCase):

    def setUp(self):

        Article.drop_collection()

        self.a1 = Article(title='ErrorClassifierTests #1',
                          url='http://t.co/t1').save()
        self.a2 = Article(title='ErrorClassifierTests #2',
                          url='http://t.co/t2',
                          url_error="HTTPConnectionPool(host='t.co', port=80): Max retries exceeded with url: /t1 (Caused by <class 'socket.error'>: [Errno 60] Operation timed out)").save() # NOQA
        self.a3 = Article(title='ErrorClassifierTests #3',
                          url='http://t.co/t3',
                          url_error="HTTP Error 404 (Not Found) while resolving http://t.co/t3.").save() # NOQA
        self.a4 = Article(title='ErrorClassifierTests #4',
                          url='http://t.co/t4',
                          url_error="HTTP Error 404 (Not Found) while resolving http://t.co/t4.").save() # NOQA
        self.a5 = Article(title='ErrorClassifierTests #5',
                          url='http://t.co/t5',
                          url_error="HTTPConnectionPool(host='t.co', port=80): Max retries exceeded with url: /t5 (Caused by <class 'socket.error'>: [Errno 65] No route to host)").save() # NOQA
        self.a6 = Article(title='ErrorClassifierTests #6',
                          url='http://t.co/6',
                          url_error="HTTPConnectionPool(host='t.co', port=80): Max retries exceeded with url: /t6 (Caused by <class 'socket.error'>: [Errno 54] Connection reset by peer)").save() # NOQA

    def test_python_errors_classifiers(self):

        results = PythonErrorClassifier(Article.objects(url_error__ne=''),
                                        'url_error').classify()

        stored = results.get('stored_instances')
        errors = results.get('error_types')

        self.assertEquals(results.get('seen_objects'), 5)

        self.assertEquals(len(errors), 5)
        self.assertEquals(len(stored), 5)

    def test_generic_errors_classifiers(self):

        results = GenericErrorClassifier(Article.objects(url_error__ne=''),
                                         'url_error').classify()

        stored = results.get('stored_instances')
        errors = results.get('error_types')

        self.assertEquals(results.get('seen_objects'), 5)

        self.assertEquals(len(errors), 5)
        self.assertEquals(len(stored), 5)

    def test_url_error_classifier(self):

        # NOTE: these errors strings are directly taken from the production
        #       database. Only URLs have been changed for tests.
        #

        results = UrlErrorClassifier(Article.objects(url_error__ne=''),
                                     'url_error').classify()

        self.assertEquals(sorted(results.keys()), [u'duration',
                          u'error_types', u'seen_objects', u'stored_instances'])
        self.assertEquals(results.get('seen_objects'), 5)

        stored = results.get('stored_instances')
        errors = results.get('error_types')

        self.assertEquals(len(errors), 4)
        self.assertEquals(len(stored), 4)

        err404 = stored.get(UrlErrorClassifier.ERR_NETWORK_OTHER)
        self.assertEquals(len(err404), 2)

        self.assertTrue(self.a3 in err404)
        self.assertTrue(self.a4 in err404)

    def test_content_error_classifier(self):

        # NOTE: these errors strings are directly taken from the production
        #       database. Only URLs have been changed for tests.
        #

        results = ContentErrorClassifier(Article.objects(url_error__ne=''),
                                         'content_error').classify()

        self.assertEquals(results.get('seen_objects'), 5)

        #
        # TODO: create articles and continue this test.
        #
