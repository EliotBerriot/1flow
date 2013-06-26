# -*- coding: utf-8 -*-

import uuid
import base64

from jsonfield import JSONField

from django.conf import settings
from django.core.urlresolvers import reverse
from django.db import models
#from django.db.models.signals import post_save
#from django.contrib.auth import get_user_model
from django.utils.translation import ugettext_lazy as _

from sparks.django.mail import send_mail


class AbstractUserProfile(models.Model):
    """ A mixin for any User class (even not real Django `User`)
        which adds primitives to get/set if a given email was sent
        to the user, and various other methods based on profile data.

        It's understood that the given user model which will use
        this mixin should either have a `.data` attribute of type
        ``JSONField``, or a `.profile.data` (JSONField too) attribute.

        Using this class allow many User classes to work in a similar
        way, be they having an dedicated profile, or not.
    """
    email_announcements = models.BooleanField(_('Email announcements'),
                                              default=True, blank=True)
    last_modified = models.DateTimeField(_('Last modified'), auto_now_add=True)

    register_data = JSONField(_('Register data, as JSON'),
                              default=lambda: {}, blank=True)
    hash_codes    = JSONField(_(u'Validation codes, as JSON'),
                              default=lambda: {'unsubscribe': uuid.uuid4().hex},
                              blank=True)
    sent_emails   = JSONField(_('sent emails names, as JSON'),
                              default=lambda: {}, blank=True)
    data          = JSONField(_('Other user data, as JSON'),
                              default=lambda: {}, blank=True)

    class Meta:
        abstract = True

    def email_user(self, subject, message, from_email=None):
        """ Sends an email to this User, [TODO: if not already done ?]. """

        send_mail(subject, message, from_email, [self.email])

    def has_email_sent(self, email_name):
        return self.sent_emails.get('email_sent_' + email_name, False)

    def log_email_sent(self, email_name):
        return self.sent_emails.setdefault('email_sent_' + email_name, True)

    def renew_hash_code(self, name, commit=True):
        self.hash_codes[name] = uuid.uuid4().hex
        if commit:
            self.save(update_fields=('hash_codes', ))

    def unsubscribe_url(self):
        return u'http://{0}{1}'.format(
            settings.SITE_DOMAIN, reverse('unsubscribe', kwargs={
                'email': base64.b64encode(self.email),
                'hash_code': self.hash_codes.get('unsubscribe')
            }))
