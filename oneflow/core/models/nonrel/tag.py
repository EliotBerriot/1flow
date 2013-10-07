# -*- coding: utf-8 -*-

import logging

from celery import task
from statsd import statsd

from pymongo.errors import DuplicateKeyError

from mongoengine import Document, NULLIFY, PULL
from mongoengine.fields import (StringField, ReferenceField, ListField,
                                GenericReferenceField)
from mongoengine.errors import NotUniqueError

from django.conf import settings
from django.utils.text import slugify
from django.utils.translation import ugettext_lazy as _

from .common import DocumentHelperMixin


LOGGER = logging.getLogger(__name__)


__all__ = ('tag_post_create_task', 'tag_replace_duplicate_everywhere', 'Tag', )


@task(name='Tag.post_create', queue='high')
def tag_post_create_task(tag_id, *args, **kwargs):

    tag = Tag.objects.get(id=tag_id)
    return tag.post_create_task(*args, **kwargs)


@task(name='Tag.replace_duplicate_everywhere', queue='low')
def tag_replace_duplicate_everywhere(tag_id, dupe_id, *args, **kwargs):

    tag  = Tag.objects.get(id=tag_id)
    dupe = Tag.objects.get(id=dupe_id)

    # This method is defined in nonrel.article to avoid an import loop.
    return tag.replace_duplicate_in_articles(dupe, *args, **kwargs)
    #
    # TODO: do the same for feeds, reads (, subscriptions?) …
    #


class Tag(Document, DocumentHelperMixin):
    name     = StringField(verbose_name=_(u'name'), unique=True)
    slug     = StringField(verbose_name=_(u'slug'))
    language = StringField(verbose_name=_(u'language'), default='')
    parents  = ListField(ReferenceField('self',
                         reverse_delete_rule=PULL), default=list)
    children = ListField(ReferenceField('self',
                         reverse_delete_rule=PULL), default=list)
    # reverse_delete_rule=NULLIFY,
    origin   = GenericReferenceField(verbose_name=_(u'Origin'),
                                     help_text=_(u'Initial origin from where '
                                                 u'the tag was created from, '
                                                 u'to eventually help '
                                                 u'defining other attributes.'))
    duplicate_of = ReferenceField('Tag', reverse_delete_rule=NULLIFY,
                                  verbose_name=_(u'Duplicate of'),
                                  help_text=_(u'Put a "master" tag here to '
                                              u'help avoiding too much '
                                              u'different tags (eg. singular '
                                              u'and plurals) with the same '
                                              u'meaning and loss of '
                                              u'information.'))

    meta = {
        'indexes': ['name', ]
    }

    # See the `WordRelation` class before working on this.
    #
    # antonyms = ListField(ReferenceField('self'), verbose_name=_(u'Antonyms'),
    #                      help_text=_(u'Define an antonym tag to '
    #                      u'help search connectable but.'))

    def __unicode__(self):
        return _(u'{0} {1}⚐ (#{2})').format(self.name, self.language, self.id)

    @classmethod
    def signal_post_save_handler(cls, sender, document,
                                 created=False, **kwargs):

        tag = document

        if created:
            if tag._db_name != settings.MONGODB_NAME_ARCHIVE:
                tag_post_create_task.delay(tag.id)

    def post_create_task(self):
        """ Method meant to be run from a celery task. """

        if not self.slug:
            self.slug = slugify(self.name)
            self.save()

            statsd.gauge('tags.counts.total', 1, delta=True)

    @classmethod
    def get_tags_set(cls, tags_names, origin=None):

        tags = set()

        for tag_name in tags_names:
            tag_name = tag_name.lower()

            try:
                tag = cls.objects.get(name=tag_name)

            except cls.DoesNotExist:
                try:
                    tag = cls(name=tag_name, origin=origin).save()

                except (NotUniqueError, DuplicateKeyError):
                    tag = cls.objects.get(name=tag_name)

            tags.add(tag.duplicate_of or tag)

        return tags

    def save(self, *args, **kwargs):
        """ This method will simply add the missing children/parents reverse
            links of the current Tag. This is needed when modifying tags from
            the Django admin, which doesn't know about the reverse-link
            existence.

            .. note:: sadly, we have no fast way to do the same for links
                removal.
        """

        super(Tag, self).save(*args, **kwargs)

        for parent in self.parents:
            if self in parent.children:
                continue

            try:
                parent.add_child(self, update_reverse_link=False,
                                 full_reload=False)
            except:
                LOGGER.exception(u'Exception while reverse-adding '
                                 u'child %s to parent %s', self, parent)

        for child in self.children:
            if self in child.parents:
                continue

            try:
                child.add_parent(self, update_reverse_link=False,
                                 full_reload=False)
            except:
                LOGGER.exception(u'Exception while reverse-adding '
                                 u'parent %s to child %s', self, child)

        return self

    def add_parent(self, parent, update_reverse_link=True, full_reload=True):

        self.update(add_to_set__parents=parent)

        if full_reload:
            self.safe_reload()

        if update_reverse_link:
            parent.add_child(self, update_reverse_link=False)

    def remove_parent(self, parent, update_reverse_link=True, full_reload=True):

        if update_reverse_link:
            parent.remove_child(self, update_reverse_link=False)

        self.update(pull__parents=parent)

        if full_reload:
            self.safe_reload()

    def add_child(self, child, update_reverse_link=True, full_reload=True):
        self.update(add_to_set__children=child)

        if full_reload:
            self.safe_reload()

        if update_reverse_link:
            child.add_parent(self, update_reverse_link=False)

    def remove_child(self, child, update_reverse_link=True, full_reload=True):

        if update_reverse_link:
            child.remove_parent(self, update_reverse_link=False)

        self.update(pull__children=child)

        if full_reload:
            self.safe_reload()
