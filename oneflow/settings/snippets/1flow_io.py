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

import datetime

SITE_ID     = 1
SITE_DOMAIN = '1flow.io'
SITE_NAME   = '1flow'

# WARNING: keep this a date(), which is neither naive nor TZ aware.
LANDING_BETA_DATE = datetime.date(2013, 07, 01)
LANDING_BETA_INVITES = 100

# We now need full access to content editors in production for fast fixes.
# This is not definitive, but will help making content more user-friendly
# without hassling back-and-forth between development and production via CLI.
FULL_ADMIN = True
