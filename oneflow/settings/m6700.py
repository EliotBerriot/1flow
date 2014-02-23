# -*- coding: utf-8 -*-
# Settings for another local development machine.
# At the first creation, it was Willian Ver Valen Paiva's Dell Precision M6700.
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

from sparks.django.settings import clone_settings

clone_settings('chani', __file__, globals())

# ——————————————————————————————————————————————————— Dev1 (Willian at my home)

GOOGLE_OAUTH2_CLIENT_ID      = '494350410052-5cgau95ek6dvhnu0c1tov8j9f10b02ou.apps.googleusercontent.com' # NOQA
GOOGLE_OAUTH2_CLIENT_SECRET  = 'qwribFAXXLHPY4_vtR-nkpFz'
#GOOGLE_CONSUMER_KEY          =     'dev1.1flow.io'
#GOOGLE_CONSUMER_SECRET       =  'w78SFaBLwwolPWybAsAGkclr'
SITE_DOMAIN = 'dev1.1flow.io'
EMAIL_HOST = 'gurney'

# ——————————————————————————————————————————————————— Dev2 (Willian's home)

#SITE_DOMAIN = 'dev2.1flow.io'
#GOOGLE_OAUTH2_CLIENT_ID      = '494350410052-kccc59ku23u9rs9bphh2pfbkabu1lihd.apps.googleusercontent.com' # NOQA
#GOOGLE_CONSUMER_KEY          =   'dev2.1flow.io'
#GOOGLE_CONSUMER_SECRET       =  '--EzJz4m8H2DX8ma5_YDLfIM'
#GOOGLE_OAUTH2_CLIENT_SECRET  = 'KCjXlE9df6YiS_cZMekfh6TB'
