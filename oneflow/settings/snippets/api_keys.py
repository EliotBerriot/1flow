# -*- coding: utf-8 -*-
#
# Django API keys, all loaded from the environment,
# conforming to http://www.12factor.net/config :-D
#
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

import os

__module_globals = globals()

for key_name in (

    # ••••••••••••••••••••••••••••••••••••••••••••• Django Social Auth API keys

    'TWITTER_CONSUMER_KEY',
    'TWITTER_CONSUMER_SECRET',
    #'FACEBOOK_APP_ID',
    #'FACEBOOK_API_SECRET',
    'LINKEDIN_CONSUMER_KEY',
    'LINKEDIN_CONSUMER_SECRET',
    #'ORKUT_CONSUMER_KEY',
    #'ORKUT_CONSUMER_SECRET',
    'GOOGLE_DISPLAY_NAME',
    'GOOGLE_CONSUMER_KEY',
    'GOOGLE_CONSUMER_SECRET',
    'GOOGLE_OAUTH2_CLIENT_ID',
    'GOOGLE_OAUTH2_CLIENT_SECRET',
    #'FOURSQUARE_CONSUMER_KEY',
    #'FOURSQUARE_CONSUMER_SECRET',
    #'VK_APP_ID',
    #'VK_API_SECRET',
    #'LIVE_CLIENT_ID',
    #'LIVE_CLIENT_SECRET',
    #'SKYROCK_CONSUMER_KEY',
    #'SKYROCK_CONSUMER_SECRET',
    #'YAHOO_CONSUMER_KEY',
    #'YAHOO_CONSUMER_SECRET',
    #'READABILITY_CONSUMER_SECRET',
    #'READABILITY_CONSUMER_SECRET'

    # •••••••••••••••••••••••••••••••••••••••••••••••••••••••••• Other API keys

    'READABILITY_PARSER_SECRET',
):
    __module_globals[key_name] = os.environ.get(key_name, '')
