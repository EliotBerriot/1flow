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
import operator
import feedparser

from celery import task

from pymongo.errors import DuplicateKeyError

from mongoengine import Document, Q, CASCADE
from mongoengine.fields import (StringField, BooleanField,
                                FloatField, DateTimeField,
                                ListField, ReferenceField,
                                GenericReferenceField, DBRef)
from mongoengine.errors import NotUniqueError, ValidationError

#from cache_utils.decorators import cached

from django.conf import settings
from django.utils.translation import ugettext_lazy as _, pgettext_lazy

from ....base.utils.dateutils import now, timedelta, naturaldelta

from .common import DocumentHelperMixin  # , CACHE_ONE_DAY

from .folder import Folder
from .subscription import Subscription, generic_check_subscriptions_method
from .article import Article
from .user import User
from .tag import Tag

LOGGER                = logging.getLogger(__name__)
feedparser.USER_AGENT = settings.DEFAULT_USER_AGENT


__all__ = ('read_post_create_task', 'Read', )


READ_BOOKMARK_TYPE_CHOICES = (
    (u'U', _(u'Undefined')),
    (u'A', _(u'This afternoon')),
    (u'W', _(u'This week-end')),
)


@task(name='Read.post_create', queue='high')
def read_post_create_task(read_id, *args, **kwargs):

    read = Read.objects.get(id=read_id)
    return read.post_create_task(*args, **kwargs)


class Read(Document, DocumentHelperMixin):
    user = ReferenceField('User', reverse_delete_rule=CASCADE)
    article = ReferenceField('Article', unique_with='user',
                             reverse_delete_rule=CASCADE)

    # HEADS UP: no `reverse_delete_rule` here, this would be too heavy and
    # slow. The hard work is done in `Subscription.post_delete_task()`.
    subscriptions = ListField(ReferenceField(Subscription))

    senders = ListField(ReferenceField(User), verbose_name=_(u'Senders'),
                        help_text=_(u'All the users that have shared the '
                                    u'article with the current owner of '
                                    u'this read.'))

    date_created = DateTimeField(default=now)

    is_good   = BooleanField(verbose_name=_('good for use?'),
                             help_text=_(u'The system has validated the '
                                         u'underlying article, and the read '
                                         u'can now be shown, used by its '
                                         u'owner, and counted in statistics.'),
                             default=False)

    is_read   = BooleanField(help_text=_(u'The Owner has read the content or '
                             u'has manually marked it as such.'),
                             default=False)
    date_read = DateTimeField()

    is_auto_read   = BooleanField(help_text=_(u'The system has automatically '
                                  u'marked it as read, in respect of a system '
                                  u'rule or a user preference.'), default=False)
    date_auto_read = DateTimeField()

    is_archived   = BooleanField(help_text=_(u'The Owner has archived this '
                                 u'read to explicitely keep it accessible.'),
                                 default=False)
    date_archived = DateTimeField()

    # NOTE: is_starred has no default, because we use True
    #       as "I like it" and False as "I don't like it".
    is_starred   = BooleanField(help_text=_(u'The owner has starred the '
                                u'content, signifying he/she loves it or '
                                u'that it is much of interest for him/her.'))
    date_starred = DateTimeField()

    is_bookmarked   = BooleanField(help_text=_(u'This content is marked to '
                                   u'be read later. When, depends on the '
                                   u'`.bookmark_type` attribute.'),
                                   default=False)
    date_bookmarked = DateTimeField()
    bookmark_type   = StringField(max_length=1, default=u'U',
                                  choices=READ_BOOKMARK_TYPE_CHOICES)

    is_fact   = BooleanField(help_text=_(u'Qualifies a time-dependant fact.'),
                             default=False)
    date_fact = DateTimeField()

    is_quote   = BooleanField(help_text=_(u'Qualifies someone’s words, '
                              u'thoughts or intentions.'), default=False)
    date_quote = DateTimeField()

    is_number   = BooleanField(help_text=_(u'Qualifies explicitely quantized '
                               u'data.'), default=False)
    date_number = DateTimeField()

    is_analysis   = BooleanField(help_text=_(u'Qualifies in-depth analysis, '
                                 u'studies or research publications.'),
                                 default=False)
    date_analysis = DateTimeField()

    is_prospective   = BooleanField(help_text=_(u'Qualifies things that want'
                                    u' to watch, that will happen or not.'),
                                    default=False)
    date_prospective = DateTimeField()

    is_knowhow   = BooleanField(help_text=_(u'Qualifies anything about '
                                u'How-to-do things and profession '
                                u'best-practices.'), default=False)
    date_knowhow = DateTimeField()

    is_rules   = BooleanField(help_text=_(u'Qualifies anything about laws, '
                              u'governments/public regulations.'),
                              default=False)
    date_rules = DateTimeField()

    is_knowledge   = BooleanField(help_text=_(u'Qualifies anything that the '
                                  u'owner wants to retain as a “must know”, '
                                  u'whatever the context.'), default=False)
    date_knowledge = DateTimeField()
    knowledge_type = StringField(max_length=2)

    is_fun   = BooleanField(help_text=_(u'Qualifies anything that makes you '
                            u'laugh out loud.'), default=False)
    date_fun = DateTimeField()

    # TODO: convert to UserTag to use ReferenceField and reverse_delete_rule.
    tags = ListField(GenericReferenceField(),
                     default=list, verbose_name=_(u'Tags'),
                     help_text=_(u'User set of tags for this read.'))

    # This will be set to Article.default_rating
    # until the user sets it manually.
    rating = FloatField()

    # ————————————————————————————————————————————————————————— Temporary space
    # items here will have a limited lifetime.

    # At the time this is created, set_subscriptions() does the right thing.
    # Don't let new reads be checked more than once, the database is already
    # overloaded with post-processing and normal end-users related usage.
    check_set_subscriptions_131004_done = BooleanField(default=True)

    def check_set_subscriptions_131004(self):
        """ Fix a bug where reads had too much subscriptions. """

        if isinstance(self.user, DBRef) or self.user is None:
            self.delete()
            sys.stderr.write(u'u')
            return

        if isinstance(self.article, DBRef) or self.article is None:
            self.delete()
            sys.stderr.write(u'a')
            return

        if self.subscriptions.count() == 1:
            # Don't bother doing CPU-intensive tasks,
            # this one seems good. At least we hope.
            self.update(set__check_set_subscriptions_131004_done=True)

        else:
            subscriptions_to_keep = []

            for subscription in self.subscriptions:
                try:
                    if subscription.user == self.user:
                        subscriptions_to_keep.append(subscription)
                except:
                    sys.stderr.write(u'-')

            # We have to update() because changing the boolean to True
            # doesn't make MongoEngine write it to the database, because
            # the new value is not different from the default one…
            #
            # Then we update subscriptions via the same mechanism to
            # avoid two disctinct write operations on the database.
            #
            # No need to reload, this is a one-shot repair.
            self.update(set__check_set_subscriptions_131004_done=True,
                        set__subscriptions=subscriptions_to_keep)

    # ———————————————————————————————————————————————————————— Class attributes

    watch_attributes = (
        'is_fact',
        'is_number',
        'is_analysis',
        'is_quote',
        'is_prospective',
        'is_rules',
        'is_knowhow',
        'is_knowledge',
        'is_fun',
    )

    status_data = {
        #
        # NOTE 1: "is_good" has nothing to do here, it's a system flag.
        #       do not confuse it with read statuses.
        #
        # NOTE 2: These two are not real statuses, but having them here
        #       allows to keep everything status-related here, without
        #       needing to craft specific code outside of this file.
        #       Just do something like:
        #
        #           if mode == 'is_read' and negated:
        #               mode = 'is_unread'
        #
        #       And then use `mode` as usual, like any other.
        #

        'all': {
            'list_headers':  (_(u'%(count)s article'),
                              _(u'%(count)s articles')),
        },

        'is_unread': {
            'list_headers':  (_(u'%(count)s unread article'),
                              _(u'%(count)s unread articles')),
        },

        # —————————————————————————————————————————————————————————————————————

        'is_read': {
            'list_name':     pgettext_lazy(u'past participle, plural', u'read'),
            'view_name':     u'read',
            'list_url':      _(ur'^read/read/$'),
            'do_title':      _(u'Mark as read'),
            'list_headers':  (_(u'%(count)s read article'),
                              _(u'%(count)s read articles')),
            'undo_title':    _(u'Mark as unread'),
            'do_label':      _(u'Mark read'),
            'undo_label':    _(u'Mark unread'),
            'status_label':  pgettext_lazy(u'adjective', u'read'),
            'do_icon':       pgettext_lazy(u'awesome-font icon name',
                                           u'check-empty'),
            'undo_icon':     pgettext_lazy(u'awesome-font icon name', u'check'),
        },

        'is_starred': {
            'list_name':     _(u'starred'),
            'view_name':     u'starred',
            'list_url':      _(ur'^read/starred/$'),
            'do_title':      _(u'Star (add to favorites)'),
            'list_headers':  (_(u'%(count)s starred article'),
                              _(u'%(count)s starred articles')),
            'undo_title':    _(u'Remove from starred/favorites'),
            'do_label':      pgettext_lazy(u'verb', u'Star'),
            'undo_label':    _(u'Unstar'),
            'status_label':  _(u'starred'),
            'do_icon':       pgettext_lazy(u'awesome-font icon name',
                                           u'star-empty'),
            'undo_icon':     pgettext_lazy(u'awesome-font icon name', u'star'),
        },

        'is_archived': {
            'list_name':     _(u'archived'),
            'view_name':     u'archived',
            'list_url':      _(ur'^read/archived/$'),
            'do_title':      _(u'Archive'),
            'list_headers':  (_(u'%(count)s article archived'),
                              _(u'%(count)s articles archived')),
            'undo_title':    _(u'Delete'),
            'do_label':      _(u'Archive'),
            'undo_label':    _(u'Delete'),
            'status_label':  _(u'archived'),
            'do_icon':       pgettext_lazy(u'awesome-font icon name',
                                           u'download'),
            'undo_icon':     pgettext_lazy(u'awesome-font icon name',
                                           u'archive'),
        },

        'is_bookmarked': {
            'list_name':     _(u'later'),
            'view_name':     u'later',
            'list_url':      _(ur'^read/later/$'),
            'do_title':      _(u'Keep for reading later'),
            'list_headers':  (_(u'%(count)s article to read later'),
                              _(u'%(count)s articles to read later')),
            'undo_title':    _(u'Remove from reading list'),
            'do_label':      _(u'Read later'),
            'undo_label':    _(u'Do not read later'),
            'status_label':  _(u'kept for later'),
            'do_icon':       pgettext_lazy(u'awesome-font icon name',
                                           u'bookmark-empty'),
            'undo_icon':     pgettext_lazy(u'awesome-font icon name',
                                           u'bookmark'),
        },

        'is_fact': {
            'list_name':     _(u'facts'),
            'view_name':     u'facts',
            'list_url':      _(ur'^read/facts/$'),
            'do_title':      _(u'Mark as fact / important event'),
            'list_headers':  (_(u'%(count)s article containing fact(s)'),
                              _(u'%(count)s articles containing fact(s)')),
            'undo_title':    _(u'Remove from facts / important events'),
            'status_title':  _(u'This article contains one or '
                               u'more important facts'),
            'do_label':      _(u'Mark as fact'),
            'undo_label':    _(u'Unmark fact'),
            'status_label':  _(u'fact'),
            'do_icon':       pgettext_lazy(u'awesome-font icon name',
                                           u'circle-blank'),
            'undo_icon':     pgettext_lazy(u'awesome-font icon name',
                                           u'bullseye'),
        },

        'is_number': {
            'list_name':     _(u'numbers'),
            'view_name':     u'numbers',
            'list_url':      _(ur'^read/numbers/$'),
            'do_title':      _(u'Mark as valuable number'),
            'list_headers':  (_(u'%(count)s article containing number(s)'),
                              _(u'%(count)s articles containing number(s)')),
            'undo_title':    _(u'Remove from valuable numbers'),
            'status_title':  _(u'This article contains quantified '
                               u'numbers for a watch.'),
            'do_label':      _(u'Mark as number'),
            'undo_label':    _(u'Unmark number'),
            'status_label':  _(u'number'),
            'do_icon':       pgettext_lazy(u'awesome-font icon name',
                                           u'bar-chart'),
            'undo_icon':     pgettext_lazy(u'awesome-font icon name',
                                           u'bar-chart icon-flip-horizontal'),
            'status_icon':   pgettext_lazy(u'awesome-font icon name',
                                           u'bar-chart'),
            #'undo_icon_stack': True,
        },

        'is_analysis': {
            'list_name':     _(u'analysis'),
            'view_name':     u'analysis',
            'list_url':      _(ur'^read/analysis/$'),
            'do_title':      _(u'Mark as analysis / study / research'),
            'list_headers':  (pgettext_lazy(u'singular', u'%(count)s analysis'),
                              pgettext_lazy(u'plural', u'%(count)s analysis')),
            'undo_title':    _(u'Unmark analysis / study / research'),
            'status_title':  _(u'This article contains an analysis, '
                               u'an in-depth study or a research '
                               u'publication.'),
            'do_label':      _(u'Mark as analysis'),
            'undo_label':    _(u'Unmark analysis'),
            'status_label':  _(u'analysis'),
            'do_icon':       pgettext_lazy(u'awesome-font icon name',
                                           u'beaker'),
            'undo_icon':     pgettext_lazy(u'awesome-font icon name',
                                           u'beaker icon-rotate-90'),
            'status_icon':   pgettext_lazy(u'awesome-font icon name',
                                           u'beaker'),
        },

        'is_quote': {
            'list_name':     _(u'quotes'),
            'view_name':     u'quotes',
            'list_url':      _(ur'^read/quotes/$'),
            'do_title':      _(u'Mark as containing quote(s) from people '
                               u'you consider important'),
            'list_headers':  (_(u'%(count)s article containing quote(s)'),
                              _(u'%(count)s articles containing quote(s)')),
            'undo_title':    _(u'Unmark as containing quotes '
                               u'(people are not famous anymore?)'),
            'status_title':  _(u'This article contains one or more quote '
                               u'from people you care about.'),
            'do_label':      _(u'Mark as quote'),
            'undo_label':    _(u'Unmark quote'),
            'status_label':  pgettext_lazy(u'noun', u'quote'),
            'do_icon':       pgettext_lazy(u'awesome-font icon name',
                                           u'quote-left icon-flip-vertical'),
            'undo_icon':     pgettext_lazy(u'awesome-font icon name',
                                           u'quote-right'),
            'status_icon':   pgettext_lazy(u'awesome-font icon name',
                                           u'quote-left icon-flip-vertical'),
        },

        'is_prospective': {
            'list_name':     _(u'prospective'),
            'view_name':     u'prospective',
            'list_url':      _(ur'^read/prospective/$'),
            'do_title':      _(u'Mark as prospective-related content'),
            'list_headers':  (_(u'%(count)s prospective article'),
                              _(u'%(count)s prospective articles')),
            'undo_title':    _(u'Unmark as prospective-related content'),
            'status_title':  _(u'This article contains prospective element(s) '
                               u'or must-remember hypothesis.'),
            'do_label':      _(u'Mark as prospective'),
            'undo_label':    _(u'Unmark prospective'),
            'status_label':  _(u'prospective'),
            'do_icon':       pgettext_lazy(u'awesome-font icon name',
                                           u'lightbulb'),
            'undo_icon':     pgettext_lazy(u'awesome-font icon name',
                                           u'lightbulb icon-rotate-180'),
            'status_icon':   pgettext_lazy(u'awesome-font icon name',
                                           u'lightbulb'),
        },

        'is_rules': {
            'list_name':     _(u'rules'),
            'view_name':     u'rules',
            'list_url':      _(ur'^read/rules/$'),
            'do_title':      _(u'Mark as legal/regulations-related content'),
            'list_headers':  (_(u'%(count)s regulation-related article'),
                              _(u'%(count)s regulation-related articles')),
            'undo_title':    _(u'Unmark as legal content (overriden laws?)'),
            'status_title':  _(u'This article contains regulations/'
                               u'law/rules element(s)'),
            'do_label':      _(u'Mark as law/regul.'),
            'undo_label':    _(u'Unmark law/regul.'),
            'status_label':  _(u'regulations'),
            'do_icon':       pgettext_lazy(u'awesome-font icon name',
                                           u'legal icon-flip-horizontal'),
            'undo_icon':     pgettext_lazy(u'awesome-font icon name',
                                           u'legal icon-rotate-180'),
            'status_icon':   pgettext_lazy(u'awesome-font icon name',
                                           u'legal icon-flip-horizontal'),
        },

        'is_knowhow': {
            'list_name':    _(u'best-practices'),
            # WARNING: there  is a '_' in the view name, and a '-' in the URL.
            'view_name':     u'know_how',
            'list_url':      _(ur'^read/best-practices/$'),
            'do_title':      _(u'Mark as best-practices / state of art '
                               u'content'),
            'list_headers':  (_(u'%(count)s best-practices article'),
                              _(u'%(count)s best-practices articles')),
            'undo_title':    _(u'Unmark as best-practices / state of art '
                               u'(has it become obsolete?)'),
            'status_title':  _(u'This article contains best-practices / '
                               u' state of art element(s).'),
            'do_label':      _(u'Mark as best-practice'),
            'undo_label':    _(u'Unmark best-practice'),
            'status_label':  pgettext_lazy(u'noun', u'know-how'),
            'do_icon':       pgettext_lazy(u'awesome-font icon name',
                                           u'trophy'),
            'undo_icon':     pgettext_lazy(u'awesome-font icon name',
                                           u'trophy icon-flip-vertical'),
            'status_icon':   pgettext_lazy(u'awesome-font icon name',
                                           u'trophy'),
        },

        'is_knowledge': {
            'list_name':     _(u'knowlegde'),
            'view_name':     u'knowledge',
            'list_url':      _(ur'^read/knowledge/$'),
            'do_title':      _(u'Mark as a valuable piece of '
                               u'knowlegde for your brain or life'),
            'list_headers':  (_(u'%(count)s knowledge article'),
                              _(u'%(count)s knowledge articles')),
            'undo_title':    _(u'Unmark as neuronal-exciting '
                               u'element(s)'),
            'status_title':  _(u'This article contains a valuable '
                               u'piece of knowlegde.'),
            'do_label':      _(u'Mark as Knowledge'),
            'undo_label':    _(u'Unmark knowlegde'),
            'status_label':  _(u'knowledge'),
            'do_icon':       pgettext_lazy(u'awesome-font icon name', u'globe'),
            'undo_icon':     pgettext_lazy(u'awesome-font icon name',
                                           u'globe icon-rotate-180'),
            'status_icon':   pgettext_lazy(u'awesome-font icon name', u'globe'),
        },

        'is_fun': {
            'list_name':     _(u'funbox'),
            'view_name':     u'fun',
            'list_url':      _(ur'^read/fun/$'),
            'do_title':      _(u'Mark as being fun. Are you sure?'),
            'list_headers':  (_(u'%(count)s fun article'),
                              _(u'%(count)s fun articles')),
            'undo_title':    _(u'Not fun anymore, sadly.'),
            'status_title':  _(u'OMG, this thing is sooooooooo fun! LMAO!'),
            'do_label':      _(u'Mark as fun'),
            'undo_label':    _(u'Mark as boring'),
            'status_label':  _(u'fun'),
            'do_icon':       pgettext_lazy(u'awesome-font icon name', u'smile'),
            'undo_icon':     pgettext_lazy(u'awesome-font icon name', u'frown'),
            'status_icon':   pgettext_lazy(u'awesome-font icon name', u'smile'),
        },
    }

    meta = {
        'indexes': [
            'user',
            ('user', 'is_good'),
            ('user', 'is_good', 'is_read'),
            ('user', 'is_good', 'is_starred'),
            ('user', 'is_good', 'is_bookmarked'),
            'article',
            ('article', 'is_good'),
        ]
    }

    # ——————————————————————————————————————————————————————————— Class methods

    @classmethod
    def get_status_attributes(cls):
        try:
            return cls._status_attributes_cache

        except AttributeError:
            # cls._status_attributes_cache = [fname for fname, field
            #                                 in cls._fields.items()
            #                                 if fname.startswith('is_')
            #                                 and isinstance(field,
            #                                                BooleanField)]

            cls._status_attributes_cache = [
                k for k in cls.status_data.keys()
                if 'list_url' in cls.status_data[k]
            ]

            return cls._status_attributes_cache

    # ———————————————————————————————————— Class methods & Mongo/Django related

    @classmethod
    def signal_post_save_handler(cls, sender, document,
                                 created=False, **kwargs):

        read = document

        if created:
            if read._db_name != settings.MONGODB_NAME_ARCHIVE:
                read_post_create_task.delay(read.id)

    def post_create_task(self):
        """ Method meant to be run from a celery task. """

        self.rating = self.article.default_rating

        self.set_subscriptions(commit=False)

        self.save()

        self.update_cached_descriptors()

    @classmethod
    def signal_pre_delete_handler(cls, sender, document, **kwargs):

        read = document

        if not read.is_good:
            # counters already don't take this read into account.
            return

        read.update_cached_descriptors(operation='-')

    def validate(self, *args, **kwargs):
        try:
            super(Read, self).validate(*args, **kwargs)

        except ValidationError as e:
            tags_error = e.errors.get('tags', None)

            if tags_error and 'GenericReferences can only contain documents' \
                    in str(tags_error):

                good_tags  = set()
                to_replace = set()

                for tag in self.tags:
                    if isinstance(tag, Document):
                        good_tags.add(tag)

                    else:
                        to_replace.add(tag)

                new_tags = Tag.get_tags_set([t for t in to_replace
                                            if t not in (u'', None)])

                self.tags = good_tags | new_tags
                e.errors.pop('tags')

            if e.errors:
                raise e

    def __unicode__(self):
        return _(u'{0}∞{1} (#{2}∞#{3}→#{4}) {5} @{6}').format(
            self.user.username,
            self.article.title[:40] + (self.article.title[40:] and u'…'),
            self.user.id, self.article.id, self.id,
            pgettext_lazy(u'adjective', u'read')
            if self.is_read
            else pgettext_lazy(u'adjective', u'unread'),
            self.rating)

    # —————————————————————————————————————————————————————————————— Properties

    @property
    def is_restricted(self):

        if (self.user.is_staff_or_superuser_and_enabled
                and self.user.preferences.staff.allow_all_articles):
            return False

        if self.is_archived:
            return False

        return any(map(lambda sub: sub.feed.restricted, self.subscriptions))

        # TODO: refresh/implement this to avoid fetching content from the
        #       database if the remote article is not available anymore.
        # NOTE: This is clearly overkill in the libre version, as 1flow
        #       is just a personnal RSS / web crawler tool. This makes
        #       sense for legal issues only if 1flow.io is a paid service.
        #
        # delta_from_now = timedelda(now() - self.date_published)
        # if self.is_read:
        #     if self.is_archived:
        #     if self.is_auto_read:
        #         if self.article.feed.restrict_read_delta \
        #           and delta_from_now > self.article.feed.restrict_read_delta:
        #             return True
        #     and delta_from_now <= config.ARTICLE_LIMITS_READ

    @property
    def title(self):

        article = self.article
        feed    = article.feed

        if feed:
            source = _(u' ({feed})').format(feed=feed.name)

        else:
            source = u''

        return _(u'{title}{source}').format(title=article.title,
                                            source=source)

    @property
    def get_source(self):

        if self.article.source:
            return self.article.source

        if self.subscriptions:
            # This method displays things to the user. Don't let dead
            # DBRefs pass through.
            #
            # TODO: let things pass through for administrators, though.
            #
            return [s for s in self.subscriptions if isinstance(s, Document)]

        return self.article.get_source

    @property
    def get_source_unicode(self):

        source = self.get_source

        if source.__class__ in (unicode, str):
            return source

        sources_count = len(source)

        if sources_count > 2:
            return _(u'Multiple sources ({0} feeds)').format(sources_count)

        return u' / '.join(x.name for x in source)

    @property
    def reading_time(self):
        """ Return a rounded value of the approximate reading time,
            for the user and the article. """

        wc = self.article.word_count_TRANSIENT

        if wc is None:
            return None

        return wc / self.user.preferences.read.reading_speed

    @property
    def reading_time_display(self):

        rtm = self.reading_time

        if rtm is None:
            return u''

        if rtm == 0:
            return _(u'a quick read')

        return _(u'{0} read').format(naturaldelta(timedelta(seconds=rtm * 60)))

    @property
    def reading_time_abstracted(self):

        rtm = self.reading_time

        if rtm is None:
            return u''

        inum = 1
        icon = u'∎'  # u'<i class="icon-time"></i>'
        tmpl = _(u'<span class="popover-top" data-toggle="tooltip" '
                 u'title="Reading time: {0}">{1}</span>')
        time = naturaldelta(timedelta(seconds=rtm * 60))

        if rtm > 8:
            inum = 4

        elif rtm > 3:
            inum = 3

        elif rtm > 1:
            inum = 2

        elif rtm == 0:
            # HEADS UP: patch/hack; non-breakable spaces everywhere.
            time = _(u'very quick (<1 min)')

        return tmpl.format(time, inum * icon)

    # ————————————————————————————————————————————————————————————————— Methods

    # HEADS UP: this method come from the subscription module.
    check_subscriptions = generic_check_subscriptions_method

    def set_subscriptions(self, commit=True):
        # @all_subscriptions, because here internal feeds count.
        user_feeds         = [sub.feed for sub in self.user.all_subscriptions]
        article_feeds      = [feed for feed in self.article.feeds
                              if feed in user_feeds]

        # HEADS UP: searching only for feed__in=article_feeds will lead
        # to have other user's subscriptions attached to the read.
        # Harmless but very confusing.
        self.subscriptions = list(Subscription.objects(
                                  feed__in=article_feeds,
                                  user=self.user))

        if commit:
            self.save()

            # TODO: only for the new subscriptions.
            #self.update_cached_descriptors( … )

        return self.subscriptions

    def activate(self, force=False):
        """ This method will mark the Read ``.is_good=True``
            and do whatever in consequence. """

        if not force and not self.article.is_good:
            LOGGER.error(u'Cannot activate read %s, whose article '
                         u'is not ready for public use!', self)
            return

        self.is_good = True
        self.save()

        update_only = ['all']

        if self.is_starred:
            update_only.append('starred')

        if self.is_bookmarked:
            update_only.append('bookmarked')

        if not self.is_read:
            update_only.append('unread')

        self.update_cached_descriptors(update_only=update_only)

    def remove_tags(self, tags=[]):
        """ If the user remove his own tags from a Read, it will get back the
            default tags from the article it comes from. """

        if tags:
            for tag in Tag.get_tags_set(tags, origin=self):
                self.update(pull__tags=tag)

            self.safe_reload()

        if self.tags == []:
            self.tags = self.article.tags.copy()
            self.save()
            # NO update_cached_descriptors() here.

    def add_tags(self, tags):

        for tag in Tag.get_tags_set(tags, origin=self):
            self.update(add_to_set__tags=tag)

        self.safe_reload()
        # NO update_cached_descriptors() here.

    # ————————————————————————————————————————————— Update subscriptions caches

    def update_cached_descriptors(self, operation=None, update_only=None):

        if operation is None:
            operation = '+'

        assert operation in ('+', '-')

        if operation == '+':
            op = operator.add
        else:
            op = operator.sub

        if update_only is None:

            to_change = ['all_articles_count']

            if self.is_archived:
                to_change.append('archived_articles_count')

            if self.is_bookmarked:
                to_change.append('bookmarked_articles_count')

            if self.is_starred:
                to_change.append('starred_articles_count')

            if not self.is_read:
                to_change.append('unread_articles_count')

            for watch_attr_name in Read.watch_attributes:
                if getattr(self, watch_attr_name):
                    # Strip 'is_' from the attribute name.
                    to_change.append(watch_attr_name[3:] + '_articles_count')

        else:
            assert type(update_only) in (type(tuple()), type([]))

            to_change = [only + '_articles_count' for only in update_only]

            for attr_name in to_change:
                try:

                    updated_folders = []

                    for subscription in self.subscriptions:
                        setattr(subscription, attr_name,
                                op(getattr(subscription, attr_name), 1))

                        for folder in subscription.folders:
                            if folder in updated_folders:
                                continue

                            setattr(folder, attr_name,
                                    op(getattr(folder, attr_name), 1))

                            updated_folders.append(folder)

                    setattr(self.user, attr_name,
                            op(getattr(self.user, attr_name), 1))

                except AttributeError, e:
                    LOGGER.warning(u'Skipped cache descriptor update for %s '
                                   u'from %s: %s', attr_name, self, e)

    def is_read_changed(self):

        self.update_cached_descriptors(operation='-' if self.is_read else '+',
                                       update_only=['unread'])

    def is_starred_changed(self):

        self.update_cached_descriptors(operation='+'
                                       if self.is_starred else '-',
                                       update_only=['starred'])

    def mark_archived(self):
        if self.is_archived_can_change() and not self.is_archived:
            self.is_archived = True
            self.save()

    def is_archived_can_change(self):

        if self.is_archived:
            # A user can always unarchive anything. This is dangerous because
            # he can permanently loose data, but the UI asks for a confirmation
            # in that case.
            return True

        return True

        if self.is_restricted:
            LOGGER.warning(u'Implement real-time checking '
                           u'of archive-ability permission.')

            return True

        else:
            # An unrestricted read/feed can always change status.
            return True

    def is_archived_changed(self):

        self.update_cached_descriptors(operation='+'
                                       if self.is_archived else '-',
                                       update_only=['archived'])

    def is_bookmarked_changed(self):

        self.update_cached_descriptors(operation='+'
                                       if self.is_bookmarked else '-',
                                       update_only=['bookmarked'])


# ————————————————————————————————————————————————————————— external properties
#                                            Defined here to avoid import loops


def Folder_reads_property_get(self):

    # The owner has already filtered good reads via an indexed search.
    #
    # self.subscriptions is a QuerySet, we need
    # to convert it to a list for the new QuerySet.
    return self.owner.reads(subscriptions__in=[s for s in self.subscriptions])


def Subscription_reads_property_get(self):

    # The user has already filtered good reads via an indexed search.
    return self.user.reads(subscriptions__contains=self)


def Article_reads_property_get(self):

    # Do NOT filter on is_good here. The Article needs to
    # know about ALL reads, to activate them when ready.
    return Read.objects.filter(article=self)


def Article_good_reads_property_get(self):

    # Do NOT filter on is_good here. The Article needs to
    # know about ALL reads, to activate them when ready.
    return self.reads(is_good=True)


def Article_bad_reads_property_get(self):

    # Do NOT filter on is_good here. The Article needs to
    # know about ALL reads, to activate them when ready.
    return self.reads(Q(is_good__exists=False) | Q(is_good=False))


def User_reads_property_get(self):

    return Read.objects.filter(user=self, is_good=True)


Folder.reads       = property(Folder_reads_property_get)
Subscription.reads = property(Subscription_reads_property_get)
Article.reads      = property(Article_reads_property_get)
Article.good_reads = property(Article_good_reads_property_get)
Article.bad_reads  = property(Article_bad_reads_property_get)
User.reads         = property(User_reads_property_get)


# —————————————————————————————————————————————————————— external bound methods
#                                            Defined here to avoid import loops


def Subscription_create_read_method(self, article, verbose=True, **kwargs):
    """ Returns a tuple (read, created) with the new (or existing) read,
        and ``created`` as a boolean indicating if it was actually created
        or if it existed before.

    """
    new_read = Read(article=article, user=self.user)

    try:
        new_read.save()

    except (NotUniqueError, DuplicateKeyError):
        if verbose:
            LOGGER.info(u'Duplicate read %s!', new_read)

        cur_read = Read.objects.get(article=article, user=self.user)

        # If another feed has already created the read, be sure the
        # current one is registered in the read via the subscriptions.
        cur_read.update(add_to_set__subscriptions=self)

        #
        # NOTE: we do not check `is_good` here, when the read was not
        #       created. This is handled (indirectly) via the article
        #       check part of Subscription.check_reads(). DRY.
        #

        return cur_read, False

    except:
        # We must not fail here, because often this method is called in
        # a loop 'for subscription in ….subscriptions:'. All other read
        # creations need to succeed.
        LOGGER.exception(u'Could not save read %s!', new_read)

    else:

        # XXX: todo remove this 'is not None', when database is clean…
        tags = [t for t in article.tags if t is not None]

        params = dict(('set__' + key, value)
                      for key, value in kwargs.items())

        # If the article was already there and fetched (mutualized from
        # another feed, for example), activate the read immediately.
        # If we don't do this here, the only alternative is the daily
        # global_reads_checker() task, which is not acceptable for
        # "just-added" subscriptions, whose reads are created via the
        # current method.
        if article.is_good:
            params['set__is_good'] = True

        new_read.update(set__tags=tags,
                        set__subscriptions=[self], **params)

        # Update cached descriptors
        self.all_articles_count += 1
        self.unread_articles_count += 1

        return new_read, True

Subscription.create_read = Subscription_create_read_method
