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

from celery import task
from statsd import statsd

from pymongo.errors import DuplicateKeyError

from mongoengine import Document, NULLIFY
from mongoengine.fields import StringField, ReferenceField, URLField
from mongoengine.errors import ValidationError, NotUniqueError

from django.conf import settings
from django.utils.text import slugify
from django.utils.translation import ugettext_lazy as _

from .common import DocumentHelperMixin

LOGGER = logging.getLogger(__name__)


__all__ = ('website_post_create_task', 'WebSite', )


@task(name='WebSite.post_create', queue='high')
def website_post_create_task(website_id):

    website = WebSite.objects.get(id=website_id)
    website.post_create_task()


class WebSite(Document, DocumentHelperMixin):
    """ Simple representation of a web site. Holds options for it.


    .. todo::
        - replace Feed.site_url by Feed.website
        - set_fetch_limit goes into website (can be common to many feeds)
    """

    name = StringField()
    slug = StringField(verbose_name=_(u'slug'))
    url  = URLField(unique=True)
    duplicate_of = ReferenceField('WebSite',
                                  reverse_delete_rule=NULLIFY)

    def __unicode__(self):
        return u'%s #%s (%s)%s' % (self.name or u'<UNSET>', self.id, self.url,
                                   (_(u'(dupe of #%s)') % self.duplicate_of.id)
                                   if self.duplicate_of else u'')

    @staticmethod
    def split_url(url, split_port=False):

        proto, remaining = url.split('://', 1)

        try:
            host_and_port, remaining = remaining.split('/', 1)

        except ValueError:
            host_and_port = remaining
            remaining     = u''

        if split_port:
            try:
                hostname, port = host_and_port.split(':')

            except ValueError:
                hostname = host_and_port
                port = '80' if proto == 'http' else '443'

            return proto, hostname, int(port), remaining

        return proto, host_and_port, remaining

    @classmethod
    def get_from_url(cls, url):
        """ Will get you the ``WebSite`` object from an :param:`url`, after
            having striped down the path part
            (eg. ``http://test.com/my-article`` gives you the web
             site ``http://test.com``, without the trailing slash).

            .. note:: unlike :meth:`get_or_create_website`, this method will
                harmonize urls: ``WebSite.get_from_url('http://toto.com')``
                and  ``WebSite.get_from_url('http://toto.com/')`` will give
                you back the same result. This is intended, to avoid
                duplication.

        """
        try:
            proto, host_and_port, remaining = WebSite.split_url(url)

        except:
            LOGGER.exception('Unable to determine Website from "%s"', url)
            return None

        else:
            base_url = '%s://%s' % (proto, host_and_port)

            try:
                website, _ = WebSite.get_or_create_website(base_url)

            except ValidationError:
                LOGGER.exception('Cannot create website from url %s (via '
                                 u'original %s)', base_url, url)
                return None

            return website

    @classmethod
    def get_or_create_website(cls, url):
        """

            .. warning:: will always return the *master* :class:`WebSite`
                if the found one is a duplicate (eg. never returns the
                duplicate one).
        """

        try:
            website = cls.objects.get(url=url)

        except cls.DoesNotExist:
            try:
                return cls(url=url).save(), True

            except (NotUniqueError, DuplicateKeyError):
                # We just hit the race condition with two creations
                # At the same time. Same player shoots again.
                website = cls.objects.get(url=url)

        return website.duplicate_of or website, False

    @classmethod
    def signal_post_save_handler(cls, sender, document,
                                 created=False, **kwargs):

        website = document

        if created:
            if not website.duplicate_of:
                # We don't run the post_create() task in the archive
                # database: the article is already complete.
                if website._db_name != settings.MONGODB_NAME_ARCHIVE:
                    website_post_create_task.delay(website.id)

    def post_create_task(self):
        """ Method meant to be run from a celery task. """

        if not self.slug:
            if self.name is None:
                proto, host_and_port, remaining = WebSite.split_url(self.url)
                self.name = host_and_port.replace(u'_', u' ').title()

            self.slug = slugify(self.name)

            self.save()

            statsd.gauge('websites.counts.total', 1, delta=True)
