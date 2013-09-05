# -*- coding: utf-8 -*-

from django.conf import settings

from oneflow import VERSION


def oneflow_version(request):
    return {'oneflow_version': VERSION, 'VERSION': VERSION}


def django_settings(request):

    return {
        u'settings': settings,
    }
