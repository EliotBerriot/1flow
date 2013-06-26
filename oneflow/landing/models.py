# -*- coding: utf-8 -*-

from transmeta import TransMeta

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone

from ..profiles.models import AbstractUserProfile


class LandingContent(models.Model):
    __metaclass__ = TransMeta

    name    = models.CharField(_('Template variable name'),
                               max_length=128, unique=True)
    content = models.TextField(_('Template variable content'))

    def __unicode__(self):
        return _(u'{field_name}: {truncated_field_value}').format(
            field_name=self.name, truncated_field_value=self.content[:30]
            + (self.content[30:] and u'…'))

    class Meta:
        translate = ('content', )
        verbose_name = _(u'Landing page content')
        verbose_name_plural = _(u'Landing page contents')


class LandingUser(AbstractUserProfile):
    """ A small user model, similar to a Django user to have the same
        attributes and primitives, but not a real user account.

        Used to hold the emails collected on the landing page, and a
        little profile data.
    """

    email = models.EmailField(_('email address'),  max_length=254,
                              help_text=_('Any valid email address.'))
    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)

    class Meta:
        verbose_name        = _(u'Landing user')
        verbose_name_plural = _(u'Landing users')

    @property
    def is_active(self):
        return False

    @property
    def is_staff(self):
        return False

    @property
    def is_superuser(self):
        return False

    @property
    def username(self):
        return self.email

    def get_full_name(self):
        return self.email

    def get_short_name(self):
        return self.email
