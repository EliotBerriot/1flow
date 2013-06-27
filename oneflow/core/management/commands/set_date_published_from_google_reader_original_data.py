# -*- coding: utf-8 -*-

import logging
import datetime
import simplejson as json

from django.core.management.base import BaseCommand

from oneflow.core.models.nonrel import Article

LOGGER = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'set date_published for all articles who have GR original data.'

    def handle(self, *args, **options):
        """ In 0.14.14 I fixed the `date_published` not beeing set on articles.
            With this management command I set the date for already imported.
        """

        ftstamp = datetime.datetime.fromtimestamp
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
