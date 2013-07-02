# -*- coding: utf-8 -*-
# Settings for obi.1flow.io (preview)

from sparks.django.settings import include_snippets

include_snippets(
    (
        '000_nobother',
        # we use "production". We don't debug on OBI: we need to be
        # in "real-life-mode", as closer as possible of the real
        # production servers. Sentry will catch all errors, anyway.
        '00_production',
        '1flow_io',
        'common',
        'constance',
        'api_keys',
        'databases',
        'cache',
        'celery',
        'mail_production',
        # But it's a preview/test environment, still.
        'common_preview',
        # Thus we get rosetta, and the Django Debug toolbar.
        'rosetta',
        'djdt',
    ),
    __file__, globals()
)

# Override `1flow_io` for preview/test environment.
SITE_DOMAIN = 'obi.1flow.io'

# OBI is the master for translations and content creation / modifications,
# cf. https://trello.com/c/dJoV4xZy . Final production is synchronized
# via deployment tools.
FULL_ADMIN = True
