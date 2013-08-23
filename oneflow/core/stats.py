# -*- coding: utf-8 -*-

import logging
import operator

from statsd import statsd
from constance import config
#from mongoengine.queryset import Q
#from mongoengine.context_managers import no_dereference

from oneflow.core.models import (Tag, Feed, Article, Author, WebSite,
                                 CONTENT_TYPE_NONE,
                                 CONTENT_TYPE_HTML,
                                 CONTENT_TYPE_MARKDOWN,
                                 )
from oneflow.base.utils.dateutils import (timedelta, now, pytime,
                                          naturaldelta, benchmark)


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


def synchronize_statsd_articles_gauges(full=False):

    with benchmark('synchronize statsd gauges for Article.*'):

        empty               = Article.objects(content_type=0).no_cache()
        #empty_pending       = empty.filter(content_error='', url_error='')
        #empty_content_error = empty.filter(content_error__ne='')
        #empty_url_error     = empty.filter(url_error__ne='')

        parsed             = Article.objects(content_type__ne=CONTENT_TYPE_NONE)
        html               = parsed.filter(content_type=CONTENT_TYPE_HTML)
        markdown           = parsed.filter(content_type=CONTENT_TYPE_MARKDOWN)

        absolutes          = Article.objects(url_absolute=True).no_cache()
        duplicates         = Article.objects(duplicate_of__ne=None).no_cache()
        orphaned           = Article.objects(orphaned=True).no_cache()
        content_errors     = Article.objects(content_error__ne='').no_cache()
        url_errors         = Article.objects(url_error__ne='').no_cache()

        statsd.gauge('articles.counts.total', Article._get_collection().count())
        statsd.gauge('articles.counts.markdown', markdown.count())
        statsd.gauge('articles.counts.html', html.count())
        statsd.gauge('articles.counts.empty', empty.count())
        statsd.gauge('articles.counts.content_errors', content_errors.count())
        statsd.gauge('articles.counts.url_errors', url_errors.count())

        if full:
            statsd.gauge('articles.counts.orphaned', orphaned.count())
            statsd.gauge('articles.counts.absolutes', absolutes.count())
            statsd.gauge('articles.counts.duplicates', duplicates.count())


def synchronize_statsd_tags_gauges(full=False):

    with benchmark('synchronize statsd gauges for Tag.*'):

        statsd.gauge('tags.counts.total', Tag._get_collection().count())

        if full:
            duplicates = Tag.objects(duplicate_of__ne=None).no_cache()
            statsd.gauge('tags.counts.duplicates', duplicates.count())


def synchronize_statsd_websites_gauges(full=False):

    with benchmark('synchronize statsd gauges for WebSite.*'):

        statsd.gauge('websites.counts.total', WebSite._get_collection().count())

        if full:
            duplicates = WebSite.objects(duplicate_of__ne=None).no_cache()
            statsd.gauge('websites.counts.duplicates', duplicates.count())


def synchronize_statsd_authors_gauges(full=False):

    with benchmark('synchronize statsd gauges for Author.*'):

        statsd.gauge('authors.counts.total', Author._get_collection().count())

        if full:
            duplicates = Author.objects(duplicate_of__ne=None).no_cache()
            statsd.gauge('authors.counts.duplicates', duplicates.count())


def synchronize_statsd_gauges(full=False):
    synchronize_statsd_articles_gauges(full=full)
    synchronize_statsd_tags_gauges(full=full)
    synchronize_statsd_websites_gauges(full=full)
    synchronize_statsd_authors_gauges(full=full)
