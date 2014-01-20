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

import os
import logging

import importlib

from django.conf import settings
from tastypie.api import Api

from tastypie.resources import ModelResource
from tastypie_mongoengine.resources import MongoEngineResource

LOGGER = logging.getLogger(__name__)

v1_api = Api(api_name='v1')

PROJECT_NAME = os.path.basename(os.path.dirname(__file__))

for app_name in settings.INSTALLED_APPS:
    if app_name.startswith(PROJECT_NAME):
        if os.path.exists(os.path.join(
                          app_name.replace('.', os.path.sep), 'api.py')):
            module_name = '{}.api'.format(app_name)
            apimod = importlib.import_module(module_name)

            for objekt_name in (apimod.__all__ if hasattr(
                                apimod, '__all__') else dir(apimod)):
                objekt = getattr(apimod, objekt_name)
                try:
                    if issubclass(objekt, MongoEngineResource) \
                            or issubclass(objekt, ModelResource):

                        v1_api.register(objekt())

                        if settings.DEBUG:
                            LOGGER.info('Automatically registered '
                                        '%(module_name)s.%(class_name)s '
                                        'in the global API.'
                                        % {'module_name': module_name,
                                           'class_name': objekt_name})

                except TypeError, e:
                    if not 'issubclass() arg 1 must be a class' in str(e):
                        LOGGER.exception('Exception while determining subclass '
                                         'of %s.%s.', module_name, objekt_name)

                except Exception:
                    LOGGER.exception('Exception while determining subclass '
                                     'of %s.%s.', module_name, objekt_name)
