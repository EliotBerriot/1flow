# -*- coding: utf-8 -*-
"""
    1flow "core" application. It's an Ember.JS based application, which
    explains why we don't have much things here. Everything takes place
    in the static/ and templates/ directories.

"""

import logging

from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.shortcuts import render
from django.template import add_to_builtins
from django.views.decorators.cache import never_cache
from django.contrib.auth import authenticate, login

from ..profiles.forms import UserProfileForm
from .forms import FullUserCreationForm

LOGGER = logging.getLogger(__name__)


# Avoid the very repetitive:
#       {% load ember js compressed i18n base_utils %}
# in the Ember application templates.
add_to_builtins('ember.templatetags.ember')
add_to_builtins('django.templatetags.i18n')
add_to_builtins('djangojs.templatetags.js')
add_to_builtins('pipeline.templatetags.compressed')
add_to_builtins('oneflow.base.templatetags.base_utils')


@never_cache
def home(request):
    """ will return the base of the Ember.JS application. """

    return render(request, 'home.html')


@never_cache
def profile(request):

    if request.POST:
        form = UserProfileForm(request.POST)

        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('profile'))

    else:
        form = UserProfileForm(request.user.profile)

    context = {'form': form}

    return render(request, 'profile.html', context)


def register(request):

    creation_form = FullUserCreationForm(data=request.POST or None)

    if request.method == 'POST' and creation_form.is_valid():

        user = creation_form.save()

        authenticated_user = authenticate(
            username=user.username,
            password=creation_form.cleaned_data['password1']
        )

        login(request, authenticated_user)

        return HttpResponseRedirect(reverse('home'))

    return render(request, 'register.html', {'form': creation_form})
