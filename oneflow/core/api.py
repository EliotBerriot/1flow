# -*- coding: utf-8 -*-

import logging

from tastypie_mongoengine.resources import MongoEngineResource
from tastypie_mongoengine.fields import ReferencedListField, ReferenceField

from tastypie.resources import ALL
from tastypie.fields import CharField

from .models.nonrel import Subscription, Feed, Article, Read, Author

from ..base.api import (UserResource,
                        common_authentication,
                        UserObjectsOnlyAuthorization, )

LOGGER = logging.getLogger(__name__)


class FeedResource(MongoEngineResource):

    class Meta:
        queryset = Feed.objects.all()

        # Ember-data expect the following 2 directives
        always_return_data = True
        allowed_methods    = ('get', 'post', 'put', 'delete')

        # These are specific to 1flow functionnals.
        authentication     = common_authentication
        authorization      = UserObjectsOnlyAuthorization()


class SubscriptionResource(MongoEngineResource):
    feed_id = ReferenceField(FeedResource, 'feed')

    class Meta:
        queryset = Subscription.objects.all()

        # Ember-data expect the following 2 directives
        always_return_data = True
        allowed_methods    = ('get', 'post', 'put', 'delete')

        # These are specific to 1flow functionnals.
        authentication     = common_authentication
        authorization      = UserObjectsOnlyAuthorization()


class AuthorResource(MongoEngineResource):

    class Meta:
        queryset = Author.objects.all()

        # Ember-data expect the following 2 directives
        always_return_data = True
        allowed_methods    = ('get', 'post', 'put', 'delete')
        collection_name    = 'objects'
        resource_name      = 'author'
        filtering          = {'id': ALL, }
        ordering           = ALL
        # These are specific to 1flow functionnals.
        authentication     = common_authentication
        #authorization      = UserObjectsOnlyAuthorization()


class ArticleResource(MongoEngineResource):

    author_ids = ReferencedListField(AuthorResource, 'authors', null=True)

    # Gosh. "url" is reserved in EmberJS… We need to map our
    # internal `Article.url` to Ember's `Article.public_url`.
    public_url = CharField(attribute='url', readonly=True)

    class Meta:
        queryset = Article.objects.all()

        # Ember-data expect the following 2 directives
        always_return_data = True
        allowed_methods    = ('get', 'post', 'put', 'delete', )
        collection_name    = 'objects'
        resource_name      = 'article'
        filtering          = {'id': ALL, }
        ordering           = ALL
        excludes           = ('pages_urls', 'authors', 'url', )

        # These are specific to 1flow functionnals.
        authentication     = common_authentication
        #authorization      = UserObjectsOnlyAuthorization()


class ReadResource(MongoEngineResource):
    article_id = ReferenceField(ArticleResource, 'article')
    user_id    = ReferenceField(UserResource, 'user')

    class Meta:
        #queryset = Read.objects.filter(date_read=now)
        queryset = Read.objects.all()

        # Ember-data expect the following 2 directives
        always_return_data = True
        allowed_methods    = ('get', 'post', 'put', 'delete')
        collection_name    = 'objects'
        resource_name      = 'read'
        filtering          = {'id': ALL, 'is_read': ALL, }
        ordering           = ALL
        excludes           = ('article', 'user', )

        # These are specific to 1flow functionnals.
        authentication     = common_authentication
        authorization      = UserObjectsOnlyAuthorization()


__all__ = ('SubscriptionResource',
           'ReadResource', 'ArticleResource',
           'AuthorResource', )
