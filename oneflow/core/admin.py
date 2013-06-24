# -*- coding: utf-8 -*-


import datetime

from django.utils.translation import ugettext_lazy as _
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.core.urlresolvers import reverse

from humanize.time import naturaldelta

from .gr_import import GoogleReaderImport

# NOTE: using "from base.models import User" will generate
# a "cannot proxy swapped model base.User" when creating the
# GriUser class. Using `get_user_model()` works.
User = get_user_model()
now = datetime.datetime.now


class GriUser(User):
    """ Just a proxy to User model, to be able to build a list against it. """

    class Meta:
        proxy = True
        verbose_name = _(u'Google Reader import')
        verbose_name_plural = _(u'Google Reader imports')


class GriOneFlowUserAdmin(UserAdmin):
    """ Wrap our GoogleReaderImport class onto User accounts,
        to be able to act on imports from the Django administration. """

    list_display = ('username', 'gri_subscriptions_display',
                    'gri_articles_display', 'gri_reads_display',
                    'gri_starred_display', 'gri_duration_display',
                    'gri_button_display', 'can_import_display', )

    def has_add_permission(self, request):
        # Don't display the ADD button in the Django interface.
        return False

    def gri_articles_display(self, obj):

        return GoogleReaderImport(obj.id).articles() or u'—'

    gri_articles_display.short_description = _(u'articles')

    def gri_subscriptions_display(self, obj):

        return GoogleReaderImport(obj.id).feeds() or u'—'

    gri_subscriptions_display.short_description = _(u'feeds')

    def gri_reads_display(self, obj):

        return GoogleReaderImport(obj.id).reads() or u'—'

    gri_reads_display.short_description = _(u'reads')

    def gri_starred_display(self, obj):

        return GoogleReaderImport(obj.id).starred() or u'—'

    gri_starred_display.short_description = _(u'starred')

    def gri_duration_display(self, obj):

        gri = GoogleReaderImport(obj.id)

        if gri.running():
            return naturaldelta(now() - gri.start())

        elif gri.running() is False:
            return naturaldelta(gri.end() - gri.start())

        else:
            return u'—'

    gri_duration_display.short_description = _(u'import duration')

    def gri_button_display(self, obj):

        gri = GoogleReaderImport(obj.id)

        has_google = obj.social_auth.filter(provider=
                                            'google-oauth2').count() > 0
        if has_google:
            if gri.running():
                return u'<a href="{0}">{1}</a>'.format(
                    reverse('google_reader_import_stop',
                            kwargs={'user_id': obj.id}), _(u'stop'))

            else:
                return u'<a href="{0}">{1}</a>'.format(
                    reverse('google_reader_import',
                            kwargs={'user_id': obj.id}),
                            _(u'start') if gri.running() is None
                            else _(u'restart'))
        else:
            return u'—'

    gri_button_display.short_description = _(u'import')
    gri_button_display.allow_tags = True

    def can_import_display(self, obj):

        gri = GoogleReaderImport(obj.id)

        return u'<a href="{0}">{1}</a>'.format(
                    reverse('google_reader_can_import_toggle',
                            kwargs={'user_id': obj.id}), _(u'deny')
                            if gri.can_import else _(u'allow'))

    can_import_display.short_description = _(u'Permission')
    can_import_display.allow_tags = True

admin.site.register(GriUser, GriOneFlowUserAdmin)
