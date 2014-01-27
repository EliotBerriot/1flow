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

import datetime

# On http://1flow.io/ there is a supplemental 'landing' Django
# application to describe the project and register beta-users.
# It must come before the 'core' and after the 'base'.
# NOTE: because of this, INSTALLED_APPS is a list (not a tuple).
INSTALLED_APPS.insert(INSTALLED_APPS.index('oneflow.core'),
                      'oneflow.landing')

# WARNING: keep this a date(), which is neither naive nor TZ aware.
LANDING_BETA_DATE = datetime.date(2013, 07, 01)
LANDING_BETA_INVITES = 100

PIPELINE_CSS.update({
    'landing': {
        # This one is not "compiled" but simply copied. We wanted it
        # to be integrated into the pipeline for consistency only.
        'source_filenames': (
            'css/landing-styles.css',
        ),
        'output_filename': 'css/landing.css',
    },
})
