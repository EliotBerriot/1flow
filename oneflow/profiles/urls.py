# -*- coding: utf-8 -*-

from django.conf.urls import patterns, url
from django.utils.translation import ugettext_lazy as _

urlpatterns = patterns(
    'oneflow.profiles.views',
    url(_(r'^unsubscribe/(?P<email>[^/]+)/(?P<hash_code>\w{32,32})?$'),
        'unsubscribe', name='unsubscribe'),
)
