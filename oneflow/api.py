# -*- coding: utf-8 -*-

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

            for objekt_name in dir(apimod):
                objekt = getattr(apimod, objekt_name)
                try:
                    if issubclass(objekt, MongoEngineResource) \
                            or issubclass(objekt, ModelResource):
                        v1_api.register(objekt())
                        LOGGER.info('Automatically registered '
                                    '%(module_name)s.%(class_name)s '
                                    'in the global API.'
                                    % {'module_name': module_name,
                                    'class_name': objekt_name})

                except TypeError:
                    # Not a class. Forget it.
                    pass

                except Exception:
                    LOGGER.warning('Exception while determining subclass '
                                   'of %s.%s.', module_name, objekt_name)
