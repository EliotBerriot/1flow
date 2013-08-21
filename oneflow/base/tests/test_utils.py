# -*- coding: utf-8 -*-
# pylint: disable=E1103,C0103

import logging

#from django.conf import settings
from django.test import TestCase  # TransactionTestCase

from oneflow.base.utils.http import clean_url

LOGGER = logging.getLogger(__file__)


class TestHttpUtilsCleanUrl(TestCase):

    def test_utm_star(self):

        good_url = u'http://test.com/mytest/'

        for bad_url in (
            u'http://test.com/mytest/?utm_X',
            u'http://test.com/mytest/?utm_X&',
            u'http://test.com/mytest/?utm_X=',
            u'http://test.com/mytest/?utm_X=&',
            u'http://test.com/mytest/?utm_X=toto',
            u'http://test.com/mytest/?utm_X=toto&',

            u'http://test.com/mytest/?utm_source=toto&utm_Y',
            u'http://test.com/mytest/?utm_source=toto&utm_Y&',
            u'http://test.com/mytest/?utm_source=toto&utm_Y=',
            u'http://test.com/mytest/?utm_source=toto&utm_Y=&',
            u'http://test.com/mytest/?utm_source=toto&utm_Y=titi',
            u'http://test.com/mytest/?utm_source=toto&utm_Y=titi&',

            u'http://test.com/mytest/#xtor',
            u'http://test.com/mytest/#xtor=',
            u'http://test.com/mytest/#xtor=tata',
            u'http://test.com/mytest/#xtor&',
            u'http://test.com/mytest/#xtor=&',
            u'http://test.com/mytest/#xtor=tata&',

            u'http://test.com/mytest/?utm_X#xtor',
            u'http://test.com/mytest/?utm_X#xtor=',
            u'http://test.com/mytest/?utm_X#xtor=tata',

            u'http://test.com/mytest/?utm_campaign&#xtor',
            u'http://test.com/mytest/?utm_campaign&#xtor=',
            u'http://test.com/mytest/?utm_campaign&#xtor=tata',

            u'http://test.com/mytest/?utm_X=&#xtor',
            u'http://test.com/mytest/?utm_X=&#xtor=',
            u'http://test.com/mytest/?utm_X=&#xtor=tata',

            u'http://test.com/mytest/?utm_X=toto#xtor',
            u'http://test.com/mytest/?utm_X=toto#xtor=',
            u'http://test.com/mytest/?utm_X=toto#xtor=tata',

            u'http://test.com/mytest/?utm_X=toto&#xtor',
            u'http://test.com/mytest/?utm_X=toto&#xtor=',
            u'http://test.com/mytest/?utm_X=toto&#xtor=tata',

            u'http://test.com/mytest/?utm_X=toto&utm_Y#xtor',
            u'http://test.com/mytest/?utm_X=toto&utm_Y#xtor=',
            u'http://test.com/mytest/?utm_X=toto&utm_Y#xtor=tata',

            u'http://test.com/mytest/?utm_X=toto&utm_Y=#xtor',
            u'http://test.com/mytest/?utm_X=toto&utm_Y=#xtor=',
            u'http://test.com/mytest/?utm_X=toto&utm_Y=#xtor=tata',

            u'http://test.com/mytest/?utm_X=toto&utm_Y=titi#xtor',
            u'http://test.com/mytest/?utm_X=toto&utm_Y=titi#xtor=',
            u'http://test.com/mytest/?utm_X=toto&utm_Y=titi#xtor=tata',

            u'http://test.com/mytest/?utm_X=toto&utm_Y=titi&#xtor',
            u'http://test.com/mytest/?utm_X=toto&utm_Y=titi&#xtor=',
            u'http://test.com/mytest/?utm_X=toto&utm_Y=titi&#xtor=tata',

            u'http://test.com/mytest/?xtor',
            u'http://test.com/mytest/?xtor=',
            u'http://test.com/mytest/?xtor=tata',
            u'http://test.com/mytest/?xtor=tata&',

            u'http://test.com/mytest/?utm_X&xtor',
            u'http://test.com/mytest/?utm_X&xtor=',
            u'http://test.com/mytest/?utm_X&xtor=tata',
            u'http://test.com/mytest/?utm_X&xtor=tata&',

            u'http://test.com/mytest/?utm_X=&xtor',
            u'http://test.com/mytest/?utm_X=&xtor=',
            u'http://test.com/mytest/?utm_X=&xtor=tata',
            u'http://test.com/mytest/?utm_X=&xtor=tata&',

            u'http://test.com/mytest/?utm_X=toto&xtor',
            u'http://test.com/mytest/?utm_X=toto&xtor=',
            u'http://test.com/mytest/?utm_X=toto&xtor=tata',
            u'http://test.com/mytest/?utm_X=toto&xtor=tata&',

            u'http://test.com/mytest/?utm_X=toto&utm_Y&xtor',
            u'http://test.com/mytest/?utm_X=toto&utm_Y&xtor=',
            u'http://test.com/mytest/?utm_X=toto&utm_Y&xtor=tata',
            u'http://test.com/mytest/?utm_X=toto&utm_Y&xtor=tata&',

            u'http://test.com/mytest/?utm_X=toto&utm_Y=&xtor',
            u'http://test.com/mytest/?utm_X=toto&utm_Y=&xtor=',
            u'http://test.com/mytest/?utm_X=toto&utm_Y=&xtor=tata',
            u'http://test.com/mytest/?utm_X=toto&utm_Y=&xtor=tata&',

            u'http://test.com/mytest/?utm_X=toto&utm_Y=titi&xtor',
            u'http://test.com/mytest/?utm_X=toto&utm_Y=titi&xtor=',
            u'http://test.com/mytest/?utm_X=toto&utm_Y=titi&xtor=tata',
                u'http://test.com/mytest/?utm_X=toto&utm_Y=titi&xtor=tata&', ):

            self.assertEquals(clean_url(bad_url), good_url)

    def test_utm_with_other_things(self):

            for bad_url, good_url in (
                (u'http://www.begeek.fr/visitez-le-tardis-de-doctor-who-sur-google-maps-101125?utm_source=Plus+d‘actu&utm_medium=cpc&utm_campaign=Plus+d‘actu', # NOQA
                 u'http://www.begeek.fr/visitez-le-tardis-de-doctor-who-sur-google-maps-101125'), # NOQA
                (u'http://techcrunch.com/2013/05/18/hell-no-tumblr-users-wont-go-to-yahoo/?utm_source=feedburner&utm_medium=feed&utm_campaign=Feed%3A+francaistechcrunch+%28TechCrunch+en+Francais%29', # NOQA
                 u'http://techcrunch.com/2013/05/18/hell-no-tumblr-users-wont-go-to-yahoo/'), # NOQA
                      ):
                self.assertEquals(clean_url(bad_url), good_url)
