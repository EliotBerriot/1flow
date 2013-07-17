# -*- coding: utf-8 -*-

import re

UTM_RE = re.compile(r'[?&]?utm_[^=]+=[^&]+', re.I)


def clean_url(url):
    """ Remove all ``utm_*`` ad-related stuff, and more. """

    return UTM_RE.sub(u'', url).replace(u'#xtor=RSS-1', u'')
