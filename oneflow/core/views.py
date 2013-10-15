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
from django.utils.translation import ugettext_lazy as _, ugettext as __

#from infinite_pagination.paginator import InfinitePaginator
from endless_pagination.utils import get_page_number_from_request

from sparks.django.utils import HttpResponseTemporaryServerError

from .forms import (FullUserCreationForm,
                    UserProfileEditForm,
                    HomePreferencesForm,
                    ReadPreferencesForm,
                    SelectorPreferencesForm,
                    StaffPreferencesForm,
                    ManageFolderForm,
                    ManageSubscriptionForm,
                    AddSubscriptionForm)
from .tasks import import_google_reader_trigger
from .models.nonrel import Feed, Subscription, Read, Folder, TreeCycleException
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


# —————————————————————————————————————————————————————————————— Home / Sources


def home(request):
    """ root of the application. """

    # home_style = request.user.mongo.preferences.home.style
    # if home_style and home_style == 'T1':
    #     return HttpResponseRedirect(reverse(u'read'))

    return render(request, 'home.html', {
        'gr_import': GoogleReaderImport(request.user.id),
    })


def source_selector(request, **kwargs):

    if request.is_ajax():
        template = u'snippets/selector/selector.html'

    else:
        template = u'selector.html'

    mongo_user     = request.user.mongo
    selector_prefs = mongo_user.preferences.selector

    return render(request, template, {
        'subscriptions':               mongo_user.subscriptions,
        'nofolder_open_subscriptions': mongo_user.nofolder_open_subscriptions,
        'closed_subscriptions':        mongo_user.nofolder_closed_subscriptions,
        'show_closed_streams':         selector_prefs.show_closed_streams,
        'titles_show_unread_count':    selector_prefs.titles_show_unread_count,
        'folders_show_unread_count':   selector_prefs.folders_show_unread_count,
        })


def manage_folder(request, **kwargs):
    """ This view does add/edit functions. """

    folder_id = kwargs.pop('folder', None)
    folder    = Folder.get_or_404(folder_id) if folder_id else None
    edit_mode = folder is not None
    user      = request.user.mongo

    if request.POST:
        if edit_mode:
            form = ManageFolderForm(request.POST, instance=folder,
                                    owner=user)

        else:
            form = ManageFolderForm(request.POST, owner=user)

        if form.is_valid():

            try:
                folder = form.save(user)

            except TreeCycleException, e:
                messages.add_message(request, messages.ERROR,
                                     _(u'Save “{0}” failed: {1}').format(
                                         folder.name, e))

            else:

                messages.add_message(request, messages.INFO,
                                     _(u'Folder “{0}” successfully '
                                       u'{1}.').format(folder.name,
                                                       _(u'modified')
                                                       if edit_mode
                                                       else _(u'created')))

        else:
            messages.add_message(request, messages.WARNING,
                                 _(u'Could not {1} folder: {0}.').format(
                                     form.errors, _(u'modify') if edit_mode
                                     else _(u'create')))

            LOGGER.error(form.errors)

        return HttpResponseRedirect(reverse('source_selector')
                                    + (u"#{0}".format(folder.id)
                                       if folder else u''))

    else:
        if not request.is_ajax():
            return HttpResponseBadRequest('Did you forget to do an Ajax call?')

        if folder:
            form = ManageFolderForm(instance=folder, owner=user)

        else:
            form = ManageFolderForm(owner=user)

    return render(request, 'snippets/selector/manage-folder.html',
                  {'form': form, 'folder': folder})


def delete_folder(request, folder):

    folder = Folder.get_or_404(folder)

    if request.user.is_superuser or folder.owner == request.user.mongo:
        folder.delete()
        return HttpResponseRedirect(reverse('source_selector'))

    return HttpResponseForbidden()


def edit_subscription(request, **kwargs):

    subscription_id = kwargs.pop('subscription', None)
    subscription    = Subscription.get_or_404(subscription_id)

    if request.POST:
        form = ManageSubscriptionForm(request.POST, instance=subscription)

        if form.is_valid():
            subscription = form.save()

            messages.add_message(request, messages.INFO,
                                 _(u'Subscription “{0}” successfully '
                                   u'modified.').format(subscription.name))

        else:
            messages.add_message(request, messages.WARNING,
                                 _(u'Could not save '
                                   u'subscription: {0}.').format(
                                     form.errors))
            LOGGER.error(form.errors)

        return HttpResponseRedirect(reverse('source_selector')
                                    + u"#{0}".format(subscription.id))

    else:
        if not request.is_ajax():
            return HttpResponseBadRequest('Did you forget to do an Ajax call?')

        form = ManageSubscriptionForm(instance=subscription)

    return render(request, 'snippets/selector/manage-subscription.html',
                  {'form': form, 'subscription': subscription})


def add_subscription(request, **kwargs):

    if request.POST:
        form = AddSubscriptionForm(request.POST, owner=request.user.mongo)

        if form.is_valid():
            form.save()

        return HttpResponseRedirect(reverse('source_selector')
                                    + __(u'#unclassified-streams'))

    else:
        form = AddSubscriptionForm(owner=request.user.mongo)

    return render(request, 'add-subscription.html', {'form': form})


# ———————————————————————————————————————————————————————————————————————— Read


def _rwep_generate_query_kwargs(request, **kwargs):
    """ This is not a view, but an helper
        for read_with_endless_pagination(). """

    query_kwargs = {}
    combinations = set()
    attributes   = Read.status_data.keys()

    # First, get the view mode we were called from.
    if kwargs.get('all', False):
        # No particular kwargs for this one, but we
        # needed to pass in the 'if' to avoid the
        # default case where we get only the unread.
        pass

    else:
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

    return query_kwargs


def _rwep_generate_order_by(request, **kwargs):

    def check_order_by(value):
        if value in (u'id', u'title', ):
            return

        raise RuntimeError

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

    return order_by


def read_with_endless_pagination(request, **kwargs):

    query_kwargs = _rwep_generate_query_kwargs(request, **kwargs)
    order_by     = _rwep_generate_order_by(request, **kwargs)
    user         = request.user.mongo
    # preferences = user.preferences

    # ——————————————————————————————————————————————————— filter feed or folder

    feed = kwargs.get('feed', None)

    if feed:
        feed = Subscription.objects.get(id=feed)

        LOGGER.info(u'Refining reads by feed %s', feed)
        query_kwargs[u'subscriptions__contains'] = feed

    folder = kwargs.get('folder', None)

    if folder:
        folder = Folder.objects.get(id=folder)

        LOGGER.info(u'Refining reads by folder %s', folder)
        query_kwargs[u'subscriptions__in'] = \
            Subscription.objects(folders=folder)

    # ——————————————————————————————————————————————————————————————— the query

    #LOGGER.info(u'query_kwargs: %s', query_kwargs)

    reads = Read.objects(user=user,
                         **query_kwargs).order_by(order_by).no_cache()

    context = {
        u'reads': reads,

        # are we rendering the first "main"
        # page, or just a subset via ajax?
        u'initial': False,
    }

    # ——————————————————————————————————————————————————————————— Ajax requests

    if request.is_ajax():

        if request.GET.get('count', False):
            template = u'snippets/read/read-endless-count.html'
            count = context[u'reads_count'] = reads.count()

            #
            # TODO: compare / update the cached counters
            #

            attr_name = None

            if kwargs.get('all', False):
                attr_name = 'all_articles_count'

            elif query_kwargs.get('is_starred', False):
                attr_name = 'starred_articles_count'

            elif query_kwargs.get('is_bookmarked', False):
                attr_name = 'bookmarked_articles_count'

            elif query_kwargs.get('is_read__ne', None) is True:
                attr_name = 'unread_articles_count'

            if attr_name:
                if feed:
                    current_count = getattr(feed, attr_name)

                    if current_count != count:
                        LOGGER.info(u'Setting Subscription#%s.%s=%s for '
                                    u'Read.%s (old was: %s).',
                                    feed.id, attr_name, count, query_kwargs,
                                    current_count, )

                        # feed is really a nonrel.subscription
                        setattr(feed, attr_name, count)

                elif folder:
                    current_count = getattr(folder, attr_name)

                    if current_count != count:
                        LOGGER.info(u'Setting Folder#%s.%s=%s for Read.%s '
                                    u'(old was: %s).', folder.id, attr_name,
                                    count, query_kwargs, current_count)

                        setattr(folder, attr_name, count)

                else:
                    current_count = getattr(user, attr_name)

                    if current_count != count:
                        LOGGER.info(u'Setting User#%s.%s=%s for Read.%s '
                                    u'(old was: %s).', user.id, attr_name,
                                    count, query_kwargs, current_count)

                        setattr(user, attr_name, count)

        elif request.GET.get('mark_all_read', False):

            if feed:
                # feed is really a nonrel.subscription
                feed.mark_all_read()

            elif folder:
                for subscription in query_kwargs[u'subscriptions__in']:
                    subscription.mark_all_read()

            else:
                for subscription in user.subscriptions:
                    subscription.mark_all_read()

            return HttpResponse('DONE')

        else:
            template = u'snippets/read/read-endless-page.html'

            # Computing tenths_counter here is much efficient than doing:
            # {% captureas tenths_counter %}{{ request.GET['page']|mul:10 }}{% endcaptureas %} # NOQA
            # in the template…
            context[u'tenths_counter'] = \
                (get_page_number_from_request(request) - 1) \
                * config.READ_INFINITE_ITEMS_PER_FETCH

        # LOGGER.info(u'Ajax with %s', context.get('tenths_counter'))

    # ———————————————————————————————————————————————————— Standard GET request

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


# ————————————————————————————————————————————————————————————————— Preferences


def preferences(request):

    if request.POST:
        home_form = HomePreferencesForm(
                request.POST, instance=request.user.mongo.preferences.home)

        reading_form = ReadPreferencesForm(
                request.POST, instance=request.user.mongo.preferences.read)

        sources_form = SelectorPreferencesForm(
                request.POST, instance=request.user.mongo.preferences.selector)

        if request.user.is_superuser:
            staff_form = StaffPreferencesForm(
                    request.POST, instance=request.user.mongo.preferences.staff)

        if home_form.is_valid() and reading_form.is_valid() \
                and sources_form.is_valid() and (
                    request.user.is_superuser and staff_form.is_valid()) or 1:
            # form.save() does nothing on an embedded document,
            # which needs to be saved from the container.
            request.user.mongo.preferences.home = home_form.save()
            request.user.mongo.preferences.read = reading_form.save()
            request.user.mongo.preferences.selector = sources_form.save()

            if request.user.is_superuser:
                request.user.mongo.preferences.staff = staff_form.save()

            request.user.mongo.preferences.save()

            return HttpResponseRedirect(reverse('preferences'))
    else:
        home_form = HomePreferencesForm(
                instance=request.user.mongo.preferences.home)
        reading_form = ReadPreferencesForm(
                instance=request.user.mongo.preferences.read)
        sources_form = SelectorPreferencesForm(
                instance=request.user.mongo.preferences.selector)

        if request.user.is_superuser:
            staff_form = StaffPreferencesForm(
                    instance=request.user.mongo.preferences.staff)
        else:
            staff_form = None

    return render(request, 'preferences.html', {
                  'home_form': home_form,
                  'reading_form': reading_form,
                  'sources_form': sources_form,
                  'staff_form': staff_form,
                  })


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


# ——————————————————————————————————————————————————————————————————————— Other


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


# ———————————————————————————————————————————————————————— Google Reader Import


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
