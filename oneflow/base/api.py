# -*- coding: utf-8 -*-

import logging

from tastypie.authorization import Authorization  # , DjangoAuthorization
from tastypie.exceptions import Unauthorized
from tastypie.authentication import (MultiAuthentication,
                                     SessionAuthentication,
                                     ApiKeyAuthentication)


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

        return bundle.obj.user == user or user.is_staff or user.is_superuser

    def create_list(self, object_list, bundle):
        # Assuming their auto-assigned to ``user``.
        return object_list

    def create_detail(self, object_list, bundle):
        user = bundle.request.user

        return bundle.obj.user == user or user.is_staff or user.is_superuser

    def update_list(self, object_list, bundle):
        allowed = []

        user = bundle.request.user

        # Since they may not all be saved, iterate over them.
        for obj in object_list:
            if obj.user == user or user.is_staff or user.is_superuser:
                allowed.append(obj)

        return allowed

    def update_detail(self, object_list, bundle):
        return bundle.obj.user == bundle.request.user

    def delete_list(self, object_list, bundle):
        # Sorry user, no deletes for you!
        raise Unauthorized("Sorry, no deletes.")

    def delete_detail(self, object_list, bundle):
        raise Unauthorized("Sorry, no deletes.")
