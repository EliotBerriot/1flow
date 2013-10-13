# -*- coding: utf-8 -*-

import logging

from mongoengine import Document, PULL
from mongoengine.fields import (StringField, ListField,
                                URLField, ReferenceField, )

from .common import DocumentHelperMixin

LOGGER = logging.getLogger(__name__)


__all__ = ('Source', )


class Source(Document, DocumentHelperMixin):
    """ The "original source" for similar articles: they have different authors,
        different contents, but all refer to the same information, which can
        come from the same article on the net (or radio, etc).

        Eg:
            - article1 on Le Figaro
            - article2 on Liberation
            - both refer to the same AFP news, but have different content.

    """
    type    = StringField()
    uri     = URLField(unique=True)
    name    = StringField()
    authors = ListField(ReferenceField('User', reverse_delete_rule=PULL))
    slug    = StringField()
