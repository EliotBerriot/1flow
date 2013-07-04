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

from mongoengine import Document, signals
from django.conf import settings
from django.template import Context, Template
from django.utils import translation
from django.contrib.auth import get_user_model
from djangojs.utils import ContextSerializer

from sparks.django import mail

from ..landing.models import LandingUser
from .models import EmailContent

LOGGER = logging.getLogger(__name__)
User = get_user_model()

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
                    connected += 1

    if connected:
        LOGGER.info('Connected %s signal handlers to MongoEngine senders.',
                    connected)


def get_user_and_update_context(context):

    # If there is no new user, it's not a registration, we
    # just get the context user, to fill email fields.

    if 'new_user_id' in context:
        user = LandingUser.objects.get(id=context['new_user_id'])
        context['new_user'] = user

    else:
        user = User.objects.get(id=context['user_id'])

    context['user'] = user

    return user


def send_email_with_db_content(context, email_template_name, **kwargs):
    """

        :param context: can contain ``new_user`` in case of a new user
            registration. If not, the ``context['user']`` will be used.
    """

    def post_send(user, email_template_name):
        # TODO: implement me for real!
        #   I just wrote this function the way I wanted it to act,
        #   but user.log_email_sent() doesn't exist yet.

        def post_send_log_mail_sent():
            user.log_email_sent(email_template_name)

        return post_send_log_mail_sent

    user = get_user_and_update_context(context)

    if user.has_email_sent(email_template_name) \
            and not kwargs.get('force', False):
        LOGGER.info(u'User %s already received email “%s”, skipped.',
                    user.username, email_template_name)
        return

    lang = context.get('language_code')

    if lang is not None:
        # switch to the user language
        old_lang = translation.get_language()

        if old_lang != lang:
            translation.activate(lang)

        else:
            old_lang = None
    else:
        old_lang = None

    try:
        context.update({'unsubscribe_url': user.unsubscribe_url()})

    except:
        # In case we are used without the profiles Django app.
        LOGGER.exception('Cannot update the context with `unsubscribe_url`.')

    email_data      = EmailContent.objects.get(name=email_template_name)
    email_footer    = EmailContent.objects.get(name='email_footer')

    # Pre-render templates for the mail HTML content.
    # email subject is mapped to <title> and <h1>.
    stemplate     = Template(email_data.subject)
    email_subject = stemplate.render(context)
    btemplate     = Template(email_data.body)
    email_body    = btemplate.render(context)
    ftemplate     = Template(email_footer.body)
    email_footer  = ftemplate.render(context)

    # Update for the second rendering pass (Markdown in Django)
    context.update({'email_subject': email_subject,
                   'email_body': email_body,
                   'email_footer': email_footer})

    mail.send_mail_html_from_template(
        'emails/email_with_db_content.html',
        # We intentionaly pass the unrendered subject string,
        # because it will be rendered independantly in the
        # send_mail… function (cf. there for details).
        subject=email_data.subject,
        recipients=[user.email],
        context=context,
        # TODO: pass the log_email_sent() as post_send callable
        #post_send=post_send(user)
        **kwargs)

    # TODO: remove this when log_email_sent is passed to send_mail*()
    user.log_email_sent(email_template_name)

    if old_lang is not None:
        # Return to application main language
        translation.activate(old_lang)

    LOGGER.info('Batched %s mail to send to %s.',
                email_template_name, user.email)


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


# •••••••••••••••••••••••••••••••••••••••••••••••••••••• utils/helper functions


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
    """ Simple Exception to notify a caller that uses SimpleCacheLock
        as a context manager that the lock could not be taken. """
    pass


class SimpleCacheLock(object):
    """ Simple lock for multi-hosted machines workers (eg. celery).
        Implemented via REDIS from http://redis.io/commands/set

        At start it was implemented via Memcache, but it doesn't work on
        development machines where cache is the DummyCache implementation.

        For commodity, if the instance has a ``fetch_interval`` attribute,
        it will be taken as the default ``expire_time`` value. If not and
        no ``expire_time`` argument is present, 3600 will be used to avoid
        persistent locks related problems.
    """

    def __init__(self, instance, lock_value=None, expire_time=None):
        self.lock_id = 'scl:%s:%s' % (instance.__class__.__name__,
                                      instance.id)
        self.expire_time = expire_time or getattr(instance, 'fetch_interval',
                                                  3600)
        self.lock_value  = lock_value or 'default_lock_value'

    def __enter__(self):
        if not self.acquire():
            raise AlreadyLockedException('already locked')

    def __exit__(self, *a, **kw):
        return self.release()

    def acquire(self):
        return REDIS.set(self.lock_id, self.lock_value,
                         ex=self.expire_time, nx=True)

    def release(self):
        val = REDIS.get(self.lock_id)

        if val == self.lock_value:
            REDIS.delete(self.lock_id)
            return True

        return False


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
    GLOBAL_KEY = 'global'

    def __init__(self, *args, **kwargs):

        self.instance_id = (args[0] if isinstance(args[0], int) else args[0].id
                            ) if args else RedisStatsCounter.GLOBAL_KEY

        try:
            self.key_base = '{0}:{1}'.format(self.__class__.key_base,
                                             self.instance_id)
        except AttributeError:
            raise RuntimeError(u'RedisStatsCounter is kind of an abstract '
                               u'class, you should not use it directly but '
                               u'rather create your own stats class.')

    @classmethod
    def _time_key(cls, key, set_time=False, time_value=None):

        if set_time:
            return REDIS.set(key, time.time()
                             if time_value is None else time_value)

        return ftstamp(float(REDIS.get(key) or 0.0))

    @classmethod
    def _int_incr_key(cls, key, increment=False):

        if increment == 'reset':
            # return, else we increment to 1…
            return REDIS.delete(key)

        if increment:
            return int(REDIS.incr(key))

        return int(REDIS.get(key) or 0)

    @classmethod
    def _int_set_key(cls, key, set_value=None):

        if set_value is None:
            return int(REDIS.get(key) or 0)

        return REDIS.set(key, set_value)

    def running(self, set_running=None):

        key = self.key_base + ':run'

        # Just to be sure we need to cast…
        # LOGGER.warning('running: set=%s, value=%s type=%s',
        #                set_running, REDIS.get(self.key_base),
        #                type(REDIS.get(self.key_base)))

        if set_running is None:
            return boolcast[REDIS.get(key)]

        return REDIS.set(key, set_running)

# By default take the normal REDIS connection, but still allow
# to override it in tests via the class attribute.
RedisStatsCounter.REDIS = REDIS
