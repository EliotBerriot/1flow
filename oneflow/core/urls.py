# -*- coding: utf-8 -*-
from django.conf.urls import patterns, url
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.decorators import login_required

from .views import home, profile

urlpatterns = patterns(
    'oneflow.core.views',
    url(_(r'^home/$'), login_required(home), name='home'),
    url(_(r'^profile/$'), login_required(profile), name='profile'),
)

urlpatterns += patterns(
    'django.contrib.auth.views',
    url(_(r'^signin/$'), 'login',
        {'template_name': 'signin.html'}, name='signin'),
    url(_(r'^signout/$'), 'logout',
        {'template_name': 'signout.html'}, name='signout'),
)
