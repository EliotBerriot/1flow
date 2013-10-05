# -*- coding: utf-8 -*-
"""
    1flow "core" application. It's an Ember.JS based application, which
    explains why we don't have much things here. Everything takes place
    in the static/ and templates/ directories.

"""

import logging
import humanize

from constance import config

from django.http import (HttpResponseRedirect,
                         HttpResponseForbidden,
                         HttpResponseBadRequest,
                         HttpResponse)
from django.core.urlresolvers import reverse
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from django.contrib import messages
from django.shortcuts import render
from django.template import add_to_builtins
#from django.views.generic import ListView
from django.contrib.auth import authenticate, login, get_user_model
from django.utils.translation import ugettext_lazy as _

#from infinite_pagination.paginator import InfinitePaginator
from endless_pagination.utils import get_page_number_from_request

from sparks.django.utils import HttpResponseTemporaryServerError

from .forms import (FullUserCreationForm,
                    UserProfileEditForm,
                    HomePreferencesForm,
                    ReadPreferencesForm,
                    SelectorPreferencesForm)
from .tasks import import_google_reader_trigger
from .models.nonrel import Feed, Subscription, Read
from .models.reldb import HelpContent
from ..base.utils.dateutils import now

from .gr_import import GoogleReaderImport

LOGGER = logging.getLogger(__name__)
User = get_user_model()

# Avoid repetitive {% load … %} in templates.
add_to_builtins('django.templatetags.i18n')
add_to_builtins('djangojs.templatetags.js')
add_to_builtins('pipeline.templatetags.compressed')
add_to_builtins('absolute.templatetags.absolute_future')
add_to_builtins('markdown_deux.templatetags.markdown_deux_tags')
add_to_builtins('widget_tweaks.templatetags.widget_tweaks')
add_to_builtins('oneflow.base.templatetags.base_utils')
add_to_builtins('oneflow.core.templatetags.coretags')

if settings.TEMPLATE_DEBUG:
    add_to_builtins('template_debug.templatetags.debug_tags')

# ———————————————————————————————————————————————————————————————————— Wrappers
# I couldn't find any way to create an URL patterns with a (?P<…>) that
# would be merged with a default `kwargs={…}` in the same URL pattern.
#
# Thus, these small view wrappers that just do the merge.
#


def read_all_feed_with_endless_pagination(request, **kwargs):

    kwargs[u'all'] = True
    return read_with_endless_pagination(request, **kwargs)


def read_feed_with_endless_pagination(request, **kwargs):

    kwargs.update({'is_read': False})  # , 'is_bookmarked': False})
    return read_with_endless_pagination(request, **kwargs)


def make_read_wrapper(attrkey, view_name):
    """ See http://stackoverflow.com/a/3431699/654755 for why."""

    def func(request, **kwargs):
        kwargs[attrkey] = True
        return read_with_endless_pagination(request, **kwargs)

    globals()['read_{0}_feed_with_endless_pagination'.format(view_name)] = func


# This builds "read_later_feed_with_endless_pagination" and so on.
for attrkey, attrval in Read.status_data.items():
    if 'list_url_feed' in attrval:
        make_read_wrapper(attrkey, attrval.get('view_name'))


# —————————————————————————————————————————————————————————————————— Real views


def home(request):
    """ root of the application. """

    home_style = request.user.mongo.preferences.home.style

    if home_style and home_style == 'T1':
        return HttpResponseRedirect(reverse(u'read'))

    return render(request, 'home.html', {
        'gr_import': GoogleReaderImport(request.user.id),
    })


def preferences(request):

    if request.POST:
        home_form = HomePreferencesForm(
                request.POST, instance=request.user.mongo.preferences.home)

        reading_form = ReadPreferencesForm(
                request.POST, instance=request.user.mongo.preferences.read)

        sources_form = SelectorPreferencesForm(
                request.POST, instance=request.user.mongo.preferences.selector)

        if reading_form.is_valid() and sources_form.is_valid:
            # form.save() does nothing on an embedded document,
            # which needs to be saved from the container.
            request.user.mongo.preferences.home = home_form.save()
            request.user.mongo.preferences.read = reading_form.save()
            request.user.mongo.preferences.selector = sources_form.save()
            request.user.mongo.preferences.save()

            return HttpResponseRedirect(reverse('preferences'))
    else:
        home_form = HomePreferencesForm(
                instance=request.user.mongo.preferences.home)
        reading_form = ReadPreferencesForm(
                instance=request.user.mongo.preferences.read)
        sources_form = SelectorPreferencesForm(
                instance=request.user.mongo.preferences.selector)

    return render(request, 'preferences.html', {
                  'home_form': home_form,
                  'reading_form': reading_form,
                  'sources_form': sources_form
                  })


def source_selector(request, **kwargs):

    if request.is_ajax():
        template = u'snippets/selector/selector.html'

    else:
        template = u'selector.html'

    mongodb_user   = request.user.mongo
    selector_prefs = mongodb_user.preferences.selector

    return render(request, template, {
        'subscriptions':             mongodb_user.subscriptions,
        'closed_subscriptions':      mongodb_user.nofolder_closed_subscriptions,
        'show_closed_streams':       selector_prefs.show_closed_streams,
        'titles_show_unread_count':  selector_prefs.titles_show_unread_count,
        'folders_show_unread_count': selector_prefs.folders_show_unread_count,
        })


def read_with_endless_pagination(request, **kwargs):

    query_kwargs = {}
    combinations = ()
    attributes   = Read.status_data.keys()

    def check_order_by(value):
        if value in (u'id', ):
            return

        raise RuntimeError()

    # First, get the view mode we were called from.
    if kwargs.get('all', False):
        # No particular kwargs for this one, but we
        # needed to pass in the 'if' to avoid the
        # default case where we get only the unread.
        pass

    else:
        combinations = set()

        for attrname in attributes:
            mykwarg = kwargs.get(attrname, None)

            if mykwarg is not None:
                if mykwarg:
                    query_kwargs[attrname] = mykwarg

                else:
                    # For 2 reasons we need to negate:
                    # - old reads don't have default attribute because some
                    #   didn't exist at the time, thus the value is None in
                    #   the database.
                    # - all Reads (old and new) can have `.is_starred` == None
                    #   because False and True mean "I don't like" and "I like",
                    #   None meaning "like status not set".
                    query_kwargs[attrname + u'__ne'] = True

                if request.user.is_superuser or request.user.is_staff:
                    combinations.union(set(
                        attr2, request.GET.get(attr2, None), bool)
                            for attr2 in attributes if attr2 not in attributes
                    )

    # Then allow the user to mix with manual query
    # parameters, but check them to avoid crashes.
    for parameter, value, checker in combinations:
        if value is None:
            continue

        try:
            checked_value = checker(value)

        except:
            LOGGER.exception(u'Check %s on value "%s" of parameter %s '
                             u'failed; skipped.', checker, value, parameter)
            continue

        if checker == bool and not checked_value:
            # See before, in the for loop.
            query_kwargs[parameter + u'__ne'] = True

        else:
            query_kwargs[parameter] = checked_value

    if request.user.is_superuser or request.user.is_staff:
        order_by = unicode(request.GET.get('order_by', u'-id'))
    else:
        order_by = u'-id'

    try:
        if order_by.startswith(u'-'):
            check_order_by(order_by[1:])
        else:
            check_order_by(order_by)
    except:
        LOGGER.exception(u'order_by check failed (value "%s"); using "-id".',
                         order_by)
        order_by = u'-id'

    # ——————————————————————————————————————————————————————— start filter more

    feed = kwargs.get('feed', None)

    if feed:
        #LOGGER.info(u'Refining reads by %s', feed)
        query_kwargs[u'subscriptions__contains'] = \
            Subscription.objects.get(id=feed)

    # ————————————————————————————————————————————————————————— end filter more

    #LOGGER.info(u'query_kwargs: %s', query_kwargs)

    reads = Read.objects(user=request.user.mongo,
                         **query_kwargs).order_by(order_by).no_cache()

    #LOGGER.info(u'%s\n%s > %s, %s, %s', reads[0], reads[0].article,
    #            reads[0].article.url_absolute,
    #            reads[0].article.duplicate_of,
    #            reads[0].article.orphaned)

    context = {
        u'reads': reads,

        # are we rendering the first "main"
        # page, or just a subset via ajax?
        u'initial': False,
    }

    #preferences = request.user.mongo.preferences

    if request.is_ajax():

        if request.GET.get('count', False):
            template = u'snippets/read/read-endless-count.html'
            context[u'reads_count'] = reads.count()

        elif request.GET.get('mark_all_read', False):

            if feed:
                query_kwargs[u'subscriptions__contains'].mark_all_read()

            else:
                for sub in request.user.mongo.subscriptions:
                    sub.mark_all_read()

            return HttpResponse('DONE')

        else:
            template = u'snippets/read/read-endless-page.html'

            # Computing tenths_counter here is much efficient than doing:
            # {% captureas tenths_counter %}{{ request.GET['page']|mul:10 }}{% endcaptureas %} # NOQA
            # in the template…
            context[u'tenths_counter'] = \
                (get_page_number_from_request(request) - 1) \
                * config.READ_INFINITE_ITEMS_PER_FETCH

        #LOGGER.info(u'Ajax with %s', context.get('tenths_counter'))

    else:
        template = u'read-endless.html'
        context[u'initial'] = True

    return render(request, template, context)


def read_one(request, read_id):

    try:
        read = Read.get_or_404(read_id)

    except:
        return HttpResponseTemporaryServerError()

    if request.is_ajax():
        template = u'snippets/read/read-one.html'

    else:
        template = u'read-one.html'

    return render(request, template, {'read': read})


def set_preference(request, base, sub, value):

    prefs = request.user.mongo.preferences

    try:
        base_pref = getattr(prefs, base)
        setattr(base_pref, sub, value)

    except:
        return HttpResponseBadRequest(u'Bad preference name or value.')

    else:

        try:
            prefs.save()

        except:
            LOGGER.exception(u'Could not save preferences for user %s',
                             request.user.mongo)
            return HttpResponseTemporaryServerError(
                u'Could not save preference.')

    if request.is_ajax():
        return HttpResponse(u'DONE')

    return HttpResponseRedirect(request.META.get('HTTP_REFERER',
                                reverse('home')))


def toggle(request, klass, oid, key):

    try:
        obj = globals()[klass].get_or_404(oid)

    except:
        return HttpResponseTemporaryServerError()

    try:
        new_value = not getattr(obj, key)
        setattr(obj, key, new_value)

    except:
        msg = (u'Unable to toggle %s of %s', key, obj)
        LOGGER.exception(*msg)
        return HttpResponseTemporaryServerError(msg[0] % msg[1:])

    else:
        if key.startswith('is_'):
            date_attr = 'date_' + key[3:]

            if hasattr(obj, date_attr):
                setattr(obj, date_attr, now())

        try:
            getattr(obj, key + '_changed')()

        except AttributeError:
            pass

        except:
            LOGGER.exception(u'Unhandled exception while running '
                             u', %s.%s_changed() on %s.',
                             obj.__class__.__name__, key, obj)

        obj.save()

    if request.is_ajax():
        return HttpResponse(u'DONE.')

    else:
        return HttpResponseRedirect(request.META.get('HTTP_REFERER',
                                    reverse('home')))


def profile(request):

    if request.POST:
        form = UserProfileEditForm(request.POST, instance=request.user)

        if form.is_valid():
            form.save()
    else:
        form = UserProfileEditForm(instance=request.user)

    return render(request, 'profile.html', {'form': form})


def help(request):

    help_sections = HelpContent.objects.filter(active=True)

    return render(request, u'help.html', {'help_sections': help_sections})


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
        fallback_url = reverse('profile')

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

    else:
        if request.user.is_staff or request.user.is_superuser:
            info(_(u'Google Reader import started for user ID %s.') % user_id)

        else:
            info(_(u'Google Reader import started.'))

    return HttpResponseRedirect(redirect_url)


def google_reader_can_import_toggle(request, user_id):

    gri = GoogleReaderImport(user_id)

    gri.can_import = not gri.can_import

    return HttpResponseRedirect(request.META.get('HTTP_REFERER',
                                reverse('admin:index')))


# This one is protected directly in urls.py
def feed_closed_toggle(request, feed_id):

    feed = Feed.objects.get(id=feed_id)

    if feed.closed:
        feed.reopen()
    else:
        feed.close(u'Closed via the admin toggle button')

    return HttpResponseRedirect(request.META.get('HTTP_REFERER',
                                reverse('admin:index')))


def google_reader_import_stop(request, user_id):

    def info(text):
        messages.add_message(request, messages.INFO, text)

    gri          = GoogleReaderImport(user_id)
    redirect_url = request.META.get('HTTP_REFERER',
                                    reverse('admin:index'))

    user = User.objects.get(id=user_id)

    if gri.running():
        gri.end(True)
        info(u'Google Reader import stopped for user %s.' % user.username)
        return HttpResponseRedirect(redirect_url)

    if not gri.is_active:
        info(u'Google Reader import deactivated!')
        return HttpResponseRedirect(redirect_url)

    if not gri.can_import:
        info(u'User %s not allowed to import.' % user.username)
        return HttpResponseRedirect(redirect_url)

    return HttpResponseRedirect(redirect_url)


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
