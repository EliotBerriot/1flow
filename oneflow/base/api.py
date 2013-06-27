# -*- coding: utf-8 -*-

import logging

from tastypie.authorization import Authorization  # , DjangoAuthorization
from tastypie.exceptions import Unauthorized
from tastypie.authentication import (MultiAuthentication,
                                     SessionAuthentication,
                                     ApiKeyAuthentication)
from tastypie.resources import ModelResource
#from tastypie import fields

from django.contrib.auth import get_user_model


LOGGER = logging.getLogger(__name__)

common_authentication = MultiAuthentication(SessionAuthentication(),
                                            ApiKeyAuthentication())


class UserObjectsOnlyAuthorization(Authorization):
    """ Basic Authorization

        cf. http://django-tastypie.readthedocs.org/en/latest/authorization.html
    """

    def read_list(self, object_list, bundle):
        user = bundle.request.user

        if user.is_staff or user.is_superuser:
            return object_list

        return object_list.filter(user=user)

    def read_detail(self, object_list, bundle):
        # Is the requested object owned by the user?

        user = bundle.request.user

        try:
            return bundle.obj.user == user or user.is_staff or user.is_superuser

        except AttributeError:
            return bundle.obj == user or user.is_staff or user.is_superuser

    def create_list(self, object_list, bundle):
        # Assuming their auto-assigned to ``user``.
        return object_list

    def create_detail(self, object_list, bundle):
        """ TODO: make this method more granular for some types of objects. """

        user = bundle.request.user

        try:
            return bundle.obj.user == user or user.is_staff or user.is_superuser

        except AttributeError:
            return user.is_staff or user.is_superuser

    def update_list(self, object_list, bundle):
        allowed = []

        user = bundle.request.user

        # Since they may not all be saved, iterate over them.
        for obj in object_list:
            try:
                object_user = obj.user

            except AttributeError:
                object_user = obj

            if object_user == user or user.is_staff or user.is_superuser:
                allowed.append(obj)

        return allowed

    def update_detail(self, object_list, bundle):
        try:
            return bundle.obj.user == bundle.request.user

        except AttributeError:
            return bundle.obj == bundle.request.user

    def delete_list(self, object_list, bundle):
        """ TODO: implement staff/superuser. """
        # Sorry user, no deletes for you!
        raise Unauthorized("Sorry, no deletes.")

    def delete_detail(self, object_list, bundle):
        """ TODO: implement staff/superuser. """
        raise Unauthorized("Sorry, no deletes.")


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


__all__ = ('UserObjectsOnlyAuthorization', 'EmberMeta',
           'common_authentication', 'UserResource', )
