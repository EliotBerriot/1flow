# -*- coding: utf-8 -*-
# Settings for zero.1flow.io, a single-host production clone
# used to validate migrations. The LXC guest is resetted every
# night (see on Gurney.licorn.org olive::crontab)

from sparks.django.settings import include_snippets

include_snippets(
    (
        '000_nobother',
        '00_production',
        '1flow_io',
        'common',
        'constance',
        'api_keys',
        'databases',
        'constance',
        'cache',
        'celery',
        'mail_production',
        'common_production',
        # we need django-nose, devserver, etc.
        'common_development',
    ),
    __file__, globals()
)

# Overide real production settings, to be able to distinguish.
SITE_DOMAIN = 'zero.1flow.io'
ALLOWED_HOSTS += ['localhost', SITE_DOMAIN]
