# -*- coding: utf-8 -*-
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

import re

UTM_RE  = re.compile(ur'[&]?utm_[^=]+(=[^&]*)?', re.I)
XTOR_RE = re.compile(ur'[&#]?xtor(=[^&]*)?', re.I)
EQL_RE  = re.compile(ur'[#&?]=[^&]+', re.I)
LAST_RE = re.compile(ur'[?&#=]*$', re.I)


def clean_url(url):
    """ Remove all ``utm_*`` ad-related stuff, and more. """

    return LAST_RE.sub(
        u'', EQL_RE.sub(
            u'', UTM_RE.sub(
                u'', XTOR_RE.sub(
                    u'', url
                )
            )
        )
    )
