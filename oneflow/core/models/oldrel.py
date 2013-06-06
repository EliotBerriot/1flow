# -*- coding: utf-8 -*-
#
# Models created before switching to MongoDB.
#

from jsonfield import JSONField

from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext as _

from .keyval import RelationalFeedback


class HierarchyManager(models.Manager):
    def get_roots(self):
        return self.get_query_set().filter(parent__isnull=True)


class Hierarchy(models.Model):
    """ Add the hierarchy ability to any other model. """

    parent = models.ForeignKey('self', null=True)

    tree = HierarchyManager()

    class Meta:
        abstract = True

    def get_children(self):
        return self._default_manager.filter(parent=self)

    def get_descendants(self):
        descs = set(self.get_children())
        for node in list(descs):
            descs.update(node.get_descendants())
        return descs


class NameAndSlug(models.Model):
    name = models.CharField(max_length=128)
    slug = models.CharField(max_length=128)

    class Meta:
        abstract = True


class Source(NameAndSlug):
    url         = models.URLField()
    description = models.CharField(max_length=2048)

    # TODO:
    #logo        = models.ImageField()


class Category(Hierarchy, NameAndSlug):
    class Meta:
        verbose_name_plural = _(u'Categories')


class Author(models.Model):
    name  = models.CharField(max_length=128)
    email = models.CharField(max_length=128)
    url   = models.URLField()


class Information(RelationalFeedback):
    """ Images are converted on the fly. """

    # TODO: finish this model
    source   = models.ForeignKey(Source, null=True)
    author   = models.ForeignKey(Author)
    content  = models.TextField()
    abstract = models.TextField()
    grows    = models.ManyToManyField(User, through='Grow')
    category = models.ForeignKey(Category)

    # TODO: add different dates… (creation, … ??)

    # TODO: finish this field
    tags = JSONField()


def grow_default_public_status(grow):
    return grow.user.get_profile().default_public


class Grow(RelationalFeedback):
    """ user ∞ information

         can be seen as a “ read ”, but it's much more.
    """

    # TODO: finish this model
    information = models.ForeignKey(Information)
    user        = models.ForeignKey(User)
    is_public   = models.BooleanField(default=grow_default_public_status)
