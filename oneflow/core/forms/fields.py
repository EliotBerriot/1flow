# -*- coding: utf-8 -*-
"""
    Copyright 2013-2014 Olivier Cortès <oc@1flow.io>

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

import logging

from django import forms
from django_select2.fields import HeavySelect2TagField

LOGGER = logging.getLogger(__name__)


class OnlyNameChoiceField(forms.ModelChoiceField):
    """ In forms, we need something much simpler
        than the `__unicode__()` output. """

    def label_from_instance(self, obj):

        root = obj.owner.root_folder

        # OMG. Please don't do this anywhere else. How ugly it is.
        if obj.parent == root:
            prefix = u''
        elif obj.parent.parent == root:
            prefix = u' ' * 8
        elif obj.parent.parent.parent == root:
            prefix = u' ' * 16
        elif obj.parent.parent.parent.parent == root:
            prefix = u' ' * 24
        elif obj.parent.parent.parent.parent.parent == root:
            prefix = u' ' * 32
        elif obj.parent.parent.parent.parent.parent.parent == root:
            prefix = u' ' * 40
        elif obj.parent.parent.parent.parent.parent.parent.parent == root:
            prefix = u' ' * 48
        else:
            prefix = u' ' * 56

        return prefix + obj.name


class OnlyNameMultipleChoiceField(forms.ModelMultipleChoiceField):
    """ In forms, we need something much simpler
        than the `__unicode__()` output. """

    def label_from_instance(self, obj):

        try:
            root = obj.owner.root_folder

        except AttributeError:
            return obj.name

        # OMG. Please don't do this anywhere else. How ugly it is.
        if obj.parent == root:
            prefix = u''
        elif obj.parent.parent == root:
            prefix = u' ' * 8
        elif obj.parent.parent.parent == root:
            prefix = u' ' * 16
        elif obj.parent.parent.parent.parent == root:
            prefix = u' ' * 24
        elif obj.parent.parent.parent.parent.parent == root:
            prefix = u' ' * 32
        elif obj.parent.parent.parent.parent.parent.parent == root:
            prefix = u' ' * 40
        elif obj.parent.parent.parent.parent.parent.parent.parent == root:
            prefix = u' ' * 48
        else:
            prefix = u' ' * 56

        return prefix + obj.name


class UsersMultipleAndTagField(HeavySelect2TagField):
    """ In forms, we need something much simpler
        than the `__unicode__()` output. """

    def __init__(self, *args, **kwargs):

        self.owner = kwargs.pop('owner')

        super(UsersMultipleAndTagField, self).__init__(*args, **kwargs)

    def create_new_value(self, value):

        LOGGER.info(u'CREATING new value from %s in %s address_book',
                    value, self.owner.username)

        value = value.strip()

        things = value.split()

        # Is this an already existing 1flow user that wants to be created???
        if things[-1].startswith(u'@'):
            raise RuntimeError(u'BAD %s' % value)

        if value not in (None, u''):
            self.owner.update(add_to_set__address_book=value)

            LOGGER.info(u'ADDED %s to %s address_book',
                        value, self.owner.username)
            #self.owner.safe_reload()
