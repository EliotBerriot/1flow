# -*- coding: utf-8 -*-

import logging

from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.contrib.auth import get_user_model
from django.shortcuts import render
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.cache import never_cache

from .forms import LandingPageForm
from .tasks import background_post_register_actions
from .funcs import get_all_beta_data

from ..base.utils import request_context_celery

LOGGER = logging.getLogger(__name__)
User = get_user_model()


def home(request):
    if request.POST:
        form = LandingPageForm(request.POST)

        if form.is_valid():
            email = form.cleaned_data['email']

            user = User.objects.create(username=email, email=email)

            # We need to forge a context for celery,
            # passing the request "as is" never works.
            context = request_context_celery(request, {'new_user_id': user.id})

            # we need to delay to be sure the profile creation is done.
            background_post_register_actions.delay(context)

            return HttpResponseRedirect(reverse('landing_thanks'))

        else:
            try:
                email = form.data['email']
            except:
                pass

            else:
                # Avoid displaying the disgracious error:
                # "User with this Email address already exists."
                # It will show up later in the application, but
                # on the landing page this is not cool.
                try:
                    User.objects.get(email=email)

                except User.DoesNotExist:
                    pass

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
