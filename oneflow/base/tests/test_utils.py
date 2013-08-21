# -*- coding: utf-8 -*-
# pylint: disable=E1103,C0103

import logging

#from django.conf import settings
from django.test import TestCase  # TransactionTestCase

from oneflow.base.utils.http import clean_url

LOGGER = logging.getLogger(__file__)


class TestHttpUtilsCleanUrl(TestCase):

    def test_utm_star(self):

        good_url = 'http://test.com/mytest/'

        for bad_url in (
            'http://test.com/mytest/?utm_X',
            'http://test.com/mytest/?utm_X&',
            'http://test.com/mytest/?utm_X=',
            'http://test.com/mytest/?utm_X=&',
            'http://test.com/mytest/?utm_X=toto',
            'http://test.com/mytest/?utm_X=toto&',

            'http://test.com/mytest/?utm_source=toto&utm_Y',
            'http://test.com/mytest/?utm_source=toto&utm_Y&',
            'http://test.com/mytest/?utm_source=toto&utm_Y=',
            'http://test.com/mytest/?utm_source=toto&utm_Y=&',
            'http://test.com/mytest/?utm_source=toto&utm_Y=titi',
            'http://test.com/mytest/?utm_source=toto&utm_Y=titi&',

            'http://test.com/mytest/#xtor',
            'http://test.com/mytest/#xtor=',
            'http://test.com/mytest/#xtor=tata',
            'http://test.com/mytest/#xtor&',
            'http://test.com/mytest/#xtor=&',
            'http://test.com/mytest/#xtor=tata&',

            'http://test.com/mytest/?utm_X#xtor',
            'http://test.com/mytest/?utm_X#xtor=',
            'http://test.com/mytest/?utm_X#xtor=tata',

            'http://test.com/mytest/?utm_campaign&#xtor',
            'http://test.com/mytest/?utm_campaign&#xtor=',
            'http://test.com/mytest/?utm_campaign&#xtor=tata',

            'http://test.com/mytest/?utm_X=&#xtor',
            'http://test.com/mytest/?utm_X=&#xtor=',
            'http://test.com/mytest/?utm_X=&#xtor=tata',

            'http://test.com/mytest/?utm_X=toto#xtor',
            'http://test.com/mytest/?utm_X=toto#xtor=',
            'http://test.com/mytest/?utm_X=toto#xtor=tata',

            'http://test.com/mytest/?utm_X=toto&#xtor',
            'http://test.com/mytest/?utm_X=toto&#xtor=',
            'http://test.com/mytest/?utm_X=toto&#xtor=tata',

            'http://test.com/mytest/?utm_X=toto&utm_Y#xtor',
            'http://test.com/mytest/?utm_X=toto&utm_Y#xtor=',
            'http://test.com/mytest/?utm_X=toto&utm_Y#xtor=tata',

            'http://test.com/mytest/?utm_X=toto&utm_Y=#xtor',
            'http://test.com/mytest/?utm_X=toto&utm_Y=#xtor=',
            'http://test.com/mytest/?utm_X=toto&utm_Y=#xtor=tata',

            'http://test.com/mytest/?utm_X=toto&utm_Y=titi#xtor',
            'http://test.com/mytest/?utm_X=toto&utm_Y=titi#xtor=',
            'http://test.com/mytest/?utm_X=toto&utm_Y=titi#xtor=tata',

            'http://test.com/mytest/?utm_X=toto&utm_Y=titi&#xtor',
            'http://test.com/mytest/?utm_X=toto&utm_Y=titi&#xtor=',
            'http://test.com/mytest/?utm_X=toto&utm_Y=titi&#xtor=tata',

            'http://test.com/mytest/?xtor',
            'http://test.com/mytest/?xtor=',
            'http://test.com/mytest/?xtor=tata',
            'http://test.com/mytest/?xtor=tata&',

            'http://test.com/mytest/?utm_X&xtor',
            'http://test.com/mytest/?utm_X&xtor=',
            'http://test.com/mytest/?utm_X&xtor=tata',
            'http://test.com/mytest/?utm_X&xtor=tata&',

            'http://test.com/mytest/?utm_X=&xtor',
            'http://test.com/mytest/?utm_X=&xtor=',
            'http://test.com/mytest/?utm_X=&xtor=tata',
            'http://test.com/mytest/?utm_X=&xtor=tata&',

            'http://test.com/mytest/?utm_X=toto&xtor',
            'http://test.com/mytest/?utm_X=toto&xtor=',
            'http://test.com/mytest/?utm_X=toto&xtor=tata',
            'http://test.com/mytest/?utm_X=toto&xtor=tata&',

            'http://test.com/mytest/?utm_X=toto&utm_Y&xtor',
            'http://test.com/mytest/?utm_X=toto&utm_Y&xtor=',
            'http://test.com/mytest/?utm_X=toto&utm_Y&xtor=tata',
            'http://test.com/mytest/?utm_X=toto&utm_Y&xtor=tata&',

            'http://test.com/mytest/?utm_X=toto&utm_Y=&xtor',
            'http://test.com/mytest/?utm_X=toto&utm_Y=&xtor=',
            'http://test.com/mytest/?utm_X=toto&utm_Y=&xtor=tata',
            'http://test.com/mytest/?utm_X=toto&utm_Y=&xtor=tata&',

            'http://test.com/mytest/?utm_X=toto&utm_Y=titi&xtor',
            'http://test.com/mytest/?utm_X=toto&utm_Y=titi&xtor=',
            'http://test.com/mytest/?utm_X=toto&utm_Y=titi&xtor=tata',
                'http://test.com/mytest/?utm_X=toto&utm_Y=titi&xtor=tata&', ):

            self.assertEquals(clean_url(bad_url), good_url)

    def test_utm_with_other_things(self):

            for bad_url, good_url in (
                ('http://www.begeek.fr/visitez-le-tardis-de-doctor-who-sur-google-maps-101125?utm_source=Plus+d‘actu&utm_medium=cpc&utm_campaign=Plus+d‘actu', # NOQA
                 'http://www.begeek.fr/visitez-le-tardis-de-doctor-who-sur-google-maps-101125'), # NOQA
                ('http://techcrunch.com/2013/05/18/hell-no-tumblr-users-wont-go-to-yahoo/?utm_source=feedburner&utm_medium=feed&utm_campaign=Feed%3A+francaistechcrunch+%28TechCrunch+en+Francais%29', # NOQA
                 'http://techcrunch.com/2013/05/18/hell-no-tumblr-users-wont-go-to-yahoo/'),
                      ):
                self.assertEquals(clean_url(bad_url), good_url)
