# -*- coding: utf-8 -*-

from constance import config

from django.conf import settings

from oneflow import VERSION


def oneflow_version(request):
    return {'oneflow_version': VERSION, 'VERSION': VERSION}


def settings_and_config(request):

    return {
        u'settings': settings,
        u'config': config,
    }
