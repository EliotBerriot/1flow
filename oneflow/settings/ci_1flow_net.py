# -*- coding: utf-8 -*-
# Settings for Jenkins CI virtual machine.

from sparks.django.settings import clone_settings

clone_settings('chani', __file__, globals())
