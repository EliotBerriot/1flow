# -*- coding: utf-8 -*-

import logging
import operator

from constance import config
#from mongoengine.queryset import Q
#from mongoengine.context_managers import no_dereference
from mongoengine import Document
from mongoengine.fields import IntField, DateTimeField, StringField

from django.utils.translation import ugettext_lazy as _

from oneflow.core.models import Feed, Article, global_feed_stats
from oneflow.base.utils.dateutils import (timedelta, now, pytime,
                                          naturaldelta)


LOGGER = logging.getLogger(__name__)


def feed_distribution_by_last_fetch():

    start_time = pytime.time()

    #open_feeds = Feed.objects(Q(closed=False) | Q(closed__exists=False))
    open_feeds_count = Feed.objects.filter(closed__ne=True).count()

    lower_value   = None
    loop_count    = 0
    fetched_feeds = 0
    delta_lengths = (
        timedelta(seconds=config.FEED_FETCH_DEFAULT_INTERVAL / 6),
        timedelta(seconds=config.FEED_FETCH_DEFAULT_INTERVAL / 2),
        timedelta(seconds=config.FEED_FETCH_DEFAULT_INTERVAL),
        timedelta(seconds=config.FEED_FETCH_DEFAULT_INTERVAL * 2),
        timedelta(seconds=config.FEED_FETCH_DEFAULT_INTERVAL * 6),
        timedelta(seconds=config.FEED_FETCH_DEFAULT_INTERVAL * 12),
        timedelta(days=1),
        timedelta(days=2),
        timedelta(days=3),
        timedelta(days=4),
        timedelta(days=5),
        timedelta(days=6),
        timedelta(days=7),
        timedelta(days=10),
        None
    )

    results = {}

    for delta in delta_lengths:

        upper_value = (now() - delta) if delta else None

        if lower_value is None:
            kwargs = {'last_fetch__gt': upper_value}

        elif upper_value is None:
            kwargs = {'last_fetch__lte': lower_value}

        else:
            kwargs = {'last_fetch__lte': lower_value,
                      'last_fetch__gt': upper_value}

        feeds   = Feed.objects(**kwargs)
        count   = feeds.count()
        percent = float(count * 100.0 / open_feeds_count)
        avg_fi  = sum(f.fetch_interval for f in feeds) * 1.0 / (count or 1.0)

        results[loop_count] = [
            feeds,
            count,
            percent,
            lower_value,
            upper_value,
            avg_fi,
        ]

        fetched_feeds += count
        lower_value = upper_value
        loop_count += 1

    results['meta'] = {'fetched_feeds': fetched_feeds,
                       'open_feeds_count': open_feeds_count,
                       'duration': pytime.time() - start_time,
                       'loop_count': loop_count}

    return results


def feed_distribution_by_last_fetch_display(results=None):

    if results is None:
        results = feed_distribution_by_last_fetch()

    meta = results.get('meta')

    output = u''

    for loop_count in xrange(meta.get('loop_count')):
        feeds, count, percent, lower_value, upper_value, avg_fi = \
            results.get(loop_count)

        output += u'%s feeds (%.1f%%) fetched ' % (count, float(percent))

        if lower_value is None:
            output += u'less than %s ago' % naturaldelta(upper_value)

        elif upper_value is None:
            output += u'more than %s ago' % naturaldelta(lower_value)

        else:
            output += u'between %s and %s ago' % (naturaldelta(lower_value),
                                                  naturaldelta(upper_value))

        output += (u', avg fetch interval: %s' % naturaldelta(avg_fi) +
                   (u' — in results[%s]\n' % loop_count))

    if meta['fetched_feeds'] == meta['open_feeds_count']:
        output += u'\n>>> All open feeds are beiing fetched.'
    else:
        output += (u'%s total feeds fetched, out of %s open feeds.\n'
                   u'[computed in %s]') % (
                       meta['fetched_feeds'], meta['open_feeds_count'],
                       naturaldelta(meta['duration']))

    return results, output


class ArticlesStatistic(Document):

    date_computed = DateTimeField(verbose_name=_(u'Date'))
    duration      = IntField(verbose_name=_(u'Duration'))

    total_count = IntField(verbose_name=_(u'Total'), default=0)

    empty_count = IntField(verbose_name=_(u'Empty'), default=0)
    empty_pending_count = IntField(verbose_name=_(u'Pending'), default=0)
    empty_content_error_count = IntField(verbose_name=_(u'Content errors'), default=0)
    empty_url_error_count = IntField(verbose_name=_(u'URL errors'), default=0)

    markdown_count = IntField(verbose_name=_(u'Markdown'), default=0)
    html_count = IntField(verbose_name=_(u'HTML'), default=0)
    html_content_error_count = IntField(verbose_name=_(u'Conversion errors'), default=0)

    absolute_count = IntField(verbose_name=_(u'Absolute URLs'), default=0)
    absolute_url_error_count = IntField(verbose_name=_(u'Abs. errors'), default=0)

    duplicates_count = IntField(verbose_name=_(u'Duplicates'), default=0)

    orphaned_count = IntField(verbose_name=_(u'Orphaned'), default=0)
    orphaned_url_error_count = IntField(verbose_name=_(u'Orph. URL err.'), default=0)

    time_limit_error_count = IntField(verbose_name=_(u'Time Limit err.'), default=0)

    raw_fetched_count    = IntField(verbose_name=_(u'Fetched'), default=0)
    raw_duplicates_count = IntField(verbose_name=_(u'Fetch dupl.'), default=0)
    raw_mutualized_count = IntField(verbose_name=_(u'Mutualized'), default=0)

    notes = StringField(verbose_name=_(u'Notes'))

    @classmethod
    def compute(cls, full=False):

        start_time = pytime.time()

        # Just doesn't work, produces a bunch of weird
        # 'KeyError: 'pending_articles_count'' and other
        # NoneType error due to scoping problems.
        #with no_dereference(Article) as Article:

        empty               = Article.objects(content_type=0).no_cache()
        empty_pending       = empty.filter(content_error='', url_error='')
        empty_content_error = empty.filter(content_error__ne='')
        empty_url_error     = empty.filter(url_error__ne='')

        parsed       = Article.objects(content_type__ne=0)
        parsed_error = parsed.filter(content_error__ne='').no_cache()
        html         = parsed.filter(content_type=1)
        html_error   = html.filter(content_error__ne='')

        markdown = parsed.filter(content_type=2)

        absolutes          = Article.objects(url_absolute=True).no_cache()
        duplicates         = Article.objects(duplicate_of__ne=None).no_cache()
        orphaned           = Article.objects(orphaned=True).no_cache()
        orphaned_url_error = orphaned.filter(url_error__ne='')

        kwargs = {
            'date_computed': now(),
            'total_count': Article._get_collection().count(),
            'empty_count': empty.count(),
            'empty_pending_count': empty_pending.count(),
            'empty_content_error_count': empty_content_error.count(),
            'empty_url_error_count': empty_url_error.count(),
            'parsed_error_count': parsed_error.count(),
            'parsed_count': parsed.count(),
            'html_count': html.count(),
            'html_error_count': html_error.count(),
            'markdown_count': markdown.count(),
            'raw_fetched_count': global_feed_stats.fetched(),
            'raw_duplicates_count': global_feed_stats.dupes(),
            'raw_mutualized_count': global_feed_stats.mutualized(),
        }

        if full:
            kwargs.update({
                'absolutes_count': absolutes.count(),
                'absolutes_url_error_count': absolutes.count(),
                'duplicates_count': duplicates.count(),
                'orphaned_count': orphaned.count(),
                'orphaned_url_error_count': orphaned_url_error.count(),
            })

        stat = ArticlesStatistic(**kwargs)
        stat.duration = pytime.time() - start_time

        try:
            stat.save()

        except:
            LOGGER.exception('Could not save new statistics')

        else:
            return stat

    def __unicode__(self):
        return u'Statistics generated on %s' % (self.date_computed.isoformat())


def classify_error(article):

    if 'codec can' in article.content_error:
        error = 'Encoding error'

    #elif article.content_error.startswith("'charmap'"):
    #    error = 'Charmap encoding error'

    #elif article.content_error.startswith("'gb2312'"):
    #    error = 'gb2312 encoding error'

    elif article.content_error.startswith("HTTPConnection"):
        error = 'Socket or bad HTTP error'

    elif article.content_error.startswith("HTTPSConnection"):
        error = 'Secure socket error / bad HTTPs'

    elif article.content_error.startswith("hostname '"):
        error = 'HTTPs certificate error'
    elif '_ssl.c:' in article.content_error:
        error = 'HTTPs certificate error'

    elif article.content_error.startswith("HTTP "):
        error = 'HTTP Error'
    elif article.content_error.startswith("Exceeded 30 redirects"):
        error = 'HTTP Error'

    elif article.content_error.startswith("<urlopen"):
        error = 'Socket/urlopen error'
    elif article.content_error.startswith("[Errno 104] Conn"):
        error = 'Socket/urlopen error'
    elif article.content_error.startswith("The read operation"):
        error = 'Socket/urlopen error'
    elif article.content_error.startswith("IncompleteRead"):
        error = 'Socket/urlopen error'

    elif article.content_error.startswith("unknown encoding: image"):
        error = 'Image instead of HTML article'

    elif article.content_error.startswith(
            "unknown encoding: application/pdf"):
        error = 'PDF instead of HTML article'

    elif article.content_error.startswith("unknown encoding: audio"):
        error = 'Audio content instead of HTML article'

    elif article.content_error.startswith("unknown encoding: video"):
        error = 'Video content instead of HTML article'

    elif article.content_error.startswith('unknown encoding:'):
        error = 'No encoding specified, server side'

    elif article.content_error.startswith("maximum recursion"):
        error = 'Python maximum recursion loop'

    #elif article.content_error.startswith("java.lang."):
    #    error = 'Old Java-BoilerPipe error'
    #    boiler_errors.append(article)

    else:
        error = article.content_error

    return error


def article_error_types():

    start_time     = pytime.time()
    seen_articles  = 0
    error_types    = {}
    timeout_errors = []
    codec_errors   = []
    ascii_errors   = []
    utf8_errors    = []

    # Next to investigate:
    #    list index out of range: 758
    #    'NoneType' object has no attribute 'findAll': 137

    for article in Article.objects(content_error__ne=''):

        seen_articles += 1

        if article.content_error.startswith("'ascii'"):
            ascii_errors.append(article)
            codec_errors.append(article)

        elif article.content_error.startswith("'utf8'"):
            #error = 'UTF8 encoding error'
            utf8_errors.append(article)
            codec_errors.append(article)

        elif article.content_error.startswith('SoftTimeLimit'):
            timeout_errors.append(article)

        error = classify_error(article)

        if error in error_types:
            error_types[error] += 1
        else:
            error_types[error] = 1

    return {
        'meta': {
            'duration': pytime.time() - start_time,
        },
        'error_types': error_types,
        'seen_articles': seen_articles,
        'timeout_errors': timeout_errors,
        'codec_errors': codec_errors,
        'utf8_errors': utf8_errors,
        'ascii_errors': ascii_errors,
    }


def article_error_types_display(results=None, articles_results=None):

    if results is None:
        results = article_error_types(articles_results)

    output = '>> Error types: %s (total: %s, computed in %s)\n' % (
        len(results.get('error_types')),
        results.get('seen_articles'),
        results.get('dupes_errors'),
        naturaldelta(results.get('meta').get('duration')))

    output += '\n'.join('%s: %s' % (k, v) for k, v in sorted(
                    results.get('error_types').items(),
                    key=operator.itemgetter(1),
                    reverse=True))

    return results, output
