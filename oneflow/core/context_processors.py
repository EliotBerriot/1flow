# -*- coding: utf-8 -*-

from django.conf import settings
from models.nonrel import (CONTENT_TYPE_NONE, CONTENT_TYPE_HTML,
                           CONTENT_TYPE_MARKDOWN, CONTENT_TYPES_FINAL,
                           CACHE_ONE_HOUR, CACHE_ONE_DAY,
                           CACHE_ONE_WEEK, CACHE_ONE_MONTH, )


def mongodb_user(request):
    """ not the most usefull context manager in the world. """

    try:
        if request.user.is_anonymous():
            return {
                u'mongodb_user': None,
                u'preferences': None,
                u'wizards': None,
            }
    except AttributeError:
        # Most probably “'WSGIRequest' object has no attribute 'user'”
        return {}

    mongodb_user = request.user.mongo

    return {
        u'mongodb_user': mongodb_user,
        u'preferences': mongodb_user.preferences,
        u'wizards': mongodb_user.preferences.wizards,

        u'NONREL_ADMIN': settings.NONREL_ADMIN,
    }


def content_types(request):
    """ Inject content types into the context, so we can use them
        by name instead of hardcoding their integer values. """

    return {
        u'CONTENT_TYPE_NONE':     CONTENT_TYPE_NONE,
        u'CONTENT_TYPE_HTML':     CONTENT_TYPE_HTML,
        u'CONTENT_TYPE_MARKDOWN': CONTENT_TYPE_MARKDOWN,
        u'CONTENT_TYPES_FINAL':   CONTENT_TYPES_FINAL,

        u'CACHE_ONE_HOUR':        CACHE_ONE_HOUR,
        u'CACHE_ONE_DAY':         CACHE_ONE_DAY,
        u'CACHE_ONE_WEEK':        CACHE_ONE_WEEK,
        u'CACHE_ONE_MONTH':       CACHE_ONE_MONTH,
    }


def social_things(request):

    if request.user.is_anonymous():
        return {}

    dsa = request.user.social_auth

    return {
        'has_google': dsa.filter(
            provider='google-oauth2').count() > 0,
        'social_count': dsa.all().count()
    }
