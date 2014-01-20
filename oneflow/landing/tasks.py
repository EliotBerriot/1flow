# -*- coding: utf-8 -*-
"""
    Copyright 2013-2014 Olivier Cortès <oc@1flow.io>

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

import logging

from celery import task
#from django.contrib.sessions.models import Session
from redis_sessions.session import SessionStore

from .funcs import get_beta_invites_left
from .models import LandingUser

from ..base.utils.mail import send_email_with_db_content


LOGGER = logging.getLogger(__name__)


@task()
def background_post_register_actions(context):
    """ Do whatever needed after a new user just registered on the
        application landing page. """

    meta = context['meta']
    user = LandingUser.objects.get(id=context['new_user_id'])

    # Classic Django
    #session = Session.objects.get(pk=context['session_key'])

    # redis_sessions.
    session = SessionStore(session_key=context['session_key'])

    has_invites_left = get_beta_invites_left(True) > 0

    send_email_with_db_content(context,
                               'landing_thanks'
                               if has_invites_left
                               else 'landing_waiting_list')

    user.register_data = {
        'language': meta.get('HTTP_ACCEPT_LANGUAGE', ''),
        'user_agent': meta.get('HTTP_USER_AGENT', ''),
        'encoding': meta.get('HTTP_ACCEPT_ENCODING', ''),
        'remote_addr': meta.get('HTTP_X_FORWARDED_FOR',
                                meta.get('REMOTE_ADDR', '')),
        'referer': session.get('INITIAL_REFERER', ''),
    }

    user.save()

    try:
        del session['INITIAL_REFERER']

    except KeyError:
        pass
