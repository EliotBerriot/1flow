# -*- coding: utf-8 -*-
"""
    1flow "core" application. It's an Ember.JS based application, which
    explains why we don't have much things here. Everything takes place
    in the static/ and templates/ directories.

"""

import logging
import humanize

from django.http import HttpResponseRedirect, HttpResponseForbidden
from django.core.urlresolvers import reverse
from django.core.exceptions import ObjectDoesNotExist
from django.contrib import messages
from django.shortcuts import render
from django.template import add_to_builtins
from django.views.decorators.cache import never_cache
from django.contrib.auth import authenticate, login
from django.utils.translation import ugettext_lazy as _

from .forms import FullUserCreationForm
from .tasks import import_google_reader_trigger
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
        'gr_import': GoogleReaderImport(request.user.id),
    })


def register(request):
    """ New user creation process.

        DISABLED / NOT USED YET as of 20130625.
    """

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


def google_reader_import(request, user_id=None):

    if user_id is None:
        user_id      = request.user.id
        fallback_url = reverse('home') + '#/profile'

    else:
        if request.user.is_superuser or request.user.is_staff:
            fallback_url = reverse('admin:index')

        else:
            return HttpResponseForbidden("Access Denied")

    redirect_url = request.META.get('HTTP_REFERER', fallback_url)

    def info(text):
        messages.add_message(request, messages.INFO, text)

    gri = GoogleReaderImport(user_id)

    if gri.running():
        info(_(u'An import is already running for your Google Reader data.'))
        return HttpResponseRedirect(redirect_url)

    if not gri.is_active:
        info(_(u'Google Reader import deactivated.'))
        return HttpResponseRedirect(redirect_url)

    if not gri.can_import:
        info(_(u'Your beta invite has not yet been accepted, sorry.'))
        return HttpResponseRedirect(redirect_url)

    try:
        import_google_reader_trigger(user_id)

    except ObjectDoesNotExist:
        info(_(u'You are not logged into Google Oauth or you have no token.'))
        return HttpResponseRedirect(redirect_url)

    except:
        info(_(u'Error parsing Google Oauth tokens. '
             u'Please try signout and re-signin.'))
        return HttpResponseRedirect(redirect_url)

    return HttpResponseRedirect(redirect_url)


def google_reader_can_import_toggle(request, user_id):

    gri = GoogleReaderImport(user_id)

    gri.can_import = not gri.can_import

    return HttpResponseRedirect(request.META.get('HTTP_REFERER',
                                reverse('admin:index')))


def google_reader_import_stop(request, user_id):

    def info(text):
        messages.add_message(request, messages.INFO, text)

    gri          = GoogleReaderImport(user_id)
    redirect_url = request.META.get('HTTP_REFERER',
                                    reverse('admin:index'))

    if gri.running():
        gri.end(True)
        return HttpResponseRedirect(redirect_url)

    if not gri.is_active:
        info('Google Reader import deactivated.')
        return HttpResponseRedirect(redirect_url)

    if not gri.can_import:
        info('BETA invite not yet accepted.')
        return HttpResponseRedirect(redirect_url)

    return HttpResponseRedirect(redirect_url)


@never_cache
def google_reader_import_status(request):
    """ An HTML snippet view. """

    #
    # NOTE: don't test gri.is_active / gri.can_import here,
    #       it is done in the template to inform the user.
    #

    gri     = GoogleReaderImport(request.user.id)
    running = gri.running()

    if running is None:
        data = {'status': 'not_started'}

    else:
        start         = gri.start()
        articles      = gri.articles()
        reads         = gri.reads()
        total_reads   = gri.total_reads()
        starred       = gri.starred()
        total_starred = gri.total_starred()

        with humanize.i18n.django_language():

            feeds = gri.feeds()

            data = {
                # -1 to avoid counting the 'starred' virtual import feed.
                'feeds': (feeds - 1) if feeds else feeds,
                'total_feeds': gri.total_feeds(),
                'reads': reads,
                'starred': starred,
                'articles': articles,
                'total_reads': total_reads,
                'total_starred': total_starred,
                'start': humanize.time.naturaltime(start),
            }

            if running:
                data.update({
                    'status' : 'running',
                })

            else:
                end = gri.end()

                data.update({
                    'status': 'done',
                    'end': humanize.time.naturaltime(end),
                    'duration': humanize.time.naturaldelta(end - start),
                })

            speeds = gri.speeds()

            data['speed'] = int(speeds.get('global') * 60)

            eta = gri.eta()

            if eta:
                data['ETA'] = humanize.time.naturaltime(eta)

    data['gr_import'] = gri

    return render(request, 'snippets/google-reader-import-status.html', data)
