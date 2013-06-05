# -*- coding: utf-8 -*-
# Settings for 1flow.net (local development)

MAIN_SERVER = '127.0.0.1'

from sparks.django.settings import include_snippets

include_snippets(
    (
        # Don't forget to deactivate nobother when we'ge got time to
        # fix other's bugs. Just kidding…
        '000_nobother',
        '00_development',
        # Activate this to test 404/500…
        #'00_production',
        '1flow_io',
        'common',
        'db_common',
        'db_development',
        'cache_common',
        'cache_development',
        'celery_development',
        'mail_development',
        'raven_development',
        'common_development',
        'rosetta',
        'djdt',
    ),
    __file__, globals()
)

# Override `1flow_net` for local development
SITE_DOMAIN = 'localhost:8000'

EMAIL_HOST = 'gurney'
#EMAIL_BACKEND = 'django.core.mail.backends.filebased.EmailBackend'
#EMAIL_FILE_PATH = '/tmp/1flow.mail'
