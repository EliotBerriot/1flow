# -*- coding: utf-8 -*-

from django.contrib import admin
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from sparks.django.admin import languages, truncate_field

from .models import LandingContent, LandingUser
from ..base.admin import CSVAdminMixin

class LandingUserAdmin(CSVAdminMixin):
    list_display = ('id', 'email', 'register_language_display', )

    def register_language_display(self, obj):
        return obj.register_data.get('language', u'—').split(',', 1)[0]

    register_language_display.short_description = _(u'language')

admin.site.register(LandingUser, LandingUserAdmin)


if settings.FULL_ADMIN:
    content_fields_names = tuple(('content_' + code)
                                 for code, lang in languages)
    content_fields_displays = tuple((field + '_display')
                                    for field in content_fields_names)

    class LandingContentAdmin(admin.ModelAdmin):
        list_display  = ('name', ) + content_fields_displays
        search_fields = ('name', ) + content_fields_names
        ordering      = ('name', )
        #change_list_template = "admin/change_list_filter_sidebar.html"
        #change_list_filter_template = "admin/filter_listing.html"

    for attr, attr_name in zip(content_fields_names,
                               content_fields_displays):
        setattr(LandingContentAdmin, attr_name,
                truncate_field(LandingContent, attr))

    admin.site.register(LandingContent, LandingContentAdmin)
