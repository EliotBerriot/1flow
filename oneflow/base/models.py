# -*- coding: utf-8 -*-
"""

    The :class:`User` and :class:`UserManager` classes can completely and
    transparently replace the one from Django.

    We don't use the `username` attribute, but it is implemented as a
    readonly property, returning the `email`, which we use as required
    user name field.
"""

from transmeta import TransMeta

from django.db import models
from django.utils.http import urlquote
from django.contrib.auth.models import (BaseUserManager,
                                        AbstractBaseUser,
                                        PermissionsMixin)
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone

from sparks.django.mail import send_mail


class EmailContent(models.Model):
    __metaclass__ = TransMeta

    name    = models.CharField(_('Email name'),
                               max_length=128, unique=True)
    subject = models.CharField(_('Email subject'), max_length=256)
    body    = models.TextField(_('Email body'))

    def __unicode__(self):
        return _(u'{field_name}: {truncated_field_value}').format(
            field_name=self.name, truncated_field_value=self.subject[:30]
            + (self.subject[30:] and u'…'))

    class Meta:
        translate = ('subject', 'body', )
        verbose_name = _(u'Email content')
        verbose_name_plural = _(u'Emails contents')


class UserManager(BaseUserManager):
    """ This is a free adaptation of
        https://github.com/django/django/blob/master/django/contrib/auth/models.py  # NOQA
        as of 20130526. """

    def create_user(self, username, email, password=None, **extra_fields):
        """ Creates and saves a User with the given username,
            email and password. """

        now = timezone.now()

        if not email:
            raise ValueError('User must have an email')

        email = UserManager.normalize_email(email)

        user = self.model(username=username, email=email,
                          is_active=True, is_staff=False, is_superuser=False,
                          last_login=now, date_joined=now, **extra_fields)

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password, **extra_fields):
        u = self.create_user(username, email, password, **extra_fields)
        u.is_staff = True
        u.is_active = True
        u.is_superuser = True
        u.save(using=self._db)
        return u


class User(AbstractBaseUser, PermissionsMixin):
    """ Username, password and email are required.
        Other fields are optional. """

    #NOTE: AbstractBaseUser brings `password` and `last_login` fields.

    username = models.CharField(_('User name'), max_length=254,
                                unique=True, db_index=True,
                                help_text=_('Required. letters, digits, '
                                            'and "@+-_".'))
    email = models.EmailField(_('email address'),  max_length=254,
                              unique=True, db_index=True,
                              help_text=_('Any valid email address.'))
    first_name = models.CharField(_('first name'), max_length=64, blank=True)
    last_name = models.CharField(_('last name'), max_length=64, blank=True)
    is_staff = models.BooleanField(_('staff status'), default=False,
                                   help_text=_('Designates whether the user '
                                               'can log into this admin '
                                               'site.'))
    is_active = models.BooleanField(_('active'), default=True,
                                    help_text=_('Designates whether this user '
                                                'should be treated as '
                                                'active. Unselect this instead '
                                                'of deleting accounts.'))
    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ('email', )

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')

    def get_absolute_url(self):
        return _("/users/{username}/").format(urlquote(self.username))

    def get_full_name(self):
        """ Returns the first_name plus the last_name, with a space in between.
        """
        full_name = '%s %s' % (self.first_name, self.last_name)
        return full_name.strip()

    def get_short_name(self):
        "Returns the short name for the user."
        return self.username

    def email_user(self, subject, message, from_email=None):
        """ Sends an email to this User. """
        send_mail(subject, message, from_email, [self.email])
