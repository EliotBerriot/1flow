# -*- coding: utf-8 -*-

import uuid

from jsonfield import JSONField

from django.conf import settings
from django.core.urlresolvers import reverse
from django.db import models
from django.db.models.signals import post_save
from django.contrib.auth import get_user_model
from django.utils.translation import ugettext_lazy as _


class UserProfile(models.Model):

    user = models.OneToOneField(settings.AUTH_USER_MODEL,
                                related_name='profile',
                                on_delete=models.CASCADE,
                                primary_key=True)

    email_announcements = models.BooleanField(_('Email announcements'),
                                              default=True, blank=True)
    register_request_data = JSONField(_('Register data'),
                                      default=lambda: {}, blank=True)
    last_modified = models.DateTimeField(_('Last modified'), auto_now_add=True)
    hash_code = models.CharField(_(u'Current validation code'), max_length=32,
                                 default=lambda: uuid.uuid4().hex)

    data = JSONField(_('profile data, as JSON'),
                     default=lambda: {}, blank=True)

    class Meta:
        verbose_name = _(u'User profile')
        verbose_name_plural = _(u'User profiles')

    def __unicode__(self):
        return u'Profile for User %s' % self.user.username

    def renew_hash_code(self, commit=True):
        self.hash_code = uuid.uuid4().hex
        if commit:
            self.save(update_fields=('hash_code',))

    def unsubscribe_url(self):
        return u'http://{0}{1}'.format(settings.SITE_DOMAIN,
                                       reverse('unsubscribe',
                                       kwargs={'hash_code': self.hash_code}))


def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)


post_save.connect(create_user_profile, sender=get_user_model())
