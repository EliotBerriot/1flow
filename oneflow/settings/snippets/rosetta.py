# https://github.com/mbi/django-rosetta
# Please include this snippet after the `cache`-related ones.

INSTALLED_APPS += ('rosetta-grappelli', 'rosetta', )

if 'dummycache' in CACHES['default']['BACKEND'].lower():
    CACHES['rosetta'] = {
        'BACKEND': 'django.core.cache.backends.memcached.PyLibMCCache',
        'LOCATION': '127.0.0.1:11211'
    }

ROSETTA_MESSAGES_PER_PAGE = 25

MAINTENANCE_IGNORE_URLS += (
    r'^/translate/.*',
)
