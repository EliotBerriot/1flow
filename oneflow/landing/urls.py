# -*- coding: utf-8 -*-

from django.conf.urls import patterns, url
from django.utils.translation import ugettext_lazy as _

urlpatterns = patterns(
    'oneflow.landing.views',
    url(r'^$', 'home', name='landing_home'),
    url(_(r'^thanks/(?P<already_registered>\w+)?$'),
        'thanks', name='landing_thanks'),
)
