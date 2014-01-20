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
import simplejson as json

from django.core.management.base import BaseCommand

from oneflow.core.models.nonrel import Article
from oneflow.base.utils.dateutils import ftstamp

LOGGER = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'set date_published for all articles who have GR original data.'

    def handle(self, *args, **options):
        """ In 0.14.14 I fixed the `date_published` not beeing set on articles.
            With this management command I set the date for already imported.
        """

        UNICODE = type(u'')
        done    = 0
        errors  = 0

        for article in Article.objects.filter(
                google_reader_original_data__exists=True):

            #self.stdout.write('On %s (%s) => %s.' % (
            #    article.title, article.id,
            #    type(article.google_reader_original_data)))

            data = article.google_reader_original_data

            if type(data) == UNICODE:
                data = json.loads(data)

            timestamp = (int(data.get('timestampUsec', 0)) / 1000000
                         ) or int(data.get('crawlTimeMsec')) / 1000

            article.google_reader_original_data = json.dumps(data)
            article.date_published = ftstamp(timestamp)
            try:
                article.save()

            except:
                LOGGER.exception('Could not save article “%s” (id: %s)',
                                 article.title, article.id)
                errors += 1
            else:
                done += 1

        self.stdout.write('Set `date_published` on %s articles with %s errors.'
                          % (done, errors))
