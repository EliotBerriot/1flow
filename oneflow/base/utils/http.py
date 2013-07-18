# -*- coding: utf-8 -*-

import re

UTM_RE  = re.compile(r'[&]?utm_[^=]+(=[^&]*)?', re.I)
XTOR_RE = re.compile(r'[&#]?xtor(=[^&]*)?', re.I)
LAST_RE = re.compile(r'[?&#]*$', re.I)


def clean_url(url):
    """ Remove all ``utm_*`` ad-related stuff, and more. """

    return LAST_RE.sub(u'',
                       UTM_RE.sub(u'',
                       XTOR_RE.sub(u'',
                       url)))
