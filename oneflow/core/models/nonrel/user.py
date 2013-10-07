# -*- coding: utf-8 -*-

import sys
import logging

from random import randint

from celery import task

from pymongo.errors import DuplicateKeyError

from mongoengine import Q, Document, NULLIFY, CASCADE, PULL
from mongoengine.fields import (IntField, StringField, URLField,
                                ListField, ReferenceField)
from mongoengine.errors import NotUniqueError

from django.conf import settings
from django.contrib.auth import get_user_model

from ....base.fields import IntRedisDescriptor

from .common import DocumentHelperMixin
from .preferences import Preferences

LOGGER     = logging.getLogger(__name__)
DjangoUser = get_user_model()


__all__ = ('user_post_create_task', 'User', 'Group', )


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


@task(name='User.post_create', queue='high')
def user_post_create_task(user_id, *args, **kwargs):

    user = User.objects.get(id=user_id)
    return user.post_create_task(*args, **kwargs)


class User(Document, DocumentHelperMixin):
    django_user = IntField(unique=True)
    username    = StringField()
    first_name  = StringField()
    last_name   = StringField()
    avatar_url  = URLField()
    preferences_data = ReferenceField(Preferences,
                                      reverse_delete_rule=NULLIFY)

    has_content = IntRedisDescriptor(
        attr_name='u.h_c', set_default=True,
        default='oneflow.core.models.nonrel.read.user_has_content_default')

    @property
    def preferences(self):
        if self.preferences_data is None:
            self.preferences_data = Preferences().save()
            self.save()

        return self.preferences_data

    def __unicode__(self):
        return u'%s #%s (Django ID: %s)' % (self.username or u'<UNKNOWN>',
                                            self.id, self.django_user)

    def get_full_name(self):
        return '%s %s' % (self.first_name, self.last_name)

    @classmethod
    def signal_post_save_handler(cls, sender, document,
                                 created=False, **kwargs):

        user = document

        if created:
            if user._db_name != settings.MONGODB_NAME_ARCHIVE:
                user_post_create_task.delay(user.id)
                pass

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

    def check_subscriptions(self, force=False):
        """
            .. note:: running this method from the feeds is more database
                friendly because the feeds will compute their articles
                QuerySet once and for all the subscriptions.
        """

        if not force:
            LOGGER.info(u'This method is very costy and should not be needed '
                        u'in normal conditions. Please call it with '
                        u'`force=True` if you are sure you want to run it.')
            return

        reads     = 0
        failed    = 0
        unreads   = 0
        missing   = 0
        rechecked = 0

        for subscription in self.subscriptions:
            smissing, srecheck, sreads, sunreads, sfailed = \
                subscription.check_reads(force)

            reads     += sreads
            failed    += sfailed
            missing   += smissing
            unreads   += sunreads
            rechecked += srecheck

            subscription.pre_compute_cached_descriptors()

        LOGGER.info(u'Checked user #%s with %s subscriptions. '
                    u'Totals: %s/%s non-existing/re-checked reads, '
                    u'%s/%s read/unread and %s not created.', self.id,
                    self.subscriptions.count(),
                    missing, rechecked, reads, unreads, failed)

    @property
    def nofolder_subscriptions(self):

        return self.subscriptions.filter(
            Q(folders__exists=False) | Q(folders__size=0))

    @property
    def open_subscriptions(self):

        # NOTE: self.subscriptions is defined
        # in nonrel.subscription to avoid import loop.
        return [s for s in self.subscriptions if not s.feed.closed]

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

# Auto-link the DjangoUser to the mongo one
DjangoUser.mongo = property(__mongo_user)


class Group(Document, DocumentHelperMixin):
    name = StringField(unique_with='creator')
    creator = ReferenceField('User', reverse_delete_rule=CASCADE)
    administrators = ListField(ReferenceField('User',
                               reverse_delete_rule=PULL))
    members = ListField(ReferenceField('User',
                        reverse_delete_rule=PULL))
    guests = ListField(ReferenceField('User',
                       reverse_delete_rule=PULL))
