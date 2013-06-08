# -*- coding: utf-8 -*-

import logging

#from django import forms
#from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model

LOGGER = logging.getLogger(__name__)
User = get_user_model()


class FullUserCreationForm(UserCreationForm):
    """ Like the django UserCreationForm,
        with optional first_name and last_name,
        and email too.

        .. note:: the ``username`` field from Django's ``UserCreationForm``
            is overriden by our Model's one. Thus the 30 chars limit
            doesn't apply.
    """

    class Meta:
        model = User
        # We want a different order of fields on the page.
        fields = ['first_name', 'last_name',
                  'username', 'email',
                  'password1', 'password2', ]

    def save(self, commit=True):
        user = super(FullUserCreationForm, self).save(commit=False)

        user.email     = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"]
        user.last_name  = self.cleaned_data["last_name"]

        if commit:
            user.save()
        return user
