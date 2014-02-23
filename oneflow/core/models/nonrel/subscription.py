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

from celery import task

from pymongo.errors import DuplicateKeyError

from mongoengine import Document, CASCADE, PULL
from mongoengine.fields import (StringField, ListField, ReferenceField,
                                GenericReferenceField, DBRef)
from mongoengine.errors import NotUniqueError

from cache_utils.decorators import cached

from django.conf import settings
from django.utils.translation import ugettext_lazy as _, ugettext as __

from ....base.fields import IntRedisDescriptor
from ....base.utils.dateutils import (timedelta, today, combine,
                                      now, time)  # , make_aware, utc)

from .common import DocumentHelperMixin, CACHE_ONE_DAY
from .folder import Folder
from .user import User
from .feed import Feed

LOGGER = logging.getLogger(__name__)


__all__ = ('subscription_post_create_task',
           'subscription_post_delete_task',
           'subscription_check_reads',
           'subscription_mark_all_read_in_database',
           'Subscription',

           # Make these accessible to compute them from `DocumentHelperMixin`.
           'subscription_all_articles_count_default',
           'subscription_unread_articles_count_default',
           'subscription_starred_articles_count_default',
           'subscription_archived_articles_count_default',
           'subscription_bookmarked_articles_count_default',

           # This one will be picked up by `Read` as an instance method.
           'generic_check_subscriptions_method',
           )


def subscription_all_articles_count_default(subscription):

    return subscription.reads.count()


def subscription_unread_articles_count_default(subscription):

    return subscription.reads.filter(is_read__ne=True).count()


def subscription_starred_articles_count_default(subscription):

    return subscription.reads.filter(is_starred=True).count()


def subscription_archived_articles_count_default(subscription):

    return subscription.reads.filter(is_archived=True).count()


def subscription_bookmarked_articles_count_default(subscription):

    return subscription.reads.filter(is_bookmarked=True).count()


@task(name='Subscription.post_create', queue='high')
def subscription_post_create_task(subscription_id, *args, **kwargs):

    subscription = Subscription.objects.get(id=subscription_id)
    return subscription.post_create_task(*args, **kwargs)


@task(name='Subscription.post_delete', queue='clean')
def subscription_post_delete_task(subscription, *args, **kwargs):
    """ HEADS UP: we get a real object (not an ID) as first argument.
        Without this, we have no way to get any reference to the
        deleted instance.

        This is an heavy operation for the database, that can be long.
        Thus done in a task, not in a `reverse_delete_rule` nor directly
        in the signal handler.
    """

    subscription.reads.update(pull__subscriptions=subscription)


@task(name='Subscription.mark_all_read_in_database', queue='low')
def subscription_mark_all_read_in_database(subscription_id, *args, **kwargs):

    subscription = Subscription.objects.get(id=subscription_id)
    return subscription.mark_all_read_in_database(*args, **kwargs)


@task(name='Subscription.check_reads', queue='low')
def subscription_check_reads(subscription_id, *args, **kwargs):

    subscription = Subscription.objects.get(id=subscription_id)
    return subscription.check_reads(*args, **kwargs)


class Subscription(Document, DocumentHelperMixin):
    feed = ReferenceField('Feed', reverse_delete_rule=CASCADE)
    user = ReferenceField('User', unique_with='feed',
                          reverse_delete_rule=CASCADE)

    # allow the user to rename the field in its own subscription
    name = StringField(verbose_name=_(u'Name'))

    # TODO: convert to UserTag to use ReferenceField and reverse_delete_rule.
    tags = ListField(GenericReferenceField(),
                     default=list, verbose_name=_(u'Tags'),
                     help_text=_(u'Tags that will be applied to new reads in '
                                 u'this subscription.'))

    folders = ListField(ReferenceField(Folder, reverse_delete_rule=PULL),
                        verbose_name=_(u'Folders'), default=list,
                        help_text=_(u'Folder(s) in which this subscription '
                                    u'appears.'))

    all_articles_count = IntRedisDescriptor(
        attr_name='s.aa_c', default=subscription_all_articles_count_default,
        set_default=True, min_value=0)

    unread_articles_count = IntRedisDescriptor(
        attr_name='s.ua_c', default=subscription_unread_articles_count_default,
        set_default=True, min_value=0)

    starred_articles_count = IntRedisDescriptor(
        attr_name='s.sa_c', default=subscription_starred_articles_count_default,
        set_default=True, min_value=0)

    archived_articles_count = IntRedisDescriptor(
        attr_name='s.ra_c',
        default=subscription_archived_articles_count_default,
        set_default=True, min_value=0)

    bookmarked_articles_count = IntRedisDescriptor(
        attr_name='s.ba_c',
        default=subscription_bookmarked_articles_count_default,
        set_default=True, min_value=0)

    meta = {
        'indexes': [
            'user',
            'feed',
            'folders',
        ]
    }

    def __unicode__(self):
        return _(u'{0}+{1} (#{2})').format(
            self.user.username, self.feed.name, self.id)

    @classmethod
    def signal_post_save_handler(cls, sender, document,
                                 created=False, **kwargs):

        subscription = document

        if created:
            if subscription._db_name != settings.MONGODB_NAME_ARCHIVE:
                subscription_post_create_task.delay(subscription.id)

    def post_create_task(self):
        """ Method meant to be run from a celery task. """

        # The content of this method is done in subscribe_user_to_feed()
        # to avoid more-than-needed write operations on the database.
        pass

    @classmethod
    def signal_post_delete_handler(cls, sender, document, **kwargs):

        subscription = document

        if subscription._db_name != settings.MONGODB_NAME_ARCHIVE:

            # HEADS UP: we don't pass an ID, else the .get() fails
            # in the task for a good reason: the subscription doesn't
            # exist anymore.
            subscription_post_delete_task.delay(subscription)

    @classmethod
    def subscribe_user_to_feed(cls, user, feed, name=None,
                               force=False, background=False):

        try:
            subscription = cls(user=user, feed=feed).save()

        except (NotUniqueError, DuplicateKeyError):
            if not force:
                LOGGER.info(u'User %s already subscribed to feed %s.',
                            user, feed)
                return cls.objects.get(user=user, feed=feed)

        else:
            subscription.name = name or feed.name
            subscription.tags = feed.tags[:]
            subscription.save()

        if background:
            # 'True' is for the 'force' argument.
            subscription_check_reads.delay(subscription.id, True)

        else:
            subscription.check_reads(force=True)

        LOGGER.info(u'Subscribed %s to %s via %s.', user, feed, subscription)

        return subscription

    @property
    def has_unread(self):

        # We need a boolean value for accurate template caching.
        return self.unread_articles_count != 0

    @property
    def is_closed(self):

        return self.feed.closed

    def mark_all_read(self, latest_displayed_read=None):

        if self.unread_articles_count == 0:
            return

        # count = self.unread_articles_count

        # self.unread_articles_count = 0

        # for folder in self.folders:
        #     folder.unread_articles_count -= count

        # self.user.unread_articles_count -= count

        # Marking all read is not a database-friendly operation,
        # thus it's run via a task to be able to return now immediately,
        # with cache numbers updated.
        subscription_mark_all_read_in_database.delay(
            self.id, now() if latest_displayed_read is None
            #
            # TRICK: we use self.user.reads for 2 reasons:
            #       - avoid importing `Read`, which would create a loop.
            #       - in case of a folder/global initiated mark_all_read(),
            #         the ID can be one of a read in another subscription
            #         and in this case, self.reads.get() will fail.
            #
            else latest_displayed_read.date_created)

    def mark_all_read_in_database(self, prior_datetime):
        """ To avoid marking read the reads that could have been created
            between the task call and the moment it is effectively run,
            we define what to exactly mark as read with the datetime when
            the operation was done by the user.

            Also available as a task for background execution.

            .. note: the archived reads stay archived, whatever their
                read status is. No need to test this attribute.
        """

        # We touch only unread. This avoid altering the auto_read attribute
        # on reads that have been manually marked read by the user.
        params = {'is_read__ne': True, 'date_created__lte': prior_datetime}

        if self.user.preferences.read.bookmarked_marks_unread:
            # Let bookmarked reads stay unread.
            params['is_bookmarked__ne'] = True

        impacted_unread = self.reads.filter(**params)
        impacted_count  = impacted_unread.count()

        impacted_unread.update(set__is_read=True,
                               set__is_auto_read=True,
                               set__date_read=prior_datetime,
                               set__date_auto_read=prior_datetime)

        # If our caches are correctly computed, doing
        # one more full query just for this is too much.
        #
        #self.compute_cached_descriptors(unread=True)

        self.unread_articles_count -= impacted_count

        for folder in self.folders:
            folder.unread_articles_count -= impacted_count

        self.user.unread_articles_count -= impacted_count

    def check_reads(self, articles=None, force=False, extended_check=False):
        """ Also available as a task for background execution. """

        if not force:
            LOGGER.info(u'Subscription.check_reads() is very costy and should '
                        u'not be needed in normal conditions. Call it with '
                        u'`force=True` if you are sure you want to run it.')
            return

        yesterday = combine(today() - timedelta(days=1), time(0, 0, 0))
        is_older  = False
        my_now    = now()
        reads     = 0
        unreads   = 0
        failed    = 0
        missing   = 0
        rechecked = 0

        # When checking the subscription from its feed, allow optimising
        # the whole story by not querying the articles again for each
        # subscription. The feed will do the query once, and forward the
        # QuerySet to all subscriptions to be checked.

        if articles is None:
            articles = self.feed.good_articles.order_by('-id')

        for article in articles:
            #
            # NOTE: `is_good` is checked at a lower level in
            #       `self.create_read()` because the `is_good`
            #       status has nothing to do here with
            #       dates-only checks.
            #

            params = {}

            if is_older or article.date_published is None:
                params = {
                    'is_read':        True,
                    'is_auto_read':   True,
                    'date_read':      my_now,
                    'date_auto_read': my_now,
                }

            else:
                # As they are ordered by date, switching is_older to True will
                # avoid more date comparisons. MongoDB already did the job.
                if article.date_published < yesterday:

                    is_older = True

                    params = {
                        'is_read':        True,
                        'is_auto_read':   True,
                        'date_read':      my_now,
                        'date_auto_read': my_now,
                    }

                # implicit: else: pass
                # No params == all by default == is_read is False

            # The `create_read()` methods is defined
            # in `nonrel/read.py` to avoid an import loop.
            _, created = self.create_read(article, False, **params)

            if created:
                missing += 1

                if params.get('is_read', False):
                    reads += 1

                else:
                    unreads += 1

            elif created is False:
                rechecked += 1

                if extended_check:
                    try:
                        article.activate_reads()

                    except:
                        LOGGER.exception(u'Problem while activating reads '
                                         u'of Article #%s in Subscription '
                                         u'#%s.check_reads(), continuing '
                                         u'check.', article.id, self.id)

            else:
                failed += 1

        if missing or rechecked:
            #
            # TODO: don't recompute everything, just
            #    add or subscribe the changed counts.
            #
            self.compute_cached_descriptors(all=True, unread=True)

            for folder in self.folders:
                folder.compute_cached_descriptors(all=True, unread=True)

        LOGGER.info(u'Checked subscription #%s. '
                    u'%s/%s non-existing/re-checked, '
                    u'%s/%s read/unread and %s not created.',
                    self.id, missing, rechecked,
                    reads, unreads, failed)

        return missing, rechecked, reads, unreads, failed


# ————————————————————————————————————————————————————————— external properties
#                                            Defined here to avoid import loops


def Feed_subscriptions_property_get(self):

    return Subscription.objects(feed=self).no_cache()


def Folder_subscriptions_property_get(self):

    # No need to query on the user, it's already common to folder and
    # subscription. The "duplicate folder name" problem doesn't exist.
    return Subscription.objects(folders=self).no_cache()


def Folder_open_subscriptions_property_get(self):

    # No need to query on the user, it's already common to folder and
    # subscription. The "duplicate folder name" problem doesn't exist.
    return [s for s in Subscription.objects(folders=self).no_cache()
            if not s.feed.closed]


def User_subscriptions_property_get(self):
    """ “Normal” subscriptions, eg. not special (immutable) ones. """

    # Add all special feeds here.
    return self.all_subscriptions(feed__nin=[self.web_import_feed,
                                             self.sent_items_feed,
                                             self.received_items_feed])


def User_all_subscriptions_property_get(self):
    """ Really, all. Including special ones. """

    return Subscription.objects(user=self).no_cache()


def get_or_create_special_subscription(user, special_feed, feed_name):

    try:
        return user.all_subscriptions.get(feed=special_feed)

    except Subscription.DoesNotExist:

        #
        # NOTE: we use a shorter name than the feed's one.
        # The user doesn't need to see his/her own name in
        # the subscription title.
        #

        return Subscription.subscribe_user_to_feed(user=user,
                                                   feed=special_feed,
                                                   name=__(u'Imported items'),
                                                   background=True)


def User_received_items_subscription_property_get(self):

    return get_or_create_special_subscription(self, self.received_items_feed,
                                              __(u'Received items'))


def User_sent_items_subscription_property_get(self):

    return get_or_create_special_subscription(self, self.sent_items_feed,
                                              __(u'Sent items'))


#@cached(CACHE_ONE_DAY)
def User_web_import_subscription_property_get(self):

    return get_or_create_special_subscription(self, self.web_import_feed,
                                              __(u'Imported items'))


def User_subscriptions_by_folder_property_get(self):

    subscriptions = Subscription.objects(user=self).no_cache()
    by_folders    = {}

    for subscription in subscriptions:
        for folder in subscription.folders:
            if folder in by_folders:
                by_folders[folder].append(subscription)

            else:
                by_folders[folder] = [subscription]

    return by_folders


def generic_check_subscriptions_method(self, commit=True, extended_check=False):
    """ This one is used for `Read` and `User` classes. """

    # if not force:
    #     LOGGER.info(u'%s.check_subscriptions() is very costy and should '
    #                 u'not be needed in normal conditions. Call it with '
    #                 u'`force=True` if you are sure you want to run it.',
    #                 self.__class__.__name__)
    #     return

    to_keep       = []
    my_class_name = self.__class__.__name__

    for subscription in self.subscriptions:
        if isinstance(subscription, DBRef) or subscription is None:
            # We need to catch DBRef on its own.
            LOGGER.warning(u'Clearing dangling Subscription reference %s '
                           u'from %s %s. ', subscription.id if subscription
                           else u'`None`', my_class_name, self.id)

        elif isinstance(subscription, Subscription):

            # TODO: code a not-hard-coded way to do this test,
            #       eg. get the values via class attributes?
            if my_class_name == 'Feed':
                attrs_to_test = [(subscription.user, 'User')]

            elif my_class_name == 'User':
                attrs_to_test = [(subscription.feed, 'Feed')]

            else:
                # We are a Read.
                attrs_to_test = [(subscription.user, 'User'),
                                 (subscription.feed, 'Feed')]

            keep_it = True

            for attr_to_test, class_to_test in attrs_to_test:
                if isinstance(attr_to_test, DBRef) or attr_to_test is None:
                    LOGGER.warning(u'Clearing Subscription #%s from %s #%s, it '
                                   u'has a dangling reference to non-existing '
                                   u'%s #%s.', subscription.id,
                                   my_class_name, self.id, class_to_test,
                                   attr_to_test.id if attr_to_test
                                   else u'`None`')
                    keep_it = False
                    break

            if keep_it:
                to_keep.append(subscription)

        else:
            LOGGER.warning(u'Clearing strange Subscription reference %s '
                           u'from %s %s. ', subscription,
                           my_class_name, self.id)

    if len(to_keep) != self.subscriptions.count():
        self.subscriptions = to_keep

        if commit:
            self.save()
        # No need to update cached descriptors, they should already be ok…

    # avoid checking supbscriptions of a read, this will dead-loop if
    # Article.activate_reads(extended_check=True).
    if extended_check and my_class_name != 'Read':

        reads     = 0
        failed    = 0
        unreads   = 0
        missing   = 0
        rechecked = 0

        if my_class_name == 'Feed':
            articles = self.good_articles.order_by('-id')

        else:
            articles = None

        # Convert the subscriptions QuerySet to a list to avoid
        # "cursor #… not valid at server" on very long operations.
        subscriptions = [s for s in self.subscriptions]

        for subscription in subscriptions:
            try:
                smissing, srecheck, sreads, sunreads, sfailed = \
                    subscription.check_reads(articles, force=True,
                                             extended_check=True)
            except:
                # In case the subscription was unsubscribed during the
                # check operation, this is probably harmless.
                LOGGER.exception(u'Checking subscription #%s failed',
                                 subscription.id)

            else:
                reads     += sreads
                failed    += sfailed
                missing   += smissing
                unreads   += sunreads
                rechecked += srecheck

        LOGGER.info(u'Checked %s #%s with %s subscriptions%s. '
                    u'Totals: %s/%s non-existing/re-checked reads, '
                    u'%s/%s read/unread and %s not created.',
                    self.__class__.__name__, self.id,
                    self.subscriptions.count(),
                    u'' if articles is None
                    else (u'and %s articles' % articles.count()),
                    missing, rechecked, reads, unreads, failed)


Folder.subscriptions          = property(Folder_subscriptions_property_get)
Folder.open_subscriptions     = property(Folder_open_subscriptions_property_get)

Feed.subscriptions            = property(Feed_subscriptions_property_get)
Feed.check_subscriptions      = generic_check_subscriptions_method

User.subscriptions            = property(User_subscriptions_property_get)
User.all_subscriptions        = property(User_all_subscriptions_property_get)
User.check_subscriptions      = generic_check_subscriptions_method
User.subscriptions_by_folder  = property(
    User_subscriptions_by_folder_property_get)
User.web_import_subscription  = property(
    User_web_import_subscription_property_get)
User.sent_items_subscription  = property(
    User_sent_items_subscription_property_get)
User.received_items_subscription = property(
    User_received_items_subscription_property_get)
