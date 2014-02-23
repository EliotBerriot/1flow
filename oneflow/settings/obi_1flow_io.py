# -*- coding: utf-8 -*-
# Settings for obi.1flow.io (preview)
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
        # we use "production". We don't debug on OBI: we need to be
        # in "real-life-mode", as closer as possible of the real
        # production servers. Sentry will catch all errors, anyway.
        '00_production',
        '1flow_io_pre_common',
        'common',
        '1flow_io_post_common',
        'constance',
        'api_keys',
        'databases',
        'cache',
        'celery',
        'mail_production',
        # But it's a preview/test environment, still.
        'common_preview',
        # Thus we get rosetta, and the Django Debug toolbar.
        'rosetta',
        'djdt',
    ),
    __file__, globals()
)

# Override `1flow_io` for preview/test environment.
SITE_DOMAIN = 'obi.1flow.io'

# OBI is the master for translations and content creation / modifications,
# cf. https://trello.com/c/dJoV4xZy . Final production is synchronized
# via deployment tools.
FULL_ADMIN = True
