# -*- coding: utf-8 -*-
# Settings for zero.1flow.io, a master clone used to validate migrations.

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
        'mail_production',
        'raven_development',
        'common_production',
    ),
    __file__, globals()
)

# Overide real production settings, to be able to distinguish.
SITE_DOMAIN = 'zero.1flow.io'
ALLOWED_HOSTS += ['localhost', SITE_DOMAIN]

# OMG: do not attach to real production database.
DATABASES['default']['HOST'] = '10.0.3.1'
