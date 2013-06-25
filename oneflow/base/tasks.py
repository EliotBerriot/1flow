# -*- coding: utf-8 -*-

import logging
#import datetime

from celery import task

from django.contrib.auth import get_user_model

LOGGER = logging.getLogger(__name__)

User = get_user_model()

#ftstamp = datetime.datetime.fromtimestamp
#now     = datetime.datetime.now


@task
def celery_beat_test():

    LOGGER.info(u'testing celery beat scheduler…')


@task
def refresh_access_tokens():
    """ Refresh all access_tokens in turn to avoid hitting
        http://dev.1flow.net/webapps/1flow/group/664/
    """

    users = User.objects.all()

    #count = users.count()
    #sleep_time = 1500 / count

    for user in users:
        # See http://django-social-auth.readthedocs.org/en/latest/use_cases.html#token-refreshing # NOQA
        #LOGGER.warning(u'Refreshing invalid access_token for user %s.',
        #               user.username)

        social_accounts = user.social_auth.filter(provider='google-oauth2')

        if social_accounts.count() == 0:
            continue

        for social in social_accounts:
            try:
                social.refresh_token()

            except:
                LOGGER.error(u'Access token could not be refreshed for user '
                             u'%s, forcing re-authentication at next login.')

                # TODO: force re-auth of user at next visit.
