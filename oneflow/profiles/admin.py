# -*- coding: utf-8 -*-

from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from ..base.admin import NearlyReadOnlyAdmin, CSVAdminMixin
from .models import UserProfile


class UserProfileAdmin(CSVAdminMixin):
    ordering = ('-last_modified', )
    date_hierarchy = 'last_modified'
    list_filter = ('last_modified', )

admin.site.register(UserProfile, UserProfileAdmin)
