# -*- coding: utf-8 -*-

from oneflow import VERSION


def oneflow_version(request):
    return {'oneflow_version': VERSION}
