# -*- coding: utf-8 -*-
# Settings for zero.1flow.io, a single-host production clone
# used to validate migrations. The LXC guest is resetted every
# night (see on Gurney.licorn.org olive::crontab)
"""
    Copyright 2013 Olivier Cortès <oc@1flow.io>

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

from sparks.django.settings import include_snippets

include_snippets(
    (
        '000_nobother',
        '00_production',
        '1flow_io_pre_common',
        'common',
        '1flow_io_post_common',
        'constance',
        'api_keys',
        'databases',
        'constance',
        'cache',
        'celery',
        'mail_production',
        'common_production',
        # we need django-nose, devserver, etc.
        'common_development',
    ),
    __file__, globals()
)

# Overide real production settings, to be able to distinguish.
SITE_DOMAIN = 'zero.1flow.io'
EMAIL_SUBJECT_PREFIX='[ZERO.1flow] '

ALLOWED_HOSTS += ['localhost', SITE_DOMAIN]
