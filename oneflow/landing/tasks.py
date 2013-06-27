# -*- coding: utf-8 -*-

import logging

from celery import task
#from django.contrib.sessions.models import Session
from redis_sessions.session import SessionStore

from .funcs import get_beta_invites_left
from .models import LandingUser

from ..base.utils import send_email_with_db_content


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
