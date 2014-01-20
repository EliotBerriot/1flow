# -*- coding: utf-8 -*-
# Settings for 1flow.net (production)
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
        '1flow_io',
        'common',
        'constance',
        'api_keys',
        'databases',
        'cache',
        'celery',
        'mail_production',
        'common_production',
        #NOTE: *NEVER* 'rosetta' here. We can't get the new translations
        #   back from production to the git repo, due to to git-flow
        #   design. Which makes perfect sense in production, anyway.
    ),
    __file__, globals()
)
