# -*- coding: utf-8 -*-
"""
    Copyright 2013 Olivier Cortès <oc@1flow.io>

    This file is part of the 1flow project.

    1flow is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of
    the License, or (at your option) any later version.

    1flow is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public
    License along with 1flow.  If not, see http://www.gnu.org/licenses/

"""

import copy
import logging

from django.conf import settings
from django.utils.importlib import import_module
from django.utils.module_loading import module_has_submodule

# We use mongoadmin to replace the Django classic admin site.
from django.contrib.admin.sites import site as django_admin_site

LOGGER = logging.getLogger(__name__)


def autodiscover():
    """ This function mimics the Django's one, but doesn't crash on auth.User
        it the User model has been swapped for our own. """

    for app in settings.INSTALLED_APPS:
        mod = import_module(app)
        # Attempt to import the app's admin module.
        try:
            before_import_registry = copy.copy(django_admin_site._registry)
            import_module('%s.admin' % app)

        except Exception, e:
            # Reset the model registry to the state before the last import as
            # this import will have to reoccur on the next request and this
            # could raise NotRegistered and AlreadyRegistered exceptions
            # (see #8245).
            django_admin_site._registry = before_import_registry

            # Decide whether to bubble up this error. If the app just
            # doesn't have an admin module, we can ignore the error
            # attempting to import it, otherwise we want it to bubble up.
            if module_has_submodule(mod, 'admin'):
                LOGGER.exception('>>> %s: %s', mod.__name__, e)
