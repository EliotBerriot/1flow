# -*- coding: utf-8 -*-

import logging

from django.contrib.auth import get_user_model
from django.template import Template
from django.utils import translation

from sparks.django import mail

from ...landing.models import LandingUser

from ..models import EmailContent


LOGGER = logging.getLogger(__name__)
User = get_user_model()


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
