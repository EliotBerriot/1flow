# -*- coding: utf-8 -*-

import logging
import feedparser

from statsd import statsd
from celery import task

from pymongo.errors import DuplicateKeyError

from mongoengine import Document, NULLIFY, CASCADE
from mongoengine.fields import StringField, BooleanField, ReferenceField
from mongoengine.errors import NotUniqueError

from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from .common import DocumentHelperMixin
from .website import WebSite

LOGGER                = logging.getLogger(__name__)
feedparser.USER_AGENT = settings.DEFAULT_USER_AGENT


__all__ = ('author_post_create_task', 'Author', )


# ••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••• Authors


@task(name=u'Author.post_create', queue=u'high')
def author_post_create_task(author_id, *args, **kwargs):

    author = Author.objects.get(id=author_id)
    return author.post_create_task(*args, **kwargs)


class Author(Document, DocumentHelperMixin):
    name        = StringField()
    website     = ReferenceField(u'WebSite', unique_with=u'origin_name',
                                 reverse_delete_rule=CASCADE)
    origin_name = StringField(help_text=_(u'When trying to guess authors, we '
                              u'have only a "fullname" equivalent. We need to '
                              u'store it for future comparisons in case '
                              u'firstname and lastname get manually modified '
                              u'after author creation.'))

    is_unsure = BooleanField(help_text=_(u'Set to True when the author '
                             u'has been found from its origin_name and '
                             u'not via email; because origin_name can '
                             u'be duplicated, but not emails.'),
                             default=False)

    user = ReferenceField(u'User', required=False, help_text=_(u'Link an '
                          u'internet author to a 1flow user.'),
                          reverse_delete_rule=NULLIFY)

    duplicate_of = ReferenceField(u'Author', reverse_delete_rule=NULLIFY)

    def __unicode__(self):
        return u'%s%s #%s for website %s' % (self.name or self.origin_name,
                                             _(u' (unsure)')
                                             if self.is_unsure else u'',
                                             self.id, self.website)

    @classmethod
    def signal_post_save_handler(cls, sender, document,
                                 created=False, **kwargs):

        author = document

        if created:
            if author._db_name != settings.MONGODB_NAME_ARCHIVE:
                author_post_create_task.delay(author.id)

    def post_create_task(self):
        """ Method meant to be run from a celery task. """

        statsd.gauge('authors.counts.total', 1, delta=True)

    @classmethod
    def get_authors_from_feedparser_article(cls, feedparser_article,
                                            set_to_article=None):

        if set_to_article:
            # This is an absolutized URL, hopefully.
            article_url = set_to_article.url

        else:
            article_url = getattr(feedparser_article, 'link',
                                  '').replace(' ', '%20') or None

        if article_url:
            website = WebSite.get_from_url(article_url)

        else:
            LOGGER.critical(u'NO url, cannot get any author.')

        authors = set()

        if 'authors' in feedparser_article:
            # 'authors' can be [{}], which is useless.

            for author_dict in feedparser_article['authors']:
                author = cls.get_author_from_feedparser_dict(author_dict,
                                                             website)

                if author:
                    if set_to_article:
                        set_to_article.update(add_to_set__authors=author)

                    authors.add(author)

        if 'author_detail' in feedparser_article:
            author = cls.get_author_from_feedparser_dict(
                feedparser_article['author_detail'], website)

            if author:
                if set_to_article:
                    set_to_article.update(add_to_set__authors=author)

                authors.add(author)

        if 'author' in feedparser_article:
            author = cls.get_author_from_feedparser_dict(
                {'name': feedparser_article['author']}, website)

            if author:
                if set_to_article:
                    set_to_article.update(add_to_set__authors=author)

                authors.add(author)

        if set_to_article and authors:
            set_to_article.reload()

        # Always return a list, else we hit
        # http://dev.1flow.net/development/1flow-dev/group/4026/
        return list(authors)

    @classmethod
    def get_author_from_feedparser_dict(cls, author_dict, website):

        email = author_dict.get('email', None)

        if email:
            # An email is less likely to have a duplicates than
            # a standard name. It takes precedence if it exists.

            try:
                return cls.objects.get(origin_name=email, website=website)

            except cls.DoesNotExist:
                try:
                    return cls(origin_name=email, website=website,
                               is_unsure=False).save()

                except (NotUniqueError, DuplicateKeyError):
                    # We just hit the race condition with two creations
                    # At the same time. Same player shoots again.
                    return cls.objects.get(origin_name=email, website=website)

        home_page = author_dict.get('href', None)

        if home_page:
            # A home_page is less likely to have a duplicates than a standard
            # name too. It also takes precedence after email if it exists.

            try:
                return cls.objects.get(origin_name=home_page, website=website)

            except cls.DoesNotExist:
                try:
                    return cls(origin_name=home_page, website=website,
                               is_unsure=False).save()

                except (NotUniqueError, DuplicateKeyError):
                    # We just hit the race condition with two creations
                    # At the same time. Same player shoots again.
                    return cls.objects.get(origin_name=home_page,
                                           website=website)

        origin_name = author_dict.get('name', None)

        if origin_name:
            try:
                return cls.objects.get(origin_name=origin_name,
                                       website=website)

            except cls.DoesNotExist:
                try:
                    return cls(origin_name=origin_name,
                               website=website,
                               is_unsure=True).save()
                except (NotUniqueError, DuplicateKeyError):
                    # We just hit the race condition with two creations
                    # At the same time. Same player shoots again.
                    return cls.objects.get(origin_name=origin_name,
                                           website=website)

        return None
