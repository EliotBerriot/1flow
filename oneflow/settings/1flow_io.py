# -*- coding: utf-8 -*-
# Settings for 1flow.net (production)

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
        'cache',
        'celery',
        'mail_production',
        'common_production',
        #NOTE: *NEVER* 'rosetta' here. We can't get the new translations
        #   back from production to the git repo, due to to git-flow
        #   design. Which makes perfect sense in production, anyway.
    ),
    __file__, globals()
)
