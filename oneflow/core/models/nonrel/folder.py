# -*- coding: utf-8 -*-

import logging

from mongoengine import Document, NULLIFY, CASCADE, PULL
from mongoengine.fields import StringField, ReferenceField, ListField

from ....base.fields import IntRedisDescriptor

from .common import DocumentHelperMixin, DocumentTreeMixin
from .user import User

LOGGER = logging.getLogger(__name__)


__all__ = ('Folder', )


def folder_all_articles_count_default(folder, *args, **kwargs):

    return folder.reads.count()


def folder_starred_articles_count_default(folder, *args, **kwargs):

    return folder.reads(is_starred=True).count()


def folder_unread_articles_count_default(folder, *args, **kwargs):

    return folder.reads(is_read=False).count()


def folder_bookmarked_articles_count_default(folder, *args, **kwargs):

    return folder.reads(is_bookmarked=True).count()


class Folder(Document, DocumentHelperMixin, DocumentTreeMixin):
    name = StringField(unique_with=['owner'])
    owner = ReferenceField('User', reverse_delete_rule=CASCADE)

    parent = ReferenceField('self', reverse_delete_rule=NULLIFY,
                            default=None)
    children = ListField(ReferenceField('self', reverse_delete_rule=PULL),
                         default=list)

    all_articles_count = IntRedisDescriptor(
        attr_name='uf.aa_c', default=folder_all_articles_count_default,
        set_default=True)

    unread_articles_count = IntRedisDescriptor(
        attr_name='uf.ua_c', default=folder_unread_articles_count_default,
        set_default=True)

    starred_articles_count = IntRedisDescriptor(
        attr_name='uf.sa_c', default=folder_starred_articles_count_default,
        set_default=True)

    bookmarked_articles_count = IntRedisDescriptor(
        attr_name='uf.ba_c', default=folder_bookmarked_articles_count_default,
        set_default=True)

    def __unicode__(self):
        return _(u'{0} for user {1}{2}{3}').format(
            self.name, self.owner,
            _(u', parent: {0} (#{1})').format(self.parent.name, self.parent.id)
                if self.parent else u'',
            _(u', children: %s').format(u', '.join(
                _(u'{0} (#{1})').format(child.name, child.id))
                    for child in self.children) if self.children else u'')


# ————————————————————————————————————————————————————————— external properties
#                                            Defined here to avoid import loops


def User_top_folders_property_get(self):

    return Folder.objects(owner=self, parent=None)


User.top_folders = property(User_top_folders_property_get)
