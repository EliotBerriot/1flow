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

from django.conf import settings

from ..base.utils.dateutils import today

from models import LandingContent, LandingUser


def get_all_beta_data():
    """ Return all Landing BETA related data, in a way suited to be used as::

        context.update(get_all_beta_data())

    """

    return get_translations() + get_beta_invites_left() + get_beta_time_left()


def get_beta_invites_left(only_number=False):

    beta_invites_left = settings.LANDING_BETA_INVITES \
        - LandingUser.objects.count()

    if only_number:
        return beta_invites_left

    return (('beta_invites_left', beta_invites_left), )


def get_beta_time_left():

    delta = (settings.LANDING_BETA_DATE - today())

    return (('beta_time_left', delta.days * 86400 + delta.seconds), )


def get_translations():

    # We can't speed up this thing with .values_list() because
    # Transmeta's way of doing thing isn't compatible with it:
    # it would need to specify the *_lang field name, which
    # would avoid the ability to fallback to default lang if
    # the field has no translation.
    return tuple((x.name, x.content) for x in LandingContent.objects.all())
