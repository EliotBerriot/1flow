# -*- coding: utf-8 -*-

import logging

import time as pytime

from constance import config
#from mongoengine.queryset import Q
from mongoengine.context_managers import no_dereference

from oneflow.core.models import Feed, Article, global_feed_stats
from oneflow.base.utils.dateutils import timedelta, now, naturaldelta


LOGGER = logging.getLogger(__name__)


def feed_distribution_by_last_fetch():

    start_time = pytime.time()

    #open_feeds = Feed.objects(Q(closed=False) | Q(closed__exists=False))
    open_feeds_count = Feed.objects.filter(closed__ne=True).count()

    lower_value   = None
    loop_count    = 0
    fetched_feeds = 0
    delta_lengths = (
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


def article_current_numbers():

    start_time = pytime.time()

    global Article

    with no_dereference(Article) as Article:
        # empty_articles is looped 2 times: cache it.
        empty_articles    = Article.objects(content_type=0)
        pending_articles  = empty_articles.filter(
            content_error__exists=False).no_cache()
        error_articles    = empty_articles.filter(
            content_error__exists=True).no_cache()
        unparsed_articles = Article.objects(
            content_type__exists=False).no_cache()
        error2_articles   = Article.objects(
            content_error__exists=True).no_cache()
        html_articles     = Article.objects(content_type=1).no_cache()
        markdown_articles = Article.objects(content_type=2).no_cache()

    return {
        'empty_articles': empty_articles,
        'pending_articles': pending_articles,
        'error_articles': error_articles,
        'unparsed_articles': unparsed_articles,
        'error2_articles': error2_articles,
        'html_articles': html_articles,
        'markdown_articles': markdown_articles,

        'total_articles_count': Article._get_collection().count(),
        # empty_articles is not counted.
        'unparsed_articles_count': unparsed_articles.count(),
        'pending_articles_count': pending_articles.count(),
        'error_articles_count': error_articles.count(),
        'error2_articles_count': error2_articles.count(),
        'html_articles_count': html_articles.count(),
        'markdown_articles_count': markdown_articles.count(),
        'meta': {'duration': timedelta(pytime.time() - start_time)}
    }


def article_current_numbers_display(results=None):

    if results is None:
        results = article_current_numbers()

    # display
    return results, (u'- %s: pending: %s, errors: %s/%s, md: %s, '
                     u'html: %s, unparsed: %s, total: %s; fetched: %s, '
                     u'dupes: %s, mutualized: %s, computed in %s') % (
                         pytime.strftime('%Y%m%d %H:%M'),
                         results['pending_articles_count'],
                         results['error_articles_count'],
                         results['error2_articles_count'],
                         results['markdown_articles_count'],
                         results['html_articles_count'],
                         results['unparsed_articles_count'],
                         results['total_articles_count'],
                         global_feed_stats.fetched(),
                         global_feed_stats.dupes(),
                         global_feed_stats.mutualized(),
                         naturaldelta(results['meta']['duration']))


def article_error_types():
    # TODO:


    start_time     = pytime.time()
    error_types    = {}
    dupes_errors   = 0
    seen_articles  = []

    codec_errors   = []
    timeout_errors = []
    utf8_errors    = []
    ascii_errors   = []
    #boiler_errors  = []

    # Next to investigate:
    #    list index out of range: 758
    #    'NoneType' object has no attribute 'findAll': 137

    for bunch in (error_articles, error2_articles):
        for article in bunch:
            if article.id in seen_articles:
                dupes_errors += 1
                continue

            seen_articles.append(article.id)

            if article.content_error.startswith("'ascii'"):
                ascii_errors.append(article)
            elif article.content_error.startswith("'utf8'"):
                #error = 'UTF8 encoding error'
                utf8_errors.append(article)

            if 'codec can' in article.content_error:
                error = 'Encoding error'
                codec_errors.append(article)

            #elif article.content_error.startswith("'charmap'"):
            #    error = 'Charmap encoding error'

            #elif article.content_error.startswith("'gb2312'"):
            #    error = 'gb2312 encoding error'

            elif article.content_error.startswith('SoftTimeLimit'):
                error = article.content_error
                timeout_errors.append(article)

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

            elif article.content_error.startswith("unknown encoding: application/pdf"):
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

            if error in error_types:
                error_types[error] +=1
            else:
                error_types[error] = 1

    duration = timedelta(seconds=pytime.time() - start_time)

    print '>> Error types: %s (total: %s, dupes: %s, computed in %s)\n' % (
        len(error_types), len(seen_articles), dupes_errors, naturaldelta(duration)), \
        '\n'.join('%s: %s' % (k, v) for k,v in sorted(error_types.items(),
            key=operator.itemgetter(1), reverse=True))
