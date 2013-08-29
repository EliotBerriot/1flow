# -*- coding: utf-8 -*-

from .models.nonrel import User


def mongodb_user(request):

    if request.user.is_anonymous():
        return {u'mongodb_user': None}

    try:
        mongodb_user = User.objects.get(id=request.session[u'mongodb_user_id'])

    except KeyError:
        mongodb_user = User.objects.get(django_user=request.user.id)

        # Cache it for next time.
        request.session[u'mongodb_user_id'] = mongodb_user.id

    return {u'mongodb_user': mongodb_user}
