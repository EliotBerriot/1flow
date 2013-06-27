# -*- coding: utf-8 -*-
from django.conf.urls import patterns, url
from django.utils.translation import ugettext_lazy as _

urlpatterns = patterns(
    'oneflow.base.views',

    url(_(r'^unsubscribe/(?P<email>[^/]+)/(?P<hash_code>\w{32,32})?$'),
        'unsubscribe', name='unsubscribe'),

    url(r'^500/?$', 'error_handler',
        name='view_500', kwargs={'raise_exception': False}),
    url(r'^500/sentry$', 'error_handler', name='view_500'),
    url(r'^crash/?$', 'crash', name='crash'),
)
