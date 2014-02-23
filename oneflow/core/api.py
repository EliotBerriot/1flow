# -*- coding: utf-8 -*-
"""
    Copyright 2013-2014 Olivier Cortès <oc@1flow.io>

    This file is part of the 1flow project.

    1flow is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of
    the License, or (at your option) any later version.

    1flow is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public
    License along with 1flow.  If not, see http://www.gnu.org/licenses/

"""

import logging

from tastypie_mongoengine.resources import MongoEngineResource
from tastypie_mongoengine.fields import ReferencedListField, ReferenceField

from tastypie.resources import ALL
from tastypie.fields import CharField

from .models.nonrel import (Feed, Subscription,
                            Article, Read,
                            Author, Preferences)

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


class PreferencesResource(MongoEngineResource):

    class Meta:
        queryset = Preferences.objects.all()

        # Ember-data expect the following 2 directives
        always_return_data = True
        allowed_methods    = ('get', 'post', 'put', 'delete')
        collection_name    = 'objects'
        resource_name      = 'preference'
        filtering          = {'id': ALL, }
        ordering           = ALL

        # These are specific to 1flow functionnals.
        authentication     = common_authentication
        authorization      = UserObjectsOnlyAuthorization()


__all__ = ('SubscriptionResource',
           'ReadResource', 'ArticleResource',
           'AuthorResource', 'PreferencesResource')
