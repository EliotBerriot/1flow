# -*- coding: utf-8 -*-
"""
    Copyright 2012-2014 Olivier Cortès <oc@1flow.io>

    This file is part of the 1flow project.

    1flow is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of
    the License, or (at your option) any later version.

    1flow is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public
    License along with 1flow.  If not, see http://www.gnu.org/licenses/

"""

import base64
import logging

#from django.utils.translation import ugettext_lazy as _
from django.http import HttpResponseNotFound
from django.template import RequestContext
from django.template.loader import render_to_string
from django.views.decorators.cache import never_cache
from django.contrib.auth import get_user_model
from django.utils.translation import ugettext_lazy as _
from django.shortcuts import render

from sparks.django.utils import HttpResponseTemporaryServerError

from ..landing.models import LandingUser


LOGGER = logging.getLogger(__name__)

User = get_user_model()


# •••••••••••••••••••••••••••••••••••••••••••••••••• user account related views


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

            LOGGER.warning(u'%s %s (%s) just unregistered from email '
                           u'announcements.', klass.__name__, user.username,
                           user.id)

            return render(request, 'unsubscribe.html',
                          RequestContext(request, {'email': user.email}))

    return HttpResponseNotFound(_('Invalid email or unsubscribe token.'))


def social_signup_closed(request):
    """ This is a mimic of `account.SignupView.closed()` method, used
        when social registration is closed, but local registration is not.
    """

    return render(request, 'account/signup_closed.html', {'social': True})


# •••••••••••••••••••••••••••••••••••••••••••••••••••••••• error / system views


def error_handler(request, *args, **kwargs):
    """ Our error handler returns a 503 instead of a bare 500. Returning a 503
        seems much more correct: the situation is clearly temporary and the
        error will certainly be resolved. For search robots this is better too.

        Besides that point, our handler passes the whole request to the 500
        template, via the whole template context processors chain, which could
        be considered risky, but is really not because we don't have any
        custom processor and Django's one are fully tested (at least we hope).
    """

    return HttpResponseTemporaryServerError(render_to_string('500.html',
                                            context_instance=RequestContext(
                                            request)))


def maintenance_mode(request, *args, **kwargs):
    """ Self-explanatory, isn't it? """

    return HttpResponseTemporaryServerError(render_to_string('503.html',
                                            context_instance=RequestContext(
                                            request)))


def not_found_handler(request, *args, **kwargs):
    """ Our 404 custom handler.

        Basically, it's just a one liner which does exactly what the Django's
        one does, but our 404.html lies in base/templates instead of
        ${root}/templates, and we have no way to specify only the modified
        path. And I don't want to create ${root}/templates just to hold the
        400.html.
    """

    return HttpResponseNotFound(render_to_string('404.html',
                                context_instance=RequestContext(request)))


def crash(request, **kwargs):
    """ deliberately run a non-existent function,
        we need to have a way to trigger a 500. """

    raise RuntimeError(u'Voluntary crash test to validate the error chain.')
