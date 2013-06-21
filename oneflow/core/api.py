# -*- coding: utf-8 -*-

import logging

from tastypie_mongoengine import resources

from .models.nonrel import Subscription
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
