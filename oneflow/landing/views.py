# -*- coding: utf-8 -*-

import logging

from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.cache import never_cache

from .forms import LandingPageForm
from .tasks import background_post_register_actions
from .funcs import get_all_beta_data
from .models import LandingUser

from ..base.utils import request_context_celery

LOGGER = logging.getLogger(__name__)


def home(request):

    if request.user.is_authenticated():
        if not (request.user.is_staff or request.user.is_superuser):
            return HttpResponseRedirect(reverse('home'))

    if request.POST:
        form = LandingPageForm(request.POST)

        if form.is_valid():
            email = form.cleaned_data['email']

            user, created = LandingUser.objects.get_or_create(email=email)

            if created:
                # We need to forge a context for celery,
                # passing the request "as is" never works.
                context = request_context_celery(request, {'new_user_id': user.id})

                # we need to delay to be sure the profile creation is done.
                background_post_register_actions.delay(context)

                return HttpResponseRedirect(reverse('landing_thanks'))

            else:
                return HttpResponseRedirect(reverse('landing_thanks',
                                            kwargs={'already_registered':
                                            _('again')}))

    else:
        form = LandingPageForm()

        # make market-man smile :-)
        request.session.setdefault('INITIAL_REFERER',
                                   request.META.get('HTTP_REFERER', ''))

    context = {'form': form}
    context.update(get_all_beta_data())

    return render(request, 'landing_index.html', context)


# never cache allows to update the counter for the newly registered user.
@never_cache
def thanks(request, **kwargs):

    context = dict(already_registered=bool(
        kwargs.pop('already_registered', False)))

    context.update(get_all_beta_data())

    return render(request, 'landing_thanks.html', context)
