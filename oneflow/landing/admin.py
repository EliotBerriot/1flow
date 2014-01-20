# -*- coding: utf-8 -*-
"""
    Copyright 2013-2014 Olivier Cortès <oc@1flow.io>

    This file is part of the 1flow project.

    1flow is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of
    the License, or (at your option) any later version.

    1flow is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public
    License along with 1flow.  If not, see http://www.gnu.org/licenses/

"""

from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from django.contrib import admin as django_admin
import mongoadmin as admin

from sparks.django.admin import languages, truncate_field

from .models import LandingContent, LandingUser
from ..base.admin import CSVAdminMixin


class LandingUserAdmin(CSVAdminMixin):
    list_display = ('id', 'email', 'register_language_display', 'date_joined', )
    list_display_links = ('id', 'email', )
    list_filter = ('email_announcements', )
    ordering = ('-date_joined', )
    date_hierarchy = 'date_joined'
    search_fields = ('email', )
    change_list_template = "admin/change_list_filter_sidebar.html"
    change_list_filter_template = "admin/filter_listing.html"

    def register_language_display(self, obj):
        return obj.register_data.get('language', u'—').split(',', 1)[0]

    register_language_display.short_description = _(u'language')

admin.site.register(LandingUser, LandingUserAdmin)


if settings.FULL_ADMIN:
    content_fields_names = tuple(('content_' + code)
                                 for code, lang in languages)
    content_fields_displays = tuple((field + '_display')
                                    for field in content_fields_names)

    class LandingContentAdmin(django_admin.ModelAdmin):
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
