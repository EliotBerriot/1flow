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


class PythonErrorClassifier(object):
    """ This object helps aggregating and grouping unique (= instance dependant)
        error strings by returning another more generic error string.

        For example, network-related errors are grouped together by themes
        (not dynamically configurable, though).
    """

    ERR_PYTHON_MAX_RECURSION = u'Python maximum recursion loop'
    ERR_NO_ERROR_STRING      = u'<NO_ERROR_STRING_PROVIDED>'

    def __init__(self, iterables=None, attribute_name=None):
        """ Calls class.reset() then class.classify(*args, **kwargs) """

        self.stored_instances = {}
        self.iterables        = iterables
        self.attribute_name   = attribute_name

    def reset(self):
        """ clears all stored instances from the class. """

        self.stored_instances = {}

    def store(self, error_string, objekt):
        """ Stores the :param:`objekt` in the
            class' :attr:`stored_instances`. """

        if error_string:
            self.stored_instances.setdefault(error_string, []).append(objekt)

    def classify(self, objekts=None, attribute_name=None):
        """ Runs :meth:`classify_one` on each member of the
            iterable :param:`objekts`. Returns a ``dict`` of the form:

                {
                        u'duration': <the duration in seconds, as integer>,
                    },
                }
        """

        start_time   = pytime.time()
        seen_objects = 0
        error_types  = {}

        if objekts is None:
            objekts = self.iterables

        if attribute_name is None:
            attribute_name = self.attribute_name

        assert objekts is not None
        assert attribute_name is not None

        for objekt in objekts:

            error = self.classify_one(getattr(objekt, attribute_name), objekt)

            error_types[error] = error_types.setdefault(error, 0) + 1
            seen_objects += 1

        return {
            u'duration': pytime.time() - start_time,
            u'seen_objects': seen_objects,
            u'error_types': error_types,
            u'stored_instances': self.stored_instances,
        }

    def classify_one(self, error_string, objekt):
        """ As the root of all classifiers, this one has a special behaviour
            to be sure *any* error gets stored in the end, if not already
            catched by any subclass.

            Thus, to create your own classifier, take example on subclasses
            implementations, but not this one.
        """

        error = None

        if error_string.startswith(u'maximum recursion'):
            error = self.ERR_PYTHON_MAX_RECURSION

        if error is None:
            error = error_string or self.ERR_NO_ERROR_STRING

        self.store(error, objekt)

        return error

    @classmethod
    def to_string(cls, results):
        """ results must be the value returned by a call
            of :meth:`classify`. """

        errors = results.get(u'error_types')

        output = (u'>> %s error types: %s distinct on %s instances, '
                  u'computed in %s\n' % (
                      cls.__name__[:-15],
                      len(errors),
                      results.get(u'seen_objects'),
                      naturaldelta(results.get(u'duration'))))

        stored = results.get('stored_instances')

        output += u'\n'.join(u'%s: %s' % (k, v) for k, v in sorted(
                             errors.items(),
                             key=operator.itemgetter(1),
                             reverse=True)) + u'\n\n'

        output += u'>> to get them, stored by error kind:\n'

        output += u'\n'.join(u'results.get("stored_instances").get("%s")'
                             % s for s in stored)

        return output


class GenericErrorClassifier(PythonErrorClassifier):

    ERR_SOFT_TIMELIMIT_EXCEEDED = u'Soft time limit exceeded'
    ERR_VALIDATION_GENERIC      = u'MongoDB Document validation error'
    ERR_VALIDATION_TAGS         = u'MongoDB Tags-related validation error'

    def classify_one(self, error_string, objekt):

        error = None

        if error_string.startswith(u'SoftTimeLimit'):
            error = self.ERR_SOFT_TIMELIMIT_EXCEEDED

        elif error_string.startswith('ValidationError'):

            if "['tags']" in error_string:
                error = self.ERR_VALIDATION_TAGS

            else:
                error = self.ERR_VALIDATION_GENERIC

        self.store(error, objekt)

        return error or super(GenericErrorClassifier,
                              self).classify_one(error_string, objekt)


class UrlErrorClassifier(GenericErrorClassifier):

    ERR_NETWORK_DOWN        = u'Network down or no route, or DNS lookup failed'
    ERR_NETWORK_CERTIFICATE = u'HTTPs certificate error'
    ERR_NETWORK_TIMEOUT     = u'Connection timeout'
    ERR_NETWORK_REFUSED     = u'Connection refused'
    ERR_NETWORK_RESET       = u'Connection reset'
    ERR_NETWORK_HTTPS_ERROR = u'Secure socket error / bad HTTPs'
    ERR_NETWORK_OTHER       = u'Other socket or HTTP Error'
    ERR_NETWORK_URLOPEN     = u'Socket/urlopen error'

    def classify_one(self, error_string, objekt):

        error = None

        if '[Errno 60] Operation timed out' in error_string:
            error = self.ERR_NETWORK_TIMEOUT

        elif '[Errno 61] Connection refused' in error_string:
            error = self.ERR_NETWORK_REFUSED

        elif '[Errno 54] Connection reset by peer' in error_string:
            error = self.ERR_NETWORK_RESET

        elif '[Errno 50] Network is down' in error_string \
            or '[Errno 8] nodename nor servname provided' in error_string \
                or '[Errno 65] No route to host' in error_string:
            error = self.ERR_NETWORK_DOWN

        elif error_string.startswith("HTTPSConnection"):
            error = self.ERR_NETWORK_HTTPS_ERROR

        elif error_string.startswith("hostname '") \
                or '_ssl.c:' in error_string:
            error = self.ERR_NETWORK_CERTIFICATE

        # Too generic for an URL error.
        #
        #elif error_string.startswith("HTTPConnection"):
        #    error = 'Socket or bad HTTP error'
        # elif error_string.startswith("HTTP "):
        #     error = 'HTTP Error'
        # elif error_string.startswith("Exceeded 30 redirects"):
        #     error = 'HTTP Error'

        elif error_string.startswith("HTTPConnection") \
            or error_string.startswith("HTTP ") \
                or error_string.startswith("Exceeded 30 redirects"):
            error = self.ERR_NETWORK_OTHER

        elif error_string.startswith("<urlopen") \
            or error_string.startswith("[Errno 104] Conn") \
            or error_string.startswith("The read operation") \
                or error_string.startswith("IncompleteRead"):
            error = self.ERR_NETWORK_URLOPEN

        self.store(error, objekt)

        return error or super(UrlErrorClassifier,
                              self).classify_one(error_string, objekt)


class ContentErrorClassifier(UrlErrorClassifier):

    ERR_ENCODING_GENERIC     = u'Encoding error'
    ERR_IMAGE_CONTENT        = u'Image instead of HTML article'
    ERR_PDF_CONTENT          = u'PDF instead of HTML article'
    ERR_AUDIO_CONTENT        = u'Audio content instead of HTML article'
    ERR_VIDEO_CONTENT        = u'Video content instead of HTML article'
    ERR_ENCODING_UNSPECIFIED = u'No encoding specified server side'

    def classify_one(self, error_string, objekt):

        error = None

        if 'codec can' in error_string:
            error = self.ERR_ENCODING_GENERIC

        #elif error_string.startswith("'charmap'"):
        #    error = u'Charmap encoding error'

        #elif error_string.startswith("'gb2312'"):
        #    error = u'gb2312 encoding error'

        elif error_string.startswith("unknown encoding: image"):
            error = self.ERR_IMAGE_CONTENT

        elif error_string.startswith(
                "unknown encoding: application/pdf"):
            error = self.ERR_PDF_CONTENT

        elif error_string.startswith("unknown encoding: audio"):
            error = self.ERR_AUDIO_CONTENT

        elif error_string.startswith("unknown encoding: video"):
            error = self.ERR_VIDEO_CONTENT

        elif error_string.startswith('unknown encoding:'):
            error = self.ERR_ENCODING_UNSPECIFIED

        self.store(error, objekt)

        return error or super(ContentErrorClassifier,
                              self).classify_one(error_string, objekt)


def article_url_error_types():

    # Next to investigate:
    #    list index out of range: 758
    #    'NoneType' object has no attribute 'findAll': 137

    return UrlErrorClassifier(
        Article.objects(url_error__ne='').no_cache(),
        'url_error'
    ).classify()


def article_url_error_types_display(results=None):

    if results is None:
        results = article_url_error_types()

    output = UrlErrorClassifier.to_string(results)

    return results, output


def article_content_error_types():

    return ContentErrorClassifier(
        Article.objects(content_error__ne='').no_cache(),
        'content_error'
    ).classify()


def article_content_error_types_display(results=None):

    if results is None:
        results = article_content_error_types()

    output = ContentErrorClassifier.to_string(results)

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
