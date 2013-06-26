# -*- coding: utf-8 -*-

import base64
import logging

#from django.utils.translation import ugettext_lazy as _
from django.template import RequestContext
from django.shortcuts import render
from django.http import HttpResponseNotFound
from django.views.decorators.cache import never_cache
from django.contrib.auth import get_user_model
from django.utils.translation import ugettext_lazy as _

from ..landing.models import LandingUser

LOGGER = logging.getLogger(__name__)

User = get_user_model()


@never_cache
def unsubscribe(request, email, hash_code):

    email = base64.b64decode(email)

    for klass in LandingUser, User:
        try:
            user = klass.objects.get(email=email)

        except:
            continue

        if hash_code == user.hash_codes.get('unsubscribe', None):
            user.email_announcements = False
            user.renew_hash_code('unsubscribe', commit=False)
            user.save(update_fields=('hash_codes', 'email_announcements', ))

            return render(request, 'unsubscribe.html',
                          RequestContext(request, {'email': user.email}))

    return HttpResponseNotFound(_('Invalid email or unsubscribe token.'))
