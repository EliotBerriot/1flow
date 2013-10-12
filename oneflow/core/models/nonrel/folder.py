# -*- coding: utf-8 -*-

import logging

from pymongo.errors import DuplicateKeyError

from mongoengine import Document, NULLIFY, CASCADE, PULL
from mongoengine.fields import StringField, ReferenceField, ListField
from mongoengine.errors import NotUniqueError, ValidationError, DoesNotExist

from django.utils.translation import ugettext_lazy as _

from ....base.fields import IntRedisDescriptor

from .common import (DocumentHelperMixin, DocumentTreeMixin,
                     PseudoQuerySet, lowername)
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
    name  = StringField(verbose_name=_(u'Name'),
                        unique_with=['owner', 'parent'])
    owner = ReferenceField('User', verbose_name=_(u'Owner'),
                           reverse_delete_rule=CASCADE)

    parent = ReferenceField('self', verbose_name=_(u'Parent'),
                            reverse_delete_rule=NULLIFY, required=False)
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
        return _(u'{0} (#{1}) for user {2}{3}{4}').format(
            self.name, self.id, self.owner,
            _(u', parent: {0} (#{1})').format(self.parent.name, self.parent.id)
                if self.parent else u'',
            _(u', children: {0}').format(u', '.join(
                _(u'{0} (#{1})').format(child.name, child.id)
                    for child in self.children))
                        if self.children != [] else u'')

    @classmethod
    def get_root_for(cls, user):

        try:
            return cls.objects.get(name=u'__root__', owner=user)

        except DoesNotExist:
            return cls(name=u'__root__', owner=user).save()

    def validate(self, *args, **kwargs):

        try:
            super(Folder, self).validate(*args, **kwargs)

        except ValidationError as e:
            parent_error = e.errors.get('parent', None)

            if parent_error and str(parent_error).startswith('Field is requi'):
                # Allow the creation of the root folder whatever it costs,
                # else we cannot create any directory (chicken & egg pbm).
                if self.name == u'__root__':
                    e.errors.pop('parent')

            if e.errors:
                raise e

    @classmethod
    def add_folder(cls, name, user, parent=None, children=None):

        assert parent is None or isinstance(parent, cls)
        assert children is None or hasattr(children, '__iter__')

        if children is None:
            children = ()

        if parent is None:
            parent = cls.get_root_for(user)

        try:
            folder = cls(name=name, owner=user, parent=parent).save()

        except (NotUniqueError, DuplicateKeyError):
            folder = cls.objects.get(name=name, owner=user, parent=parent)

        else:
            # If the folder exists [with the same parent], no
            # need to add it as child, it's already the case.
            parent.add_child(folder, update_reverse_link=False)

        if children:
            for child in children:
                assert child.owner == folder.owner

                folder.add_child(child, full_reload=False)

            folder.reload()

        LOGGER.info(u'Created folder %s.', folder)

        return folder

    @classmethod
    def signal_pre_delete_handler(cls, sender, document, **kwargs):

        folder_to_delete = document

        if folder_to_delete.parent:
            for child in folder_to_delete.children:
                child.set_parent(folder_to_delete.parent)

        else:
            for child in folder_to_delete.children:
                child.unset_parent()

    @property
    def max_depth(self):

        return 5 if self.owner.preferences.selector.extended_folders_depth \
                else 3

    def get_subfolders(self, current_level):

        if current_level >= self.max_depth:
            return PseudoQuerySet()

        children = PseudoQuerySet(model=self.__class__)

        for child in sorted(self.children, key=lowername):
            children.append(child)
            children.extend(child.get_subfolders(current_level + 1))

        return children


# ————————————————————————————————————————————————————————— external properties
#                                            Defined here to avoid import loops


def User_folders_property_get(self):

    return Folder.objects(owner=self, parent__ne=None)


def User_root_folder_property_get(self):

    return Folder.get_root_for(self)


def User_top_folders_property_get(self):

    return self.folders.filter(parent=self.root_folder).order_by('name')


def User_folders_tree_property_get(self):
    """ Returns the full (but preference-via
        depth-limited) user folders tree as a list. """

    return self.get_folders_tree()


def User_get_folders_tree_method(self, for_parent=False):

    folders = PseudoQuerySet(model=Folder)

    # Articificialy increment the level by one to limit the folder
    # tree to the N-1 levels. This clamps the folder manager modal.
    level = 1 if for_parent else 0

    for folder in self.top_folders.order_by('name'):
        folders.append(folder)
        folders.extend(folder.get_subfolders(level + 1))

    return folders


User.folders          = property(User_folders_property_get)
User.root_folder      = property(User_root_folder_property_get)
User.top_folders      = property(User_top_folders_property_get)
User.folders_tree     = property(User_folders_tree_property_get)
User.get_folders_tree = User_get_folders_tree_method
