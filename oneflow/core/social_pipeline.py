# -*- coding: utf-8 -*-

import logging

from .models.nonrel import Preferences


LOGGER = logging.getLogger(__name__)


def check_1flow_requirements(social_auth, user, details, request,
                             is_new=False, *args, **kwargs):

    mongodb_user = user.mongo

    try:
        mongodb_user.preferences

    except Preferences.DoesNotExist:
        mongodb_user.preferences = Preferences().save()
        mongodb_user.save()
