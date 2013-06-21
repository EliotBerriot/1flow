# -*- coding: utf-8 -*-
"""
    1flow "core" application. It's an Ember.JS based application, which
    explains why we don't have much things here. Everything takes place
    in the static/ and templates/ directories.

"""

import logging
import datetime

from humanize import time as humanize_time

from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.core.exceptions import ObjectDoesNotExist
from django.contrib import messages
from django.shortcuts import render
from django.template import add_to_builtins
from django.views.decorators.cache import never_cache
from django.contrib.auth import authenticate, login

from .forms import FullUserCreationForm
from .tasks import import_google_reader_data_trigger
from .gr_import import GoogleReaderImport

LOGGER = logging.getLogger(__name__)

# Avoid the very repetitive:
#       {% load ember js compressed i18n base_utils %}
# in the Ember application templates.
add_to_builtins('ember.templatetags.ember')
add_to_builtins('django.templatetags.i18n')
add_to_builtins('djangojs.templatetags.js')
add_to_builtins('pipeline.templatetags.compressed')
add_to_builtins('absolute.templatetags.absolute_future')
add_to_builtins('oneflow.base.templatetags.base_utils')


@never_cache
def home(request):
    """ will return the base of the Ember.JS application. """

    has_google = request.user.social_auth.filter(
        provider='google-oauth2').count() > 0

    return render(request, 'home.html', {
        'has_google': has_google,
        'gr_import': GoogleReaderImport(request.user),
    })


def register(request):

    creation_form = FullUserCreationForm(data=request.POST or None)

    if request.method == 'POST':

        if creation_form.is_valid():

            user = creation_form.save()

            authenticated_user = authenticate(
                username=user.username,
                password=creation_form.cleaned_data['password1']
            )

            login(request, authenticated_user)

            #post_register_actions.delay((user.id, ))

            return HttpResponseRedirect(reverse('home'))

    return render(request, 'register.html', {'form': creation_form})


def google_reader_import(request):

    def info(text):
        messages.add_message(request, messages.INFO, text)

    redirect_url = reverse('home') + '#/profile'

    gri = GoogleReaderImport(request.user)

    if gri.running():
        info('An import is already running for your Google Reader data.')
        return HttpResponseRedirect(redirect_url)

    try:
        import_google_reader_data_trigger(request.user.id)

    except ObjectDoesNotExist:
        info('You are not logged into Google Oauth or you have no token.')
        return HttpResponseRedirect(reverse('home') + '#/profile')

    except:
        info('Error parsing Google Oauth tokens. '
             'Please try signout and re-signin.')
        return HttpResponseRedirect(reverse('home') + '#/profile')

    return HttpResponseRedirect(redirect_url)


@never_cache
def google_reader_import_status(request):
    """ An HTML snippet view. """

    gri = GoogleReaderImport(request.user)

    running = gri.running()

    if running is None:
        data = {'status': 'not_started'}

    else:
        now         = datetime.datetime.now()
        start       = gri.start()
        articles    = gri.articles()
        reads       = gri.reads()
        total_reads = gri.total_reads()

        data = {
            'feeds': gri.feeds(),
            'total_feeds': gri.total_feeds(),
            'reads': reads,
            'starred': gri.starred(),
            'articles': articles,
            'total_reads': total_reads,
            'start': humanize_time.naturaltime(start),
        }

        if running:
            data.update({
                'status' : 'running',
            })

        else:
            end = gri.end()

            data.update({
                'status': 'done',
                'end': humanize_time.naturaltime(end),
                'duration': humanize_time.naturaldelta(end - start),
            })

        def duration_since(start):
            delta = (now if running else end) - start
            return delta.seconds + delta.microseconds / 1E6 + delta.days * 86400

        speed = articles / duration_since(start)

        data['speed'] = int(speed * 60)

        if running:
            data['ETA'] = humanize_time.naturaltime(now + datetime.timedelta(
                                                    seconds=(total_reads
                                                    - reads) * speed))

    return render(request, 'snippets/google-reader-import-status.html', data)
