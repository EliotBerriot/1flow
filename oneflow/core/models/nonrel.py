# -*- coding: utf-8 -*-

from mongoengine import Document
from mongoengine.fields import (IntField, FloatField, BooleanField,
                                DateTimeField,
                                ListField, StringField,
                                URLField, EmailField,
                                ReferenceField, GenericReferenceField,
                                EmbeddedDocumentField)

from django.utils.translation import ugettext_lazy as _

import datetime
import logging

LOGGER = logging.getLogger(__name__)


class Source(Document):
    # is this a feed ??
    url = URLField()


class Article(Document):
    title = StringField(max_length=256, required=True)
    slug = StringField(max_length=256)
    authors = ListField(ReferenceField('User'))
    publishers = ListField(ReferenceField('User'))
    url = URLField()
    date_published = DateTimeField(default=datetime.datetime.now)
    abstract = StringField()
    content = StringField()
    comments = ListField(ReferenceField('Comment'))
    default_rating = FloatField()

    # A snap / a serie of snaps references the original article.
    # An article references its source (origin blog / newspaper…)
    source = GenericReferenceField()

    def is_origin(self):
        return isinstance(self.source, Source)

    # Avoid displaying duplicates to the user.
    duplicates = ListField(ReferenceField('Article')) # , null=True)


class Read(Document):
    user = ReferenceField('User')
    article = ReferenceField('Article')
    is_read = BooleanField()
    is_auto_read = BooleanField()
    date_created = DateTimeField()
    date_read = DateTimeField()
    rating = FloatField()

    # For free users, fix a limit ?
    #meta = {'max_documents': 1000, 'max_size': 2000000}


class Comment(Document):
    TYPE_COMMENT = 1
    TYPE_INSIGHT = 10
    TYPE_ANALYSIS = 20
    TYPE_SYNTHESIS = 30
    nature = IntField(default=TYPE_COMMENT)
    is_synthesis = BooleanField()
    is_analysis = BooleanField()
    read = ReferenceField('Read')
    content = StringField()

    # already in the Read:
    #article = ReferenceField('Article')
    #user = ReferenceField('User')

    in_reply_to = ReferenceField('Comment') # , null=True)

    # @property
    # def type(self):
    #     return self.internal_type
    # @type.setter
    # def type(self, type):
    #     parent_type = comment.in_reply_to.type
    #     if parent_type is not None:
    #         if parent_type == Comment.TYPE_COMMENT:
    #             if type == Comment.TYPE_COMMENT:
    #                 self.internal_type = Comment.TYPE_COMMENT
    #             raise ValueError('Cannot synthetize a comment')
    #             return Comment.TYPE_COMMENT


class SnapPreference(Document):
    select_paragraph = BooleanField(_('Select whole paragraph on click'),
                                    default=False) # , blank=True)
    default_public = BooleanField(_('Grows public by default'),
                                  default=True) # , blank=True)


class NotificationPreference(Document):
    """ Email and other web notifications preferences. """


class Preference(Document):
    snap = EmbeddedDocumentField('SnapPreference')
    notification = EmbeddedDocumentField('NotificationPreference')


class User(Document):
    email = EmailField()
    preferences = EmbeddedDocumentField('Preference')
