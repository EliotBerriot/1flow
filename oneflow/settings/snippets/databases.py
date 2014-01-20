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

import dj_database_url
import mongoengine

# will be filled by sub-snippets
DATABASES = {
    'default': dj_database_url.config(),
}

DATABASES['default']['OPTIONS'] = {
    'autocommit': True,
}

MONGODB_NAME = os.environ.get('MONGODB_NAME')
MONGODB_HOST = os.environ.get('MONGODB_HOST')
MONGODB_PORT = int(os.environ.get('MONGODB_PORT', 27017))

MONGODB_NAME_ARCHIVE = os.environ.get('MONGODB_NAME_ARCHIVE')
MONGODB_HOST_ARCHIVE = os.environ.get('MONGODB_HOST_ARCHIVE')
MONGODB_PORT_ARCHIVE = int(os.environ.get('MONGODB_PORT_ARCHIVE', 27017))

mongoengine.connect(MONGODB_NAME,
                    host=MONGODB_HOST,
                    port=MONGODB_PORT,
                    tz_aware=USE_TZ)

# http://mongoengine-odm.readthedocs.org/en/latest/apireference.html#connecting
mongoengine.register_connection('archive',              # alias
                                MONGODB_NAME_ARCHIVE,   # name
                                host=MONGODB_HOST_ARCHIVE,
                                port=MONGODB_PORT_ARCHIVE,
                                tz_aware=USE_TZ)

REDIS_HOST = os.environ.get('REDIS_HOST', MAIN_SERVER)
REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
REDIS_DB   = int(os.environ.get('REDIS_DB'))

REDIS_TEST_HOST = os.environ.get('REDIS_TEST_HOST', MAIN_SERVER)
REDIS_TEST_PORT = int(os.environ.get('REDIS_TEST_PORT', REDIS_PORT))
REDIS_TEST_DB   = int(os.environ.get('REDIS_TEST_DB'))

REDIS_DESCRIPTORS_HOST = os.environ.get('REDIS_DESCRIPTORS_HOST', MAIN_SERVER)
REDIS_DESCRIPTORS_PORT = int(os.environ.get('REDIS_DESCRIPTORS_PORT', REDIS_PORT))
REDIS_DESCRIPTORS_DB   = int(os.environ.get('REDIS_DESCRIPTORS_DB'))

REDIS_FEEDBACK_HOST = os.environ.get('REDIS_FEEDBACK_HOST', MAIN_SERVER)
REDIS_FEEDBACK_PORT = int(os.environ.get('REDIS_FEEDBACK_PORT', REDIS_PORT))
REDIS_FEEDBACK_DB   = int(os.environ.get('REDIS_FEEDBACK_DB'))

CONSTANCE_REDIS_CONNECTION = os.environ.get('CONSTANCE_REDIS_CONNECTION')

SESSION_REDIS_PREFIX = 'sss'
SESSION_REDIS_HOST   = os.environ.get('SESSION_REDIS_HOST', MAIN_SERVER)
SESSION_REDIS_DB     = int(os.environ.get('SESSION_REDIS_DB'))
SESSION_REDIS_PORT   = int(os.environ.get('SESSION_REDIS_PORT', REDIS_PORT))

# TODO: if we ever need this, move it to $ENV!
#SESSION_REDIS_PASSWORD = 'password'
