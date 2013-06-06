# -*- coding: utf-8 -*-

from django.contrib import admin
from django.conf import settings
from .models import LandingContent
from sparks.django.admin import languages, truncate_field


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
