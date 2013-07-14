# -*- coding: utf-8 -*-

import six
import time
import redis
import urllib2
import logging
import datetime

try:
    import blinker
except:
    blinker = None # NOQA

from bs4 import BeautifulSoup
from requests.packages import charade

from mongoengine import Document, signals
from django.conf import settings
from django.db import models
from django.template import Context

from djangojs.utils import ContextSerializer


LOGGER = logging.getLogger(__name__)

REDIS = redis.StrictRedis(host=getattr(settings, 'MAIN_SERVER',
                                       'localhost'), port=6379,
                          db=getattr(settings, 'REDIS_DB', 0))

now     = datetime.datetime.now
ftstamp = datetime.datetime.fromtimestamp
today   = datetime.date.today

boolcast = {
    'True': True,
    'False': False,
    'None': None,
    # The real None is needed in case of a non-existing key.
    None: None
}


# •••••••••••••••••••••••••••••••••••••••••••••••••••••• utils/helper functions


def connect_mongoengine_signals(module_globals):
    """ Automatically iterate classes of a given module and connect handlers
        to signals, given they follow the name pattern
        ``signal_<signal_name>_handler()``.

        See https://mongoengine-odm.readthedocs.org/en/latest/guide/signals.html#overview # NOQA
        for a list of valid signal names.
    """

    if blinker is None:
        LOGGER.error('blinker module is not installed, '
                     'cannot connect mongoengine signals!')
        return

    if __debug__:
        connected = 0

    for key, potential_class in module_globals.items():

        # TODO: use ReferenceDocument and other Mongo classes if appropriate?
        try:
            look_for_handlers = issubclass(potential_class, Document)

        except:
            # potential_class is definitely not a class/document ;-)
            continue

        if look_for_handlers:
            for signal_name in ('pre_init', 'post_init', 'pre_save',
                                'pre_save_post_validation', 'post_save',
                                'pre_delete', 'post_delete',
                                'pre_bulk_insert', 'post_bulk_insert'):
                handler_name = 'signal_{0}_handler'.format(signal_name)
                if hasattr(potential_class, handler_name):
                    getattr(signals, signal_name).connect(
                        getattr(potential_class, handler_name),
                        sender=potential_class)
                    if __debug__:
                        connected += 1

    if __debug__ and settings.DEBUG and connected:
        LOGGER.debug('Connected %s signal handlers to MongoEngine senders.',
                     connected)


def request_context_celery(request, *args, **kwargs):
    """ Create a standard Django :class:`Context`, and add it some useful
        things from the current RequestContext, without all the fudge. Eg.::

        - ``request.user`` becomes ``context['user']``
        - ``request.session`` becomes ``context['session']``
        - ``request.META`` becomes ``context['meta']`` (lowercase) and
          gets cleaned from non-pickable values (see later).
        - ``request.LANGUAGE_CODE`` becomes ``context['language_code']``
          if it is available in the request, else it is set to ``None``.

        With :param:`args` and :param:`kwargs`, you can pass anything you
        want to be added to the context, these arguments will be passed
        verbatim to the :class:`Context` constructor.

        This Context instance is specialy forged for celery tasks,
        and should not make them crash with :class:`PicklingError`.
        In case it still does, you can mark ``HttpRequest.META`` keys to
        be removed from the context via the ``CELERY_CONTEXT_EXPUNGE_META``
        setting directive. Defaults keys purged are::

            ('wsgi.errors', 'wsgi.input', 'wsgi.file_wrapper',
             'gunicorn.socket', )

        You can specify non-existing keys, they will just be skipped.

        .. note:: the default keys will *always* be purged. You do not need
            to add them to ``CELERY_CONTEXT_EXPUNGE_META``. Said another way
            there is currently no way to avoid expunging them, and this is
            intentional.

    """

    # TODO: i18n
    context = Context(*args, **kwargs)

    meta = request.META.copy()

    expunge_keys = getattr(settings, 'CELERY_CONTEXT_EXPUNGE_META', ())

    # We always get the basics for free.
    expunge_keys += ('wsgi.errors', 'wsgi.input', 'wsgi.file_wrapper',
                     'gunicorn.socket', )

    for key in expunge_keys:
        try:
            del meta[key]

        except KeyError:
            pass

    context.update({
                   'meta': meta,
                   'session_key': request.session.session_key,
                   'user_id': request.user.id,
                   })

    try:
        context.update({'language_code': request.LANGUAGE_CODE})

    except:
        context.update({'language_code': None})

    return context


def detect_encoding_from_requests_response(response):
    """ :param:`response` beiing a :module:`requests` response, this function
        will try to detect the encoding as much as possible. Fist, the "normal"
        response encoding will be tried, else the headers will be parsed, and
        finally the ``<head>`` of the ``<html>`` content will be parsed. If
        nothing succeeds, we will rly on :module:`charade` to guess from the
        content.

        .. todo:: we have to check if content-type is HTML before parsing the
            headers. For now you should use this function only on responses
            which you are sure they will contain HTML.
    """

    if getattr(response, 'encoding', None):
        return response.encoding

    # In case the headers don't contain an content-type, we get()
    # 'text/html' as a fallback value, which will trigger the same
    # behaviour as having a content-type header with no charset value.
    encoding = response.headers.get(
        'content-type', 'text/html').lower().split('charset=')[-1]

    if encoding.lower() == 'text/html':
        # HTTP headers don't contain any encoding.
        # Search in page head, then try to detect from data.

        html_content = BeautifulSoup(response.content, 'lxml')

        for meta_header in html_content.head.findAll('meta'):
            for attribute, value in meta_header.attrs.items():
                if attribute.lower() == 'http-equiv':
                    if value.lower() == 'content-type':
                        content  = meta_header.attrs.get('content')
                        encoding = content.lower().split('charset=')[-1]
                        break

        if encoding.lower() == 'text/html':
            # If we couldn't find an encoding in the HTML <head>,
            # try to detect it manually wth charade. This can
            # eventually fail, too… In this case, OMG… We are alone.
            try:
                return charade.detect()['encoding']
            except:
                pass

    return None

# •••••••••••••••••••••••••••••••••••••••••••••••••••••••• utils/helper classes


class JsContextSerializer(ContextSerializer):
    """ This class should probably move into sparks some day. """

    def process_social_auth(self, social_auth, data):
        """ Just force social_auth's LazyDict to be converted to a dict for the
            JSON serialization to work properly. """

        data['social_auth'] = dict(six.iteritems(social_auth))

    def handle_user(self, data):
        """ We just add the user ID to everything already gathered by Django.JS
            user serializer. """

        super(JsContextSerializer, self).handle_user(data)

        data['user']['id'] = self.request.user.id


class AlreadyLockedException(Exception):
    """ Simple Exception to notify a caller that uses RedisExpiringLock
        as a context manager that the lock could not be taken. """
    pass


class RedisExpiringLock(object):
    """ Simple lock for multi-hosted machines workers (eg. celery).
        Implemented via REDIS from http://redis.io/commands/set

        At start it was implemented via Memcache, but it doesn't work on
        development machines where cache is the DummyCache implementation.

        For commodity, if the instance has a ``fetch_interval`` attribute,
        it will be taken as the default ``expire_time`` value. If not and
        no ``expire_time`` argument is present, 3600 will be used to avoid
        persistent locks related problems.

        .. note:: **this lock can be re-entrant**: just give an
            unique :param:`lock_value` (eg. ``uuid.uuid4().hex``, to
            name only this one…), and pass it as the only argument to
            :meth:`acquire`. If the argument is equal to the lock value
            then the acquire method will return ``True``. This is a poor
            man's implementation, but should work.
    """

    REDIS     = None
    key_base  = 'rxl'
    exc_class = AlreadyLockedException

    def __init__(self, instance, lock_name=None,
                 lock_value=None, expire_time=None):

        if isinstance(instance, str):
            self.lock_id = '%s:str:%s:%s' % (self.key_base, instance,
                                             lock_name or 'giant')
            self.expire_time = expire_time or 3600

        else:
            self.lock_id = '%s:%s:%s:%s' % (self.key_base,
                                            instance.__class__.__name__,
                                            instance.id, lock_name or 'giant')
            self.expire_time = expire_time or getattr(instance,
                                                      'fetch_interval',
                                                      3600)

        self.lock_value  = ('locked_by:%s' % lock_value
                            ) if lock_value else 'locked'

    def __enter__(self):
        if not self.acquire():
            raise self.exc_class()

    def __exit__(self, *a, **kw):
        return self.release()

    def acquire(self, reentrant_id=None):
        """ We implement the re-entrant lock with a poor-man's solution:
            In case of an already taken lock, if the new acquirer's ID
            equals the lock_value, we return ``True``.

            There is still a risk of race condition because the current
            method is not guaranteed to run atomically, but it's small
            in a multi-node networked environment.
        """
        val = self.REDIS.set(self.lock_id, self.lock_value,
                             ex=self.expire_time, nx=True)

        if reentrant_id:
            return val or val[10:] == reentrant_id

        return val

    def release(self):
        val = self.REDIS.get(self.lock_id)

        if val == self.lock_value:
            self.REDIS.delete(self.lock_id)
            return True

        return False

    def is_locked(self):
        """ OMG this method costs so much,
            and can even have a race condition.
            Hope we don't need it too often.
        """

        if self.acquire():
            self.release()
            return True
        return False

# By default take the normal REDIS connection, but still allow
# to override it in tests via the class attribute.
RedisExpiringLock.REDIS = REDIS


class NoResourceAvailableException(Exception):
    """ Raised by the RedisSemaphore when the limit is reached. """

    pass


class RedisSemaphore(RedisExpiringLock):
    """ A simple but networked-machines-safe semaphore implementation.

        .. warning:: as this class inherits from :class:`RedisExpiringLock`,
            it has the automagic ability to make the semaphore expire after
            the default expiration period.

            This is OK for me because the Sem should be used to avoid
            concurrent requests in a short period of time, and should
            expire automatically to avoid problems with dead tasks.

            But, this can be surprising, and could probably lead to
            some frustration some day…
    """

    REDIS     = None
    key_base  = 'rsm'
    exc_class = NoResourceAvailableException

    def __init__(self, instance, resources_number=None):
        super(RedisSemaphore, self).__init__(instance=instance)

        #
        # NOT A GOOD Idea to reset semaphore at instanciation,
        # parallel workers have different instances of it.
        #
        self.sem_limit = resources_number or 1

        #LOGGER.warning('SEMinit: %s %s', self.lock_id, self.holders())

    def acquire(self):

        #LOGGER.warning('>> ACQUIRE before: %s', self.holders())

        val = self.REDIS.incr(self.lock_id)

        #LOGGER.warning('>> ACQUIRE after: %s', self.holders())

        if val <= self.sem_limit:
            return True

        else:
            #LOGGER.warning('>> WILL -1: %s', self.holders())

            self.release()
            return False

    def release(self):

        #LOGGER.warning('>> RELEASE before: %s', self.REDIS.get(self.lock_id))

        val = self.REDIS.decr(self.lock_id)

        #LOGGER.warning('>> RELEASE after: %s', val)

        if val < 0:
            # This should happen only during test, but just in case…
            LOGGER.warning(u'Semaphore value %s is under zero (%s), resetting.',
                           self.lock_id, val)
            self.REDIS.set(self.lock_id, 0)
            return False

        return True

    def set_limit(self, limit=None):

        if limit is None:
            limit = self.holders() + 1

        if self.sem_limit != limit:
            LOGGER.info('Semaphore %s limit changed from %s to %s.',
                        self.lock_id, self.sem_limit, limit)
            self.sem_limit = limit

        return limit

    def holders(self):
        # LOGGER.warning('>> HOLDERS: %s %s', self.lock_id,
        #                int(self.REDIS.get(self.lock_id) or 0))
        return int(self.REDIS.get(self.lock_id) or 0)


# By default take the normal REDIS connection, but still allow
# to override it in tests via the class attribute.
RedisSemaphore.REDIS = REDIS


class HttpResponseLogProcessor(urllib2.BaseHandler):
        """ urllib2 processor that maintains a log of HTTP responses.
            See http://code.google.com/p/feedparser/issues/detail?id=390
            For why it exists.
        """

        # Run after anything that's mangling headers (usually 500 or less),
        # but before HTTPErrorProcessor (1000).
        handler_order = 900

        def __init__(self):
            self.log = []

        def http_response(self, req, response):
            entry = {
                "url": req.get_full_url(),
                "status": response.getcode(),
            }
            location = response.info().get("Location")

            if location is not None:
                entry["location"] = location

            self.log.append(entry)

            return response

        https_response = http_response


class RedisStatsCounter(object):
    """ A small statistics counter implemented on top of REDIS. Meant to
        be replaced by a full-featured StatsD implementation at some point
        in the future.

        We explicitely need to cast return values. See
        http://stackoverflow.com/a/13060733/654755 for details. It should
        normally not be needed (cf.
        https://github.com/andymccurdy/redis-py#response-callbacks) but
        for an unknown reason it drove me crazy and I finally re-casted
        them again to make the whole thing work.
    """
    REDIS      = None
    GLOBAL_KEY = 'gbl'

    def __init__(self, *args, **kwargs):

        # This could clash with a pure Django model because IDs overlap
        # from one model to another. It doesn't with MongoDB documents,
        # where IDs are unique accross the whole database.
        if __debug__ and args:
            assert not isinstance(args[0], models.Model)

        self.instance_id = (args[0].id if isinstance(args[0], Document)
                            else args[0]
                            ) if args else RedisStatsCounter.GLOBAL_KEY

        try:
            self.key_base = '{0}:{1}'.format(self.__class__.key_base,
                                             self.instance_id)
        except AttributeError:
            raise RuntimeError(u'RedisStatsCounter is an abstract class. '
                               u'You should not use it directly but '
                               u'rather create your own stats class '
                               u'with a `cls.key_base` attribute.')

    @classmethod
    def _time_key(cls, key, set_time=False, time_value=None):

        if set_time:
            return cls.REDIS.set(key, time.time()
                                 if time_value is None else time_value)

        return ftstamp(float(cls.REDIS.get(key) or 0.0))

    @classmethod
    def _int_incr_key(cls, key, increment=False):

        if increment == 'reset':
            # return, else we increment to 1…
            return cls.REDIS.delete(key)

        if increment:
            return int(cls.REDIS.incr(key))

        return int(cls.REDIS.get(key) or 0)

    @classmethod
    def _int_set_key(cls, key, set_value=None):

        if set_value is None:
            return int(cls.REDIS.get(key) or 0)

        return cls.REDIS.set(key, set_value)

    def running(self, set_running=None):

        key = self.key_base + ':run'

        # Just to be sure we need to cast…
        # LOGGER.warning('running: set=%s, value=%s type=%s',
        #                set_running, self.REDIS.get(self.key_base),
        #                type(self.REDIS.get(self.key_base)))

        if set_running is None:
            return boolcast[RedisStatsCounter.REDIS.get(key)]

        return RedisStatsCounter.REDIS.set(key, set_running)

# By default take the normal REDIS connection, but still allow
# to override it in tests via the class attribute.
RedisStatsCounter.REDIS = REDIS
