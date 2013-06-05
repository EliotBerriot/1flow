# -*- coding: utf-8 -*-
# Settings for zero.1flow.io, a master clone used to validate migrations.

# This will connect all databases to local LXC host,
# instead of production host. SAFER.
MAIN_SERVER = '10.0.3.1'

from sparks.django.settings import include_snippets

include_snippets(
    (
        '000_nobother',
        '00_production',
        '1flow_io',
        'common',
        'db_common',
        'db_production',
        'cache_common',
        'cache_production',
        'celery_production',
        'mail_production',
        'raven_development',
        'common_production',
    ),
    __file__, globals()
)

# Overide real production settings, to be able to distinguish.
SITE_DOMAIN = 'zero.1flow.io'
ALLOWED_HOSTS += ['localhost', SITE_DOMAIN]
