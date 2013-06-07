# -*- coding: utf-8 -*-
# Settings for worbi.1flow.net (preview worker) and florbi (flower instance),
# hosted on the same machine (thus, same settings, thanks to sparks).

from sparks.django.settings import clone_settings

clone_settings('obi.1flow.io', __file__, globals())
