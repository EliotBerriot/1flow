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

#import ast
import uuid
import redis

#from jsonfield import JSONField
from transmeta import TransMeta

from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils.translation import ugettext as _
from django.utils.text import slugify

#from django.db.models import Q
#from django.db.models.aggregates import Count
#from django.utils import dateformat
#from django.contrib.sites.models import Site
#from django.template.defaultfilters import slugify

REDIS = redis.StrictRedis(host=settings.REDIS_HOST,
                          port=settings.REDIS_PORT,
                          db=settings.REDIS_DB)

DjangoUser = get_user_model()


class HelpContent(models.Model):
    __metaclass__ = TransMeta

    label = models.CharField(_(u'Help section label'),
                             max_length=128, unique=True,
                             help_text=_(u'Any text. Will NOT show '
                                         u'anywhere, but is used to '
                                         u'distinguish sections from '
                                         u'one another.'))
    ordering = models.IntegerField(_(u'Ordering'), help_text=_(u'An integer '
                                   u'that will be used to order help sections '
                                   u'on the help page.'), default=0)
    active = models.BooleanField(default=True, help_text=_(u'is this help '
                                 u'section currently displayed on the '
                                 u'website?'))
    name    = models.CharField(_(u'Help section name'), max_length=128,
                               help_text=_(u'Any text. Will be the title '
                                           u'of the help section.'))
    content = models.TextField(_(u'Help section content'),
                               help_text=_(u'Any text. Entered as Markdown.'))

    def __unicode__(self):
        return _(u'{field_name}: {truncated_field_value}').format(
            field_name=self.label, truncated_field_value=self.content[:30]
            + (self.content[30:] and u'…'))

    @property
    def slug(self):
        return slugify(self.name) or uuid.uuid4().hex

    class Meta:
        app_label = 'core'
        ordering = ['ordering', 'id']
        translate = ('name', 'content', )
        verbose_name = _(u'Help section')
        verbose_name_plural = _(u'Help contents')
