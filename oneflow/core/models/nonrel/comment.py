# -*- coding: utf-8 -*-

import logging

from mongoengine import Document, CASCADE, NULLIFY
from mongoengine.fields import (IntField, StringField,
                                BooleanField, ReferenceField,
                                EmbeddedDocumentField, )

from ...keyval import FeedbackDocument

from .common import DocumentHelperMixin

LOGGER = logging.getLogger(__name__)


__all__ = ('Comment', )


class Comment(Document, DocumentHelperMixin):
    TYPE_COMMENT = 1
    TYPE_INSIGHT = 10
    TYPE_ANALYSIS = 20
    TYPE_SYNTHESIS = 30

    VISIBILITY_PUBLIC  = 1
    VISIBILITY_GROUP   = 10
    VISIBILITY_PRIVATE = 20

    nature = IntField(default=TYPE_COMMENT)
    visibility = IntField(default=VISIBILITY_PUBLIC)

    is_synthesis = BooleanField()
    is_analysis = BooleanField()
    content = StringField()

    feedback = EmbeddedDocumentField(FeedbackDocument)

    # We don't comment reads. We comment articles.
    #read = ReferenceField('Read')
    article = ReferenceField('Article', reverse_delete_rule=CASCADE)

    # Thus, we must store
    user = ReferenceField('User', reverse_delete_rule=CASCADE)

    in_reply_to = ReferenceField('Comment', reverse_delete_rule=NULLIFY)

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
