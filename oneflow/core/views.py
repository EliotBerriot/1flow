# -*- coding: utf-8 -*-
"""
    1flow "core" application. It's an Ember.JS based application, which
    explains why we don't have much things here. Everything takes place
    in the static/ and templates/ directories.

"""

import redis
import logging
import simplejson as json

from django.http import HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.core.exceptions import ObjectDoesNotExist
from django.contrib import messages
from django.shortcuts import render
from django.template import add_to_builtins
from django.views.decorators.cache import never_cache
from django.contrib.auth import authenticate, login

from .models.nonrel import User as MongoUser, Subscription
from .forms import FullUserCreationForm
from .tasks import import_google_reader_data_trigger

LOGGER = logging.getLogger(__name__)
REDIS = redis.StrictRedis(host=getattr(settings, 'REDIS_FEEDBACK_HOST',
                          'localhost'), port=6379,
                          db=getattr(settings, 'REDIS_DB', 0))


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


def import_google_reader(request):

    def info(text):
        messages.add_message(request, messages.INFO, text)

    redirect_url = reverse('home') + '#/profile'

    # TODO: if already_imported: return + message

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


def import_google_reader_stats(request):
    """ A JSON View. """

    user = MongoUser.objects.get(django_user=request.user.id)

    if user.gr_import:
        if user.gr_import.is_running:
            data = {
                'feeds': user.gr_import.feeds_imported,
                'total': Subscription.objects(user=user),
                'reads': user.gr_import.articles_imported,
                'start': user.gr_import.start_time.isoformat(),
                'done' : False,
            }
        else:
            data = {
                'done': True,
                'start': user.gr_import.start_time.isoformat(),
                'end': user.gr_import.end_time.isoformat(),
            }
    else:
        data = {'done': None}

    return HttpResponse(json.dumps(data),
                        content_type="application/json")
