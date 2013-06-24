# -*- coding: utf-8 -*-


import datetime

from django.utils.translation import ugettext_lazy as _
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.core.urlresolvers import reverse

from humanize.time import naturaldelta

from .gr_import import GoogleReaderImport
#from .models import User

User = get_user_model()
now = datetime.datetime.now


class GriUser(User):
    class Meta:
        proxy = True
        verbose_name = _(u'Google Reader import')
        verbose_name_plural = _(u'Google Reader imports')


class GriOneFlowUserAdmin(UserAdmin):

    list_display = ('username', 'gri_subscriptions_display',
                    'gri_articles_display', 'gri_duration_display',
                    'gri_button_display', )

    def has_add_permission(self, request):
        return False

    def gri_articles_display(self, obj):
        gri = GoogleReaderImport(obj)
        return gri.articles() or u'—'

    gri_articles_display.short_description = _(u'article imported')

    def gri_subscriptions_display(self, obj):
        gri = GoogleReaderImport(obj)
        return gri.feeds() or u'—'

    gri_subscriptions_display.short_description = _(u'feeds imported')

    def gri_duration_display(self, obj):

        gri = GoogleReaderImport(obj)

        if gri.running():
            return naturaldelta(now() - gri.start())

        elif gri.running() is False:
            return naturaldelta(gri.end() - gri.start())

        else:
            return u'—'

    gri_duration_display.short_description = _(u'import duration')

    def gri_button_display(self, obj):
        gri = GoogleReaderImport(obj)

        if gri.running():
            return u'<a href="{0}">{1}</a>'.format(
                reverse('google_reader_import_stop',
                        kwargs={'user_id': obj.id}), _(u'stop'))

        else:
            return u'<a href="{0}">{1}</a>'.format(
                reverse('google_reader_import', kwargs={'user_id': obj.id}),
                _(u'start') if gri.running() is None else _(u'restart'))

    gri_button_display.short_description = _(u'action')
    gri_button_display.allow_tags = True

admin.site.register(GriUser, GriOneFlowUserAdmin)
