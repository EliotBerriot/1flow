# -*- coding: utf-8 -*-

import logging

from tastypie_mongoengine import resources
from tastypie.resources import ALL

from .models.nonrel import Subscription, Read
from ..base.api import common_authentication, UserObjectsOnlyAuthorization

LOGGER = logging.getLogger(__name__)


class SubscriptionResource(resources.MongoEngineResource):
    class Meta:
        queryset = Subscription.objects.all()

        # Ember-data expect the following 2 directives
        always_return_data = True
        allowed_methods    = ('get', 'post', 'put', 'delete')

        # These are specific to 1flow functionnals.
        authentication     = common_authentication
        authorization      = UserObjectsOnlyAuthorization()

        #authorization = authorization.Authorization()


class ReadResource(resources.MongoEngineResource):
    class Meta:
        queryset = Read.objects.all()

        # Ember-data expect the following 2 directives
        always_return_data = True
        allowed_methods    = ('get', 'post', 'put', 'delete')
        collection_name = 'reads'
        resource_name = 'read'
        filtering = {'id': ALL, }
        ordering = ALL
        # These are specific to 1flow functionnals.
        #authentication     = common_authentication
        #authorization      = UserObjectsOnlyAuthorization()

        #authorization = authorization.Authorization()


__all__ = ('SubscriptionResource', 'ReadResource', )
