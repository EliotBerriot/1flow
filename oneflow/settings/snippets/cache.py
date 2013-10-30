
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.PyLibMCCache',
        'LOCATION': '127.0.0.1:11211',
        'TIMEOUT': 3600,

        # Only for locmem, filesystem and database backends
        #
        # 'OPTIONS': {
        #     'MAX_ENTRIES': 65535,
        #     'CULL_FREQUENCY': 10,
        # }
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

