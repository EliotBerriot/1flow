
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.PyLibMCCache',
        'LOCATION': '127.0.0.1:11211'
    }
}

# In development environement we completely
# bypass the cache to see changes in reatime.
if DEBUG:
    CACHES['default']['BACKEND']  = 'django.core.cache.backends.dummy.DummyCache'

# Be sure our multiple sites don't collide,
# but keep the prefix as short as possible.
CACHE_MIDDLEWARE_KEY_PREFIX = '%02d' % SITE_ID

