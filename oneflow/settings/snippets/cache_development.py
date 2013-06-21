
# In development environement, we completely bypass the cache,
# to see changes in reatime.
CACHES['default']['BACKEND']  = 'django.core.cache.backends.dummy.DummyCache'
