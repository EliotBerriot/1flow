# -*- coding: utf-8 -*-

import logging

from operator import attrgetter

from pymongo.errors import DuplicateKeyError

from mongoengine import Document, NULLIFY, CASCADE, PULL
from mongoengine.fields import StringField, ReferenceField, ListField
from mongoengine.errors import NotUniqueError  # , ValidationError

from django.utils.translation import ugettext_lazy as _

from ....base.fields import IntRedisDescriptor

from .common import DocumentHelperMixin, DocumentTreeMixin, PseudoQuerySet
from .user import User

LOGGER = logging.getLogger(__name__)


__all__ = ('Folder', )


def lowername(objekt):

    return attrgetter('name')(objekt).lower()


def folder_all_articles_count_default(folder, *args, **kwargs):

    return folder.reads.count()


def folder_starred_articles_count_default(folder, *args, **kwargs):

    return folder.reads(is_starred=True).count()


def folder_unread_articles_count_default(folder, *args, **kwargs):

    return folder.reads(is_read=False).count()


def folder_bookmarked_articles_count_default(folder, *args, **kwargs):

    return folder.reads(is_bookmarked=True).count()


class Folder(Document, DocumentHelperMixin, DocumentTreeMixin):
    name = StringField(verbose_name=_(u'Name'), unique_with=['owner'])
    owner = ReferenceField('User', verbose_name=_(u'Owner'),
                           reverse_delete_rule=CASCADE)

    parent = ReferenceField('self', verbose_name=_(u'Parent'),
                            reverse_delete_rule=NULLIFY,
                            required=False, default=None)
    children = ListField(ReferenceField('self', reverse_delete_rule=PULL),
                         default=list, verbose_name=_(u'Children'))

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
            _(u', children: {0}').format(u', '.join(
                _(u'{0} (#{1})').format(child.name, child.id)
                    for child in self.children)) if self.children else u'')

    @property
    def children_by_name(self):

        return sorted(self.children, key=lowername)

    @property
    def children_tree(self):

        children = PseudoQuerySet(model=Folder)

        for child in sorted(self.children, key=lowername):
            children.append(child)
            children.extend(child.children_tree)

        #LOGGER.warning('%s children: %s > %s', self, self.children, children)

        return children

    @classmethod
    def add_folder(cls, name, user, parent=None, children=None):

        assert parent is None or isinstance(parent, cls)
        assert children is None or hasattr(children, '__iter__')

        if children is None:
            children = ()

        try:
            folder = cls(name=name, owner=user).save()

        except (NotUniqueError, DuplicateKeyError):

            folder = cls.objects.get(name=name, owner=user)

        if parent is not None:
            assert parent.owner == folder.owner

            folder.set_parent(parent)

        if children:
            for child in children:
                assert child.owner == folder.owner

                folder.add_child(child, full_reload=False)

            folder.safe_reload()

        LOGGER.info(u'Created folder %s.', folder)

    @classmethod
    def signal_pre_delete_handler(cls, sender, document, **kwargs):

        folder_to_delete = document

        if folder_to_delete.parent:
            for child in folder_to_delete.children:
                child.set_parent(folder_to_delete.parent)

        else:
            for child in folder_to_delete.children:
                child.unset_parent()


# ————————————————————————————————————————————————————————— external properties
#                                            Defined here to avoid import loops


def User_folders_property_get(self):

    return Folder.objects(owner=self)


def User_top_folders_property_get(self):

    return self.folders.filter(parent=None).order_by('name')


def User_folders_tree_property_get(self):

    folders = PseudoQuerySet(model=Folder)

    for folder in self.top_folders.order_by('name'):
        folders.append(folder)
        folders.extend(folder.children_tree)

    return folders

User.folders      = property(User_folders_property_get)
User.top_folders  = property(User_top_folders_property_get)
User.folders_tree = property(User_folders_tree_property_get)
