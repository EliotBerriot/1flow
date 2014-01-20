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

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.PyLibMCCache',
        'LOCATION': os.environ.get('CACHE_DEFAULT'),
        'TIMEOUT': 3600,

        # Only for locmem, filesystem and database backends
        #
        # 'OPTIONS': {
        #     'MAX_ENTRIES': 65535,
        #     'CULL_FREQUENCY': 10,
        # }
    },
    'persistent': {
        'BACKEND': 'redis_cache.cache.RedisCache',
        # Don't set any fallback, we *need* to have this configured in `.env`.
        'LOCATION': os.environ.get('REDIS_PERSISTENT_DB'),
        'OPTIONS': {
            'CLIENT_CLASS': 'redis_cache.client.DefaultClient',
        }
    }
}

# In development, I now use a cache for enhanced reading speed
# and production-like behaviour check. But in case I need to
# disable it, just uncomment the next two lines.
#
# if DEBUG:
#    CACHES['default']['BACKEND']  = 'django.core.cache.backends.dummy.DummyCache'

SELECT2_MEMCACHE_HOST = '127.0.0.1'
SELECT2_MEMCACHE_PORT = '11211'

# Be sure our multiple sites don't collide,
# but keep the prefix as short as possible.
CACHE_MIDDLEWARE_KEY_PREFIX = '%02d' % SITE_ID

# Not required: settings for django-cache-utils
#CACHE_BACKEND = 'cache_utils.group_backend://localhost:11211/'

