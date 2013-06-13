# -*- coding: utf-8 -*-

from django.contrib import admin

from ..base.admin import NearlyReadOnlyAdmin, CSVAdminMixin
from .models import UserProfile


class UserProfileAdmin(CSVAdminMixin, NearlyReadOnlyAdmin):
    readonly_fields = ('user', )
    ordering = ('-last_modified', )
    date_hierarchy = 'last_modified'
    list_filter = ('last_modified', )

admin.site.register(UserProfile, UserProfileAdmin)
