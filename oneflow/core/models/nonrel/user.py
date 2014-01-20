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

import sys
import logging

from random import randint

from celery import task
from constance import config

from pymongo.errors import DuplicateKeyError

from mongoengine import Q, Document, NULLIFY, CASCADE, PULL
from mongoengine.fields import (IntField, StringField, URLField,
                                BooleanField, ListField, ReferenceField)
from mongoengine.errors import NotUniqueError

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils.translation import ugettext_lazy as _

from ....base.fields import IntRedisDescriptor

from .common import DocumentHelperMixin
from .preferences import Preferences

LOGGER     = logging.getLogger(__name__)
DjangoUser = get_user_model()


__all__ = (
    'user_post_create_task',
    'User', 'Group',
    'user_all_articles_count_default',
    'user_unread_articles_count_default',
    'user_starred_articles_count_default',
    'user_bookmarked_articles_count_default',
    'user_archived_articles_count_default',

    'user_fun_articles_count_default',
    'user_fact_articles_count_default',
    'user_number_articles_count_default',
    'user_analysis_articles_count_default',
    'user_quote_articles_count_default',
    'user_knowhow_articles_count_default',
    'user_rules_articles_count_default',
    'user_prospective_articles_count_default',
    'user_knowledge_articles_count_default',
)


def user_django_user_random_default():
    """ 20130731: unused function but I keep this code for random()-related
        and future use. """

    count = 1

    while count:
        random_int = randint(-sys.maxint - 1, -1)

        try:
            User.objects.get(django_user=random_int)

        except User.DoesNotExist:
            return random_int

        else:
            count += 1
            if count == 10:
                LOGGER.warning(u'user_django_user_random_default() is starting '
                               u'to slow down things (more than 10 cycles to '
                               u' generate a not-taken random ID)…')


# ————————————————————————————————————————————————————————————————— Permissions
#                                                    (common to User and Group)
#
# NOTE: as of 20131031, these MongoDB permissions have been replaced by the
#       standard Django permissions. They are less flexible (eg. cannot query
#       permissions of one object on another, but just a global can_… perm),
#       but very easy to get in templates via the official Django context
#       processor. As this is all we need today, I don't continue with the
#       following idea. But it could still be useful one day, thus I keep
#       the code.
#
# class ReadPermissions(EmbeddedDocument):
#     full_text = BooleanField(default=False,
#                              verbose_name=_(u'Can read full-text articles?'))
#     def __unicode__(self):
#         return u'ReadPermissions: full_text=%s' % (self.full_text)
# class Permissions(EmbeddedDocument):
#     read = EmbeddedDocumentField(ReadPermissions, default=ReadPermissions,
#                                  verbose_name=_(u'Read-related permissions'))


def user_all_articles_count_default(user):

    return user.reads.count()


def user_unread_articles_count_default(user):

    return user.reads.filter(is_read__ne=True).count()


def user_starred_articles_count_default(user):

    return user.reads.filter(is_starred=True).count()


def user_archived_articles_count_default(user):

    return user.reads.filter(is_archived=True).count()


def user_bookmarked_articles_count_default(user):

    return user.reads.filter(is_bookmarked=True).count()


def user_fact_articles_count_default(user):

    return user.reads.filter(is_fact=True).count()


def user_number_articles_count_default(user):

    return user.reads.filter(is_number=True).count()


def user_analysis_articles_count_default(user):

    return user.reads.filter(is_analysis=True).count()


def user_quote_articles_count_default(user):

    return user.reads.filter(is_quote=True).count()


def user_prospective_articles_count_default(user):

    return user.reads.filter(is_prospective=True).count()


def user_knowhow_articles_count_default(user):

    return user.reads.filter(is_knowhow=True).count()


def user_knowledge_articles_count_default(user):

    return user.reads.filter(is_knowledge=True).count()


def user_rules_articles_count_default(user):

    return user.reads.filter(is_rules=True).count()


def user_fun_articles_count_default(user):

    return user.reads.filter(is_fun=True).count()


@task(name='User.post_create', queue='high')
def user_post_create_task(user_id, *args, **kwargs):

    user = User.objects.get(id=user_id)
    return user.post_create_task(*args, **kwargs)


class User(Document, DocumentHelperMixin):

    # Attributes synchronized between the Django User class and this one.
    SYNCHRONIZED_ATTRS = ('is_staff', 'is_superuser',
                          'first_name', 'last_name',
                          'username')

    django_user = IntField(unique=True)
    username    = StringField()
    first_name  = StringField()
    last_name   = StringField()
    avatar_url  = URLField()
    preferences_data = ReferenceField(Preferences,
                                      reverse_delete_rule=NULLIFY)

    #
    # disabled on 20131031. Kept commented for future use/reference
    #   (there is unused data for some users in the production DB)
    #
    # permissions  = EmbeddedDocumentField(Permissions, default=Permissions,
    #                                      verbose_name=_(u'User Permissions'),
    #                                      help_text=_(u'NOTE: any user will '
    #                                                  u'benefit the permissions ' # NOQA
    #                                                  u'of its groups if they '
    #                                                  u'are more permissive '
    #                                                  u'than his/her current '
    #                                                  u'permissions.'))

    is_superuser = BooleanField(default=False, verbose_name=_(u'Staff member'),
                                help_text=_(u'The user has staff permissions '
                                            u'(see Django documentation).'))
    is_staff     = BooleanField(default=False, verbose_name=_(u'Superuser'),
                                help_text=_(u'The user has super user related '
                                            u'permissions (see Django doc.).'))

    friends     = ListField(ReferenceField('self'), verbose_name=_(u'Friends'))

    address_book = ListField(StringField(), verbose_name=_(u'Address book'))

    all_articles_count = IntRedisDescriptor(
        attr_name='u.aa_c', default=user_all_articles_count_default,
        set_default=True, min_value=0)

    unread_articles_count = IntRedisDescriptor(
        attr_name='u.ua_c', default=user_unread_articles_count_default,
        set_default=True, min_value=0)

    starred_articles_count = IntRedisDescriptor(
        attr_name='u.sa_c', default=user_starred_articles_count_default,
        set_default=True, min_value=0)

    archived_articles_count = IntRedisDescriptor(
        attr_name='u.ra_c',
        default=user_archived_articles_count_default,
        set_default=True, min_value=0)

    bookmarked_articles_count = IntRedisDescriptor(
        attr_name='u.ba_c',
        default=user_bookmarked_articles_count_default,
        set_default=True, min_value=0)

    # ———————————————————————————————————————————————————————— Watch attributes

    fact_articles_count = IntRedisDescriptor(
        attr_name='u.fa_c',
        default=user_fact_articles_count_default,
        set_default=True, min_value=0)

    number_articles_count = IntRedisDescriptor(
        attr_name='u.na_c',
        default=user_number_articles_count_default,
        set_default=True, min_value=0)

    analysis_articles_count = IntRedisDescriptor(
        attr_name='u.ya_c',
        default=user_analysis_articles_count_default,
        set_default=True, min_value=0)

    quote_articles_count = IntRedisDescriptor(
        attr_name='u.qa_c',
        default=user_quote_articles_count_default,
        set_default=True, min_value=0)

    prospective_articles_count = IntRedisDescriptor(
        attr_name='u.pa_c',
        default=user_prospective_articles_count_default,
        set_default=True, min_value=0)

    rules_articles_count = IntRedisDescriptor(
        attr_name='u.ra_c',
        default=user_rules_articles_count_default,
        set_default=True, min_value=0)

    knowhow_articles_count = IntRedisDescriptor(
        attr_name='u.ka_c',
        default=user_knowhow_articles_count_default,
        set_default=True, min_value=0)

    knowledge_articles_count = IntRedisDescriptor(
        attr_name='u.oa_c',
        default=user_knowledge_articles_count_default,
        set_default=True, min_value=0)

    fun_articles_count = IntRedisDescriptor(
        attr_name='u.la_c',
        default=user_fun_articles_count_default,
        set_default=True, min_value=0)

    @property
    def relations(self):
        """ Meant to generate a list of choices suitable
            for a Django form ``choices`` argument. """

        for friend in self.friends:
            # MongoDB ID, full name or username
            yield (friend.id, friend.display_name)

        for contact in self.address_book:
            try:
                full_name, email = contact.rsplit(u' ', 1)

            except:
                # We have only the email.
                email     = contact
                full_name = contact

            yield email, full_name

    @property
    def has_content(self):

        return self.all_articles_count > 0 or [
            s for s in self.open_subscriptions if not s.feed.is_internal
        ]

    @property
    def has_contacts(self):

        return len(self.address_book)

    @property
    def preferences(self):
        if self.preferences_data is None:
            self.preferences_data = Preferences().save()
            self.save()

        return self.preferences_data

    @property
    def django(self):
        """ Cached property that returns the PostgreSQL counterpart
            of the current MongoDB user account. """
        try:
            return self.__django_user__

        except AttributeError:
            self.__django_user__ = DjangoUser.objects.get(id=self.django_user)
            return self.__django_user__

    def __unicode__(self):
        return u'%s #%s (Django ID: %s)' % (self.username or u'<UNKNOWN>',
                                            self.id, self.django_user)

    @property
    def is_staff_or_superuser_and_enabled(self):
        return ((self.is_staff or self.is_superuser)
                and self.preferences.staff.super_powers_enabled
                and config.STAFF_HAS_FULL_ACCESS)

    # def has_permission(self, permission, **kwargs):
    #     if self.is_staff_or_superuser_and_enabled:
    #         # Staff and super users always have all permissions, except when
    #         # they disable their super powers for demonstration purposes. In
    #         # this case, the models/views/templates should test .is_superuser
    #         # or .is_staff manually for emergency permissions.
    #         return True
    #     try:
    #         try:
    #             # first, see if we have a dedicated method for the permission.
    #             # Methods are used to combine permissions into meta-perms or
    #             # to test permissions on given objects for fine grained ones.
    #             return getattr(self, 'has_permission__'
    #                            + permission.replace(u'.', u'__'))(**kwargs)
    #         except AttributeError:
    #             # Second: no dedicated method, try
    #             # the traditional boolean permission.
    #             base, sub = permission.split(u'.')
    #             return getattr(getattr(self.permissions, base), sub)
    #     except:
    #         LOGGER.exception(u'Could not determine `%s` permission of user %s ' # NOQA
    #                          u'on %s.', permission, self, kwargs)
    #     return False

    def get_full_name(self):

        if self.first_name or self.last_name:
            return u'%s %s' % (self.first_name, self.last_name)

        return self.username

    @property
    def display_name(self):

        if self.firstname or self.lastname:
            return u'{0} {1} @{2}'.format(self.firstname,
                                          self.lastname,
                                          self.username)

        return u'@{0}'.format(self.username)

    @classmethod
    def signal_post_save_handler(cls, sender, document,
                                 created=False, **kwargs):

        user = document

        if created:
            if user._db_name != settings.MONGODB_NAME_ARCHIVE:
                user_post_create_task.delay(user.id)
                pass

        else:
            if user._db_name != settings.MONGODB_NAME_ARCHIVE:

                django_user   = user.django
                update_fields = []

                for attr in User.SYNCHRONIZED_ATTRS:
                    current_value = getattr(user, attr)
                    if getattr(django_user, attr) != current_value:
                        setattr(django_user, attr, current_value)
                        update_fields.append(attr)

                # The Django doc states that if ``update_fields`` is empty,
                # the save is avoided. No need for "if update_fields", then.
                django_user.save(update_fields=update_fields,
                                 # Avoid the back-synchronization cycle.
                                 mongo_django_sync=False)

    @classmethod
    def signal_pre_save_post_validation_handler(cls, sender,
                                                document, **kwargs):

        if document.preferences is None:
            document.preferences = Preferences().save()

    def post_create_task(self):
        """ Method meant to be run from a celery task. """

        django_user = DjangoUser.objects.get(id=self.django_user)
        self.username = django_user.username
        self.last_name = django_user.last_name
        self.first_name = django_user.first_name
        self.save()

    @property
    def nofolder_subscriptions(self):

        return [
            s for s in self.subscriptions.filter(
                Q(folders__exists=False) | Q(folders__size=0)
            )
            if not s.feed.is_internal
        ]

    @property
    def open_subscriptions(self):

        # NOTE: self.subscriptions is defined
        # in nonrel.subscription to avoid import loop.
        return [s for s in self.subscriptions if not s.feed.closed]

    @property
    def closed_subscriptions(self):

        # NOTE: self.subscriptions is defined
        # in nonrel.subscription to avoid import loop.
        return [s for s in self.subscriptions if s.feed.closed]

    @property
    def nofolder_open_subscriptions(self):

        return [s for s in self.nofolder_subscriptions if not s.feed.closed]

    @property
    def nofolder_closed_subscriptions(self):

        return [s for s in self.nofolder_subscriptions if s.feed.closed]


def __mongo_user(self):
    try:
        return self.__mongo_user_cache__

    except:
        try:
            self.__mongo_user_cache__ = User.objects.get(django_user=self.id)

        except User.DoesNotExist:
            try:
                self.__mongo_user_cache__ = User(django_user=self.id).save()

            except (NotUniqueError, DuplicateKeyError):
                # Woops. Race condition? On a user?? Weird.

                self.__mongo_user_cache__ = User.objects.get(
                    django_user=self.id)

        return self.__mongo_user_cache__


# Override the Django save() method so that MongoDB and PostgreSQL are
# synchronized on specific fields, without producing post-save signal
# cycles in either direction.
def DjangoUser__save__method(self, *args, **kwargs):

    back_sync = kwargs.pop('mongo_django_sync', True)

    result = super(self.__class__, self).save(*args, **kwargs)

    if back_sync:
        params = dict(('set__' + attr, getattr(self, attr))
                      for attr in User.SYNCHRONIZED_ATTRS)

        # In the PostgreSQL > MongoDB direction, the cycle is avoided
        # with a signal bypass. We write directly the new data in the
        # DB and trigger a reload. This is at the expense of potentially
        # useless writes, but modifying users in the Django admin occurs
        # very infrequently anyway so the real cost is nothing.
        self.mongo.update(**params)
        self.mongo.safe_reload()

    return result


# Auto-link the DjangoUser to the mongo one
DjangoUser.mongo = property(__mongo_user)
DjangoUser.save  = DjangoUser__save__method


class Group(Document, DocumentHelperMixin):
    name           = StringField(unique_with='creator')
    is_system      = BooleanField(default=False,
                                  verbose_name=_(u'System group?'))
    creator        = ReferenceField('User', reverse_delete_rule=CASCADE)
    administrators = ListField(ReferenceField('User',
                               reverse_delete_rule=PULL))
    members = ListField(ReferenceField('User',
                        reverse_delete_rule=PULL))
    guests  = ListField(ReferenceField('User',
                        reverse_delete_rule=PULL))

    #
    # disabled on 20131031. Kept commented for future use/reference
    #   (there is unused data for some users in the production DB)
    #
    # permissions = EmbeddedDocumentField(Permissions, default=Permissions,
    #                                     verbose_name=_(u'Group permissions'))
    #
    # def has_permission(self, permission, **kwargs):
    #     """ This method is copied after `User.has_permission()`, but a little
    #         different internally to match Group specificities. """
    #     if self.is_system:
    #         # TODO: this is probably a bad idea to mimic
    #         #       user behaviour here. Please review.
    #         return True
    #     try:
    #         try:
    #             return getattr(self, 'has_permission__'
    #                            + permission.replace(u'.', u'__'))(**kwargs)
    #         except AttributeError:
    #             # Second: no dedicated method, try
    #             # the traditional boolean permission.
    #             base, sub = permission.split(u'.')
    #             return getattr(getattr(self.permissions, base), sub)
    #     except:
    #         LOGGER.exception(u'Could not determine `%s` permission of '
    #                          u'group %s on %s.', permission, self, kwargs)
    #     return False
