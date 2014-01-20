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

import logging

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from oneflow.landing.models import LandingUser

LOGGER = logging.getLogger(__name__)

User = get_user_model()


class Command(BaseCommand):
    help = 'set date_published for all articles who have GR original data.'

    def handle(self, *args, **options):
        """ In 0.15 we moved beta registered users to a dedicated table.
            As it's the Django `User` model involved, `south` just fails
            miserably with error “AttributeError: 'User' object has no
            attribute 'id'”.

            Thus I needed to write a manual command for this, hooked in
            the post-migration as a shell call…
        """
        done = 0
        errors = 0

        for user in User.objects.filter(email__startswith='BETA_'):

            try:
                landing_user, created = LandingUser.objects.get_or_create(
                    # filter out the 'BETA_' prefix
                    email=user.email[5:], date_joined=user.date_joined)

                landing_user.data = user.profile.data
                landing_user.register_data = user.profile.register_request_data
                landing_user.email_announcements = user.profile.email_announcements # NOQA
                landing_user.hash_codes['unsubscribe'] = user.profile.hash_code
                landing_user.last_modified = user.profile.last_modified

                landing_user.save()

            except:
                LOGGER.exception(u'Could not migrate user %s from base to '
                                 u'landing!', user.username)
                errors += 1
            else:
                done += 1
                try:
                    user.delete()
                except:
                    LOGGER.exception(u'Could not delete user %s (%s) from '
                                     u'base.User.', user.username, user.id)

        self.stdout.write(u'Done migrating %s user(s) from base to landing, '
                          u'with %s error(s).' % (done, errors))
