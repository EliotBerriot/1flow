# -*- coding: utf-8 -*-
# pylint: disable=E1103,C0103
"""
    Copyright 2012-2014 Olivier Cortès <oc@1flow.io>

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

#from django.conf import settings
from django.test import TestCase  # TransactionTestCase

from oneflow.base.utils.http import clean_url

LOGGER = logging.getLogger(__file__)


class TestHttpUtilsCleanUrl(TestCase):

    def test_utm_star(self):

        good_url = u'http://test.com/mytest/'

        for bad_url in (
            u'http://test.com/mytest/?=',
            u'http://test.com/mytest/?#',
            u'http://test.com/mytest/#?=',
            u'http://test.com/mytest/?=rss',
            u'http://test.com/mytest/?=rss-450',
            u'http://test.com/mytest/?=rss-450&',
            u'http://test.com/mytest/?=rss-450&=rss',

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
                (u'http://www.liberation.fr/politiques/2013/09/24/la-niche-fiscale-pour-les-parents-d-enfants-scolarises-sera-conservee_934193?=rss-450', # NOQA
                 u'http://www.liberation.fr/politiques/2013/09/24/la-niche-fiscale-pour-les-parents-d-enfants-scolarises-sera-conservee_934193'), # NOQA

                # This one must not be changed.
                (u'http://tctechcrunch2011.files.wordpress.com/2013/09/screen-shot-2013-09-24-at-5-57-35-am.png?w=1280&h=948', # NOQA
                 u'http://tctechcrunch2011.files.wordpress.com/2013/09/screen-shot-2013-09-24-at-5-57-35-am.png?w=1280&h=948'), # NOQA
                      ):
                self.assertEquals(clean_url(bad_url), good_url)
