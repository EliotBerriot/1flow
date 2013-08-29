# -*- coding: utf-8 -*-


def mongodb_user(request):
    """ not the most usefull context manager in the world. """

    if request.user.is_anonymous():
        return {u'mongodb_user': None}

    return {u'mongodb_user': request.user.mongo}
