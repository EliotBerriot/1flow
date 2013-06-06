# -*- coding: utf-8 -*-
# Settings for obi.1flow.net (test)

from sparks.django.settings import clone_settings

clone_settings('obi.1flow.io', __file__, globals())

# worbi has no admin, it's a worker…
FULL_ADMIN = False
