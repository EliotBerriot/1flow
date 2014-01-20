# -*- coding: utf-8 -*-
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

import sys

DEBUG = True
TEMPLATE_DEBUG = DEBUG
TASTYPIE_FULL_DEBUG = DEBUG

for celery_name in ('celery', 'celeryd', 'worker', 'flower'):
    if celery_name in sys.argv:
        # Avoid the infamous 'Using settings.DEBUG leads to a memory leak,
        # never use this setting in production environments!' message, cf.
        # http://stackoverflow.com/a/4806384/654755
        DEBUG = False
        break

# Development installs exhibit all admin models.
FULL_ADMIN = True
