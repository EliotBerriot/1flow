# -*- coding: utf-8 -*-
"""
    Copyright 2012-2014 Olivier Cortès <oc@1flow.io>

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

from django.contrib.sites import models
from django.db.models import signals
from django.conf import settings


LOGGER = logging.getLogger(__name__)


def create_site(app, created_models, verbosity, **kwargs):
    """ Create the default site when when we install the sites framework. """

    try:
        site = models.Site.objects.get(pk=settings.SITE_ID)

    except models.Site.DoesNotExist:
        site = models.Site.objects.create(pk=settings.SITE_ID,
                                          name=settings.SITE_NAME,
                                          domain=settings.SITE_DOMAIN)
        site.save()

        LOGGER.debug('Site created: %s', site)

    else:
        # update Django's example.com with our real data.
        site.name   = settings.SITE_NAME
        site.domain = settings.SITE_DOMAIN
        site.save()

        LOGGER.debug('Site updated: %s', site)


signals.post_syncdb.connect(create_site, sender=models)
