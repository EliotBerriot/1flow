# -*- coding: utf-8 -*-

import logging

from django.conf import settings
from django.template import Context, Template
from django.utils import translation

from sparks.django import mail

from models import EmailContent

LOGGER = logging.getLogger(__name__)


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
    user = context.get('new_user', context.get('user'))
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
        context.update({'unsubscribe_url': user.profile.unsubscribe_url()})

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
        #post_send=post_send(user)
        **kwargs)

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
        be removed from the context. Defaults keys purged are::

            ('wsgi.errors', 'wsgi.input', )

        You can specify non-existing keys, they will just be skipped.

    """

    # TODO: i18n
    context = Context(*args, **kwargs)

    meta = request.META.copy()
    for key in getattr(settings, 'CELERY_CONTEXT_EXPUNGE_META',
                       ('wsgi.errors', 'wsgi.input', )):
        try:
            del meta[key]

        except KeyError:
            pass

    context.update({
                   'user': request.user,
                   'meta': meta,
                   'session': request.session})

    try:
        context.update({'language_code': request.LANGUAGE_CODE})

    except:
        context.update({'language_code': None})

    return context
