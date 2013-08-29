# -*- coding: utf-8 -*-

import logging

from .models.nonrel import Preference


LOGGER = logging.getLogger(__name__)


def check_1flow_requirements(social_auth, user, details, request,
                             is_new=False, *args, **kwargs):

    mongodb_user = user.mongo

    try:
        mongodb_user.preferences

    except Preference.DoesNotExist:
        mongodb_user.preferences = Preference().save()
        mongodb_user.save()
