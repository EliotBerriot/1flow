# -*- coding: utf-8 -*-

import six
import logging

from mongoengine import Document, signals
from django.conf import settings
from django.template import Context, Template
from django.utils import translation
from django.contrib.auth import get_user_model
from djangojs.utils import ContextSerializer

from sparks.django import mail

from models import EmailContent

LOGGER = logging.getLogger(__name__)
User = get_user_model()


def connect_mongoengine_signals(module_scope):
    """ Automatically iterate classes of a given module and connect handlers
        to signals, given they follow the name pattern
        ``signal_<signal_name>_handler()``.

        See https://mongoengine-odm.readthedocs.org/en/latest/guide/signals.html#overview # NOQA
        for a list of valid signal names.
    """

    for key in dir(module_scope):
        klass = getattr(module_scope, key)

        # TODO: use ReferenceDocument and other Mongo classes.
        try:
            look_for_handlers = issubclass(Document, klass)

        except:
            # klass is definitely not a class ;-)
            continue

        if look_for_handlers:
            for signal_name in ('pre_init', 'post_init', 'pre_save',
                                'pre_save_post_validation', 'post_save',
                                'pre_delete', 'post_delete',
                                'pre_bulk_insert', 'post_bulk_insert'):
                handler_name = 'signal_{0}_handler'.format(signal_name)
                if hasattr(klass, handler_name):
                    getattr(signals, signal_name).connect(
                        getattr(klass, handler_name), sender=klass)


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

    # If there is no new user, it's not a registration, we
    # just get the context user, to fill email fields.
    # BTW, we need to get back the real user object,
    # because the celery task only gave us the ID.
    if 'new_user_id' in context:
        user = User.objects.get(id=context['new_user_id'])
        context['new_user'] = user
    else:
        user = User.objects.get(id=context['user_id'])

    if user.has_email_sent(email_template_name) \
            and not kwargs.get('force', False):
        LOGGER.info(u'User %s already received email “%s”, skipped.',
                    user.username, email_template_name)
        return

    context['user'] = user

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
