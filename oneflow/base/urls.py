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
#from __future__ import unicode_literals
from django.conf.urls import patterns, url
#from django.conf.urls.i18n import i18n_patterns
from django.utils.translation import ugettext_lazy as _
#from django.core.urlresolvers import reverse_lazy

urlpatterns = patterns(
    'oneflow.base.views',

    url(_(r'^unsubscribe/(?P<email>[^/]+)/(?P<hash_code>\w{32,32})?$'),
        'unsubscribe', name='unsubscribe'),

    url(_(r'^social_signup_closed/$'), 'social_signup_closed',
        name='social_signup_closed'),

    url(r'^500/?$', 'error_handler',
        name='view_500', kwargs={'raise_exception': False}),
    url(r'^500/sentry$', 'error_handler', name='view_500'),
    url(r'^crash/?$', 'crash', name='crash'),
)
