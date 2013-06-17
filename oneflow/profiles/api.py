# -*- coding: utf-8 -*-

import logging

from django.contrib.auth import get_user_model

from tastypie.resources import ModelResource
from tastypie import fields

from ..base.api import common_authentication, UserObjectsOnlyAuthorization
from .models import UserProfile

LOGGER = logging.getLogger(__name__)
User = get_user_model()


class EmberMeta:
    # Ember-data expect the following 2 directives
    always_return_data = True
    allowed_methods    = ('get', 'post', 'put', 'delete')

    # These are specific to 1flow functionnals.
    authentication     = common_authentication
    authorization      = UserObjectsOnlyAuthorization()


class UserResource(ModelResource):

    class Meta(EmberMeta):
        queryset = User.objects.all()
        resource_name = 'user'


class UserProfileResource(ModelResource):

    # NOTE: "user" won't work because it's a OneToOne field in DJango.
    # We need "user_id". See http://stackoverflow.com/a/15609667/654755
    user_id = fields.ForeignKey(UserResource, 'user')

    class Meta(EmberMeta):
        queryset = UserProfile.objects.all()
        resource_name = 'user_profile'
