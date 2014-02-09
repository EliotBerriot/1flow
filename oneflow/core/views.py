# -*- coding: utf-8 -*-
"""
    Copyright 2013-2014 Olivier Cortès <oc@1flow.io>

    This file is part of the 1flow project.

    1flow is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of
    the License, or (at your option) any later version.

    1flow is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public
    License along with 1flow.  If not, see http://www.gnu.org/licenses/

"""

import logging
import humanize

import gdata.gauth

from constance import config
from mongoengine import Q

from django.http import (HttpResponseRedirect,
                         HttpResponsePermanentRedirect,
                         HttpResponseForbidden,
                         HttpResponseBadRequest,
                         HttpResponse)
from django.core.urlresolvers import reverse
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from django.contrib import messages
from django.shortcuts import render, redirect
from django.template import add_to_builtins
#from django.views.generic import ListView
from django.contrib.auth import authenticate, login, get_user_model
from django.utils.translation import (ugettext_lazy as _,
                                      ugettext as __, ungettext)

from django_select2.views import Select2View

#from infinite_pagination.paginator import InfinitePaginator
#from contact_importer.decorators import get_contacts
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
                    AddSubscriptionForm,
                    WebPagesImportForm,
                    ReadShareForm)
from .tasks import import_google_reader_trigger
from .models.nonrel import (Feed, Subscription, FeedIsHtmlPageException,
                            Article, Read,
                            Folder, WebSite,
                            TreeCycleException, CONTENT_TYPES_FINAL)
from .models.reldb import HelpContent
from ..base.utils import word_match_consecutive_once
from ..base.utils.dateutils import now

from .gr_import import GoogleReaderImport

LOGGER = logging.getLogger(__name__)
User = get_user_model()

# Avoid repetitive {% load … %} in templates.
add_to_builtins('django.templatetags.i18n')
add_to_builtins('django.templatetags.cache')
add_to_builtins('djangojs.templatetags.js')
add_to_builtins('pipeline.templatetags.compressed')
add_to_builtins('absolute.templatetags.absolute_future')
add_to_builtins('markdown_deux.templatetags.markdown_deux_tags')
add_to_builtins('widget_tweaks.templatetags.widget_tweaks')
add_to_builtins('endless_pagination.templatetags.endless')
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


def read_feed_with_endless_pagination(request, **kwargs):

    kwargs.update({'is_read': False})  # , 'is_bookmarked': False})
    return read_with_endless_pagination(request, **kwargs)


def read_all_feed_with_endless_pagination(request, **kwargs):

    kwargs[u'all'] = True
    return read_with_endless_pagination(request, **kwargs)


def read_folder_with_endless_pagination(request, **kwargs):

    kwargs.update({'is_read': False})  # , 'is_bookmarked': False})
    return read_with_endless_pagination(request, **kwargs)


def read_all_folder_with_endless_pagination(request, **kwargs):

    kwargs[u'all'] = True
    return read_with_endless_pagination(request, **kwargs)


def make_read_wrapper(attrkey, typekey, view_name):
    """ See http://stackoverflow.com/a/3431699/654755 for why."""

    def func(request, **kwargs):
        kwargs[attrkey] = True
        return read_with_endless_pagination(request, **kwargs)

    final_func_name = 'read_{0}_{1}_with_endless_pagination'.format(view_name,
                                                                    typekey)

    #LOGGER.info(u'registered %s', final_func_name)

    globals()[final_func_name] = func


# This builds "read_later_feed_with_endless_pagination",
# 'read_later_folder_with_endless_pagination' and so on.

for attrkey, attrval in Read.status_data.items():
    if 'list_url' in attrval:
        # HEADS UP: sync the second argument with urls.py
        make_read_wrapper(attrkey, 'feed', attrval.get('view_name'))
        make_read_wrapper(attrkey, 'folder', attrval.get('view_name'))


# —————————————————————————————————————————————————————————————— Home / Sources


def skip_welcome_beta(request):

    user = request.user.mongo

    user.preferences.wizards.welcome_beta_shown = True
    user.preferences.save()

    # NOTE: The next 3 lines of code have to
    #       be synched with the home() view.

    if user.has_content:
        return redirect('source_selector')

    return redirect('add_subscription')


def home(request):
    """ root of the application. """

    user    = request.user.mongo
    wizards = user.preferences.wizards

    if wizards.welcome_beta_shown or not wizards.show_all:

        # NOTE: The next 3 lines of code have to be synched
        #       with the skip_welcome_beta() view.

        if user.has_content:
            return redirect('source_selector')

        return redirect('add_subscription')

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
        messages.info(request, u'manage folder POST "%s"' % request.POST,
                      extra_tags='safe')

        if edit_mode:
            messages.info(request, u'manage folder EDIT %s' % folder,
                          extra_tags='safe')

            form = ManageFolderForm(request.POST, instance=folder,
                                    owner=user)

        else:
            form = ManageFolderForm(request.POST, owner=user)

        if form.is_valid():

            try:
                folder = form.save()

            except TreeCycleException, e:
                messages.error(request, _(u'Save <em>{0}</em> '
                               u'failed: {1}').format(folder.name, e),
                               extra_tags=u'safe')

            else:
                messages.info(request, _(u'Folder <em>{0}</em> successfully '
                              u'{1}.').format(folder.name, _(u'modified')
                                              if edit_mode else _(u'created')),
                              extra_tags=u'safe')

        else:
            messages.info(request, u'TEST2', extra_tags='safe')
            messages.warning(request, _(u'Could not {0} folder: {1}.').format(
                             _(u'modify') if edit_mode else _(u'create'),
                             form.errors), extra_tags='sticky safe')

            LOGGER.error(u'%s: %s', form.errors, form.cleaned_data)

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
        return redirect('source_selector')

    return HttpResponseForbidden()


def edit_subscription(request, **kwargs):

    subscription_id = kwargs.pop('subscription', None)
    subscription    = Subscription.get_or_404(subscription_id)

    if request.POST:
        form = ManageSubscriptionForm(request.POST, instance=subscription)

        if form.is_valid():
            subscription = form.save()

            messages.info(request, _(u'Subscription <em>{0}</em> successfully '
                          u'modified.').format(subscription.name),
                          extra_tags='safe')

        else:
            messages.warning(request, _(u'Could not save '
                             u'subscription: {0}.').format(form.errors),
                             extra_tags='safe')

            LOGGER.error(form.errors)

        return HttpResponseRedirect(reverse('source_selector')
                                    + u"#{0}".format(subscription.id))

    else:
        if not request.is_ajax():
            return HttpResponseBadRequest('Did you forget to do an Ajax call?')

        form = ManageSubscriptionForm(instance=subscription)

    return render(request, 'snippets/selector/manage-subscription.html',
                  {'form': form, 'subscription': subscription})


def add_feed(request, feed_url, subscribe=True):
    """ The :param`subscribe` parameter is set to False for staff members
        who use a different URL. """

    user = request.user.mongo
    feeds = []
    feed = subscription = None
    feed_exc = sub_exc = None
    created = already_subscribed = False

    # Sanitize the URL as much as possible. Try to get the REFERER if the
    # user manually typed the address in the URL bar of his browser.
    try:
        if not feed_url.startswith(u'http'):
            if request.META.get('HTTP_REFERER', None):
                proto, host_and_port, remaining = WebSite.split_url(
                    request.META['HTTP_REFERER'])

                feed_url = u'{0}://{1}{2}{3}'.format(
                    proto, host_and_port,
                    u'' if feed_url.startswith(u'/') else u'/',
                    feed_url)

            else:
                LOGGER.error(u'Bad url {0} while trying to add a '
                             u'feed.'.format(feed_url))
                feed_exc = _(u'Malformed URL {0}').format(feed_url)

    except:
        LOGGER.exception(u'Very bad url {0} while trying to add a '
                         u'feed.'.format(feed_url))
        feed_exc = _(u'Very malformed url {0}').format(feed_url)

    if feed_exc is None:
        try:
            feeds = Feed.create_feeds_from_url(feed_url)

        except FeedIsHtmlPageException:
            feed_exc = _(u'The website at {0} does not seem '
                         u'to provide any feed.').format(feed_url)

        except Exception, e:
            feed_exc = _(u'Could not create any feed from '
                         u'URL {0}: {1}').format(feed_url, e)

    if feeds:
        # Taking the first is completely arbitrary, but better than nothing.
        # TODO: enhance this with a nice form to show all feeds to the user.
        feed, created = feeds[0]

        if subscribe:

            # Then subscribe the user to this feed,
            # and don't fail if he's already subscribed.
            try:
                subscription = Subscription.objects.get(user=user, feed=feed)

            except Subscription.DoesNotExist:
                try:
                    subscription = Subscription.subscribe_user_to_feed(
                        user, feed, background=True)

                except Exception, sub_exc:
                    LOGGER.exception(u'Failed to subscribe user %s to feed %s',
                                     user, feed)

            else:
                already_subscribed = True

    return render(request, 'add-feed.html', {
                  'feed': feed, 'created': created, 'feeds': feeds,
                  'subscription': subscription,
                  'already_subscribed': already_subscribed,
                  'subscribe': subscribe,
                  'feed_exc': feed_exc, 'sub_exc': sub_exc})


def add_subscription(request, **kwargs):

    if request.POST:
        form = AddSubscriptionForm(request.POST, owner=request.user.mongo)

        if form.is_valid():
            added = form.save()

            messages.info(request, _(u'Successfully subscribed to {0} '
                          u'streams. Articles are being added progressively, '
                          u'thanks for your patience.').format(len(added)))

            return HttpResponseRedirect(reverse('source_selector')
                                        + u'#' + __(u'unclassified-streams'))

    else:
        form = AddSubscriptionForm(owner=request.user.mongo)

    return render(request, 'add-subscription.html', {'form': form})


def delete_subscription(request, **kwargs):

    subscription_id = kwargs.pop('subscription', None)
    subscription    = Subscription.get_or_404(subscription_id)

    if request.user.is_superuser or subscription.user == request.user.mongo:

        subscription.delete()

        messages.info(request, _(u'Subscription <em>{0}</em> successfully '
                      u'deleted.').format(subscription.name),
                      extra_tags=u'safe')

        return redirect('source_selector')

    return HttpResponseForbidden()


class FeedsCompleterView(Select2View):

    def get_results(self, request, term, page, context):

        return (
            'nil',
            False,
            #
            # NOTE: this query is replicated in the form,
            #       to get the count() in the placeholder.
            #
            # we use unicode(id) to avoid
            # “ObjectId('51c8a0858af8069f5bafbb5a') is not JSON serializable”
            [(unicode(f.id), f.name) for f in Feed.good_feeds(
                id__nin=[s.feed.id for s in request.user.mongo.subscriptions]
            ).filter(Q(name__icontains=term) | Q(site_url__icontains=term))]
        )


# ———————————————————————————————————————————————————————————————————————— Read


def _rwep_generate_query_kwargs(request, **kwargs):
    """ This is not a view, but an helper
        for read_with_endless_pagination(). """

    query_kwargs = {}
    primary_mode = None
    combinations = set()
    attributes   = Read.status_data.keys()

    # First, get the view mode we were called from.
    if kwargs.get('all', False):
        # No particular kwargs for this one, but we
        # needed to pass in the 'if' to avoid the
        # default case where we get only the unread.
        primary_mode = (u'all', False)

    else:
        for attrname in attributes:
            mykwarg = kwargs.get(attrname, None)

            if mykwarg is not None:
                primary_mode = (attrname, mykwarg)

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

    return query_kwargs, primary_mode


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


def _rwep_ajax_update_counters(kwargs, query_kwargs,
                               subscription, folder,
                               user, count):

    attr_name = None

    #LOGGER.info(query_kwargs)

    if kwargs.get('all', False):
        attr_name = u'all_articles_count'

    elif query_kwargs.get('is_starred', False):
        attr_name = u'starred_articles_count'

    elif query_kwargs.get('is_bookmarked', False):
        attr_name = u'bookmarked_articles_count'

    elif query_kwargs.get('is_read__ne', None) is True:
        attr_name = u'unread_articles_count'

    if attr_name:
        if subscription:
            current_count = getattr(subscription, attr_name)

            if current_count != count:
                setattr(subscription, attr_name, count)

                LOGGER.info(u'Updated Subscription#%s.%s=%s for '
                            u'Read.%s (old was: %s).',
                            subscription.id, attr_name, count,
                            unicode(query_kwargs), current_count)

                # TODO: update folder with diff.

        elif folder:
            current_count = getattr(folder, attr_name)

            if current_count != count:
                setattr(folder, attr_name, count)

                LOGGER.info(u'Updated Folder#%s.%s=%s for Read.%s '
                            u'(old was: %s).', folder.id, attr_name,
                            count, unicode(query_kwargs), current_count)

                # TODO: recount()/update all subscriptions counters…

        else:
            current_count = getattr(user, attr_name)

            if current_count != count:
                setattr(user, attr_name, count)

                LOGGER.info(u'Updated User#%s.%s=%s for Read.%s '
                            u'(old was: %s).', user.id, attr_name,
                            count, query_kwargs, current_count)


def _rwep_special_update_counters(subscription, user):

    if subscription == user.web_import_subscription:
        for attr_name, count in (
            ('unread_articles_count',
             subscription.reads(is_read__ne=True).count()),
        ):
            current_count = getattr(subscription, attr_name)

            if current_count != count:
                LOGGER.info(u'Setting Import Subscription#%s.%s=%s '
                            u'(old was: %s).', subscription.id, attr_name,
                            count, current_count, )

                # subscription is really a nonrel.subscription
                setattr(subscription, attr_name, count)


def _rwep_ajax_mark_all_read(subscription, folder, user, latest_displayed_read):

    if subscription:
        subscription.mark_all_read(latest_displayed_read)

    elif folder:
        for subscription in folder.subscriptions:
            subscription.mark_all_read(latest_displayed_read)

    else:
        for subscription in user.subscriptions:
            subscription.mark_all_read(latest_displayed_read)


def _rwep_build_page_header_text(subscription, folder, user, primary_mode):

    mode, negated = primary_mode

    if mode == 'is_read' and not negated:
        mode = 'is_unread'

    attr_name = (u'all_articles_count'
                 if mode == u'all'
                 else mode[3:] + u'_articles_count')

    singular_text, plural_text = Read.status_data[mode]['list_headers']

    if subscription:
        count = getattr(subscription, attr_name)

        header_text_left = subscription.name

    elif folder:
        count     = getattr(folder, attr_name)
        sub_count = folder.subscriptions.count()

        header_text_left = folder.name + ungettext(
            u' (%(count)s subscription)',
            u' (%(count)s subscriptions)', sub_count) % {'count': sub_count}

    else:
        count     = getattr(user, attr_name)
        sub_count = user.subscriptions.count()

        header_text_left = ungettext(
            u'In your <span class="hide">%(count)s</span> subscription',
            u'In your %(count)s subscriptions', sub_count) % {
            'count': sub_count}

    header_text_right = ungettext(singular_text, plural_text, count) % {
        'count': count}

    return header_text_left, header_text_right


def read_with_endless_pagination(request, **kwargs):

    (query_kwargs,
     primary_mode) = _rwep_generate_query_kwargs(request, **kwargs)
    order_by       = _rwep_generate_order_by(request, **kwargs)
    djuser         = request.user
    user           = djuser.mongo
    preferences    = user.preferences

    # —————————————————————————————————————————————————— subscription or folder

    # "feed" (from the user point of view) is actually
    # a subscription (from the developer point of view).
    subscription = kwargs.get('feed', None)

    if subscription:
        subscription = Subscription.get_or_404(subscription)

        if subscription.user != user:
            if user.is_staff_or_superuser_and_enabled:

                messages.warning(request, _(u'As administrator, you are '
                                 u'accessing the feed of another user. '
                                 u'USE WITH CAUTION.'), extra_tags='sticky')

            else:
                return HttpResponseForbidden('Not Owner')

        #LOGGER.info(u'Refining reads by subscription %s', subscription)

        query_kwargs[u'subscriptions__contains'] = subscription

    folder = kwargs.get('folder', None)

    if folder:
        folder = Folder.get_or_404(folder)

        if folder.owner != user:
            if user.is_staff_or_superuser_and_enabled:
                messages.warning(request, _(u'As administrator, you are '
                                 u'accessing the feed of another user. '
                                 u'USE WITH CAUTION.'), extra_tags='sticky')

            else:
                return HttpResponseForbidden('Not Owner')

        # LOGGER.info(u'Refining reads by folder %s', folder)

        query_kwargs[u'subscriptions__in'] = \
            Subscription.objects(folders=folder)

    # ——————————————————————————————————————————————————————————————— the query

    #LOGGER.info(u'query_kwargs: %s', query_kwargs)

    reads = user.reads(**query_kwargs).order_by(order_by).no_cache()

    header_text_left, header_text_right = _rwep_build_page_header_text(
        subscription, folder, user, primary_mode)

    context = {
        u'reads': reads,
        u'subscription': subscription,
        u'folder': folder,
        u'current_mode': primary_mode[0],

        # 'user' is already there, via a context processor.

        u'read_page_header_text_left': header_text_left,
        u'read_page_header_text_right': header_text_right,

        # are we rendering the first "main"
        # page, or just a subset via ajax?
        u'initial': False,
    }

    # ——————————————————————————————————————————————————————————— Ajax requests

    if request.is_ajax():

        if request.GET.get('count', False):
            count = reads.count()

            #
            # Check and update cache counters
            #

            try:
                _rwep_ajax_update_counters(kwargs, query_kwargs,
                                           subscription, folder, user, count)
            except UnicodeDecodeError:
                pass

            if subscription:
                _rwep_special_update_counters(subscription, user)

            #
            # prepare the "inline mini-template" for ajax update.
            #

            mode, negated = primary_mode

            if mode == 'is_read' and not negated:
                mode = 'is_unread'

            singular_text, plural_text = Read.status_data[mode]['list_headers']

            if count == 0:
                rendered_text = _(u'no item')

            elif count == 1:
                rendered_text = singular_text % {'count': count}

            else:
                rendered_text = plural_text % {'count': count}

            return HttpResponse(rendered_text)

        elif request.GET.get('mark_all_read', False):

            latest_displayed_read = user.reads.get(
                article=Article.objects.get(
                    id=request.GET.get('mark_all_read')))

            _rwep_ajax_mark_all_read(subscription, folder, user,
                                     latest_displayed_read)

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


def article_content(request, article_id):

    try:
        article = Article.get_or_404(article_id)

    except:
        return HttpResponseTemporaryServerError()

    try:
        read = Read.get_or_404(article=article, user=request.user.mongo)

    except:
        return HttpResponseTemporaryServerError()

    if not request.is_ajax():
        return HttpResponseBadRequest('Must be called via Ajax')

    return render(request,
                  'snippets/read/article-content-async.html',
                  {'article': article, 'read': read})


def read_meta(request, read_id):

    try:
        read = Read.get_or_404(read_id)

    except:
        return HttpResponseTemporaryServerError()

    if not request.is_ajax() and not settings.DEBUG:
        return HttpResponseBadRequest('Must be called via Ajax')

    return render(request,
                  'snippets/read/read-meta-async.html',
                  {'read': read, 'article': read.article})


def read_one(request, read_id):

    try:
        read = Read.get_or_404(read_id)

    except:
        return HttpResponseTemporaryServerError()

    user = request.user.mongo

    if read.user != user:
        # Most probably, a user has shared
        # his read_one() url with another user.

        cloned_read, created = user.received_items_subscription.create_read(
            article=read.article)

        cloned_read.update(add_to_set__senders=read.user)

        if created:
            message = _(u'{1} shared <em>{0}</em> with you.').format(
                read.article.title, read.user.get_full_name())
        else:
            message = _(u'Recorded <em>{0}</em> as shared by {1} '
                        u'in your inbox.').format(
                read.article.title, read.user.get_full_name())

        messages.info(request, message, extra_tags='safe')

        return HttpResponsePermanentRedirect(
            u'http://' + settings.SITE_DOMAIN
            + reverse('read_one', args=(cloned_read.id,)))

    if request.is_ajax():
        template = u'snippets/read/read-one.html'

    else:
        template = u'read-one.html'

    return render(request, template, {'read': read})


def share_one(request, article_id):

    if not request.is_ajax():
        return HttpResponseBadRequest(u'Ajax is needed for this…')

    try:
        article = Article.get_or_404(article_id)
        read    = Read.get_or_404(article=article, user=request.user.mongo)

    except:
        LOGGER.exception(u'Could not load things to share article #%s',
                         article_id)
        return HttpResponseTemporaryServerError('BOOM')

    if request.POST:
        form = ReadShareForm(request.POST, user=request.user.mongo)

        if form.is_valid():
            sent, failed = form.save()

            if failed:
                for address, reason in failed:
                    messages.warning(request,
                                     _(u'Share article with <code>{0}</code> '
                                       u'failed: {1}').format(address, reason),
                                     extra_tags='sticky safe')

            if sent:
                messages.info(request,
                              _(u'Successfully shared <em>{0}</em> '
                                u'with {1} persons').format(
                                  read.article.title, len(sent)),
                              extra_tags='safe')

            return HttpResponse(u'DONE')

    else:
        form = ReadShareForm(user=request.user.mongo)

    return render(request, u'snippets/share/share-one.html',
                  {'read': read, 'form': form})


class UserAddressBookView(Select2View):

    def get_results(self, request, term, page, context):

        term = term.lower()

        return (
            'nil',
            False,
            [r for r in request.user.mongo.relations
             if word_match_consecutive_once(term, r[1].lower())]
        )

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

            return redirect('preferences')
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

    if 'staff' in base and not (request.user.is_staff
                                or request.user.is_superuser):
        return HttpResponseForbidden(u'forbidden')

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


def preference_toggle(request, base, sub):
    """ Handy for boolean preferences. """

    try:
        base_pref = getattr(request.user.mongo.preferences, base)
        value     = not getattr(base_pref, sub)

    except:
        return HttpResponseBadRequest(u'Bad preference name or value.')

    else:
        return set_preference(request, base, sub, value)


def toggle(request, klass, oid, key):

    #
    # TODO: push notifications on error to the user.
    #

    try:
        obj = globals()[klass].get_or_404(oid)

    except:
        return HttpResponseTemporaryServerError()

    if not obj.check_owner(request.user.mongo):
        return HttpResponseForbidden(u'Not owner')

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


def import_web_url(request, url):

    form = WebPagesImportForm({'urls': url}, request=request)

    article = None

    if form.is_valid():
        created, failed = form.save()

        article = created[0]

        # Just in case the item was previously
        # here (from another user, or the same).
        if article.content_type in CONTENT_TYPES_FINAL:
            read = Read.get_or_404(user=request.user.mongo,
                                   article=article)

            return HttpResponsePermanentRedirect(
                u'http://' + settings.SITE_DOMAIN
                + reverse('read_one', args=(read.id,)))

    return render(request, 'import-web-url.html',
                  {'article': article, 'url': url,
                   'poll_url': reverse('article_conversion_status',
                                       args=(article.id,))})


def article_conversion_status(request, article_id):

    try:
        article = Article.get_or_404(article_id)

    except:
        return HttpResponseTemporaryServerError(
            u'Could not find article #{0}'.format(article_id))

    if article.content_type in CONTENT_TYPES_FINAL:

        read = Read.get_or_404(user=request.user.mongo, article=article)

        return HttpResponse(u'http://' + settings.SITE_DOMAIN +
                            reverse('read_one', args=(read.id,)))

    res = HttpResponse(u'IN PROGRESS')
    res.status = 202

    return res


def import_web_pages(request):

    if not request.is_ajax():
        return HttpResponseBadRequest('This request needs Ajax')

    if request.POST:
        form = WebPagesImportForm(request.POST,
                                  # This is our own kwargs parameter.
                                  request=request)

        if form.is_valid():
            created, failed = form.save()

        #
        # TODO: return a JSON when request comes from browser extensions.
        #
        return render(request,
                      'snippets/selector/import-web-items-result.html',
                      {'created': created, 'failed': failed})

    else:
        form = WebPagesImportForm()

    return render(request, 'snippets/selector/import-web-pages.html',
                  {'form': form})


def import_contacts(request):
    """

        Reference, as of 20140102:
            http://stackoverflow.com/a/14161012/654755
    """

    auth_token = gdata.gauth.OAuth2Token(
        client_id=settings.GOOGLE_OAUTH2_CLIENT_ID,
        client_secret=settings.GOOGLE_OAUTH2_CLIENT_SECRET,
        scope=settings.GOOGLE_OAUTH2_CONTACTS_SCOPE,
        user_agent=settings.DEFAULT_USER_AGENT)

    authorize_url = auth_token.generate_authorize_url(
        redirect_uri='http://{0}{1}'.format(
            settings.SITE_DOMAIN,
            settings.GOOGLE_OAUTH2_CONTACTS_REDIRECT_URI
        )
    )

    return HttpResponseRedirect(authorize_url)


def import_contacts_authorized(request):
    """
        Reference, as of 20140102:
            https://developers.google.com/google-apps/contacts/v3/
    """
    import gdata.contacts.client

    user          = request.user.mongo
    dupes         = 0
    imported      = 0
    address_book  = set(a.rsplit(u' ', 1)[1] for a in user.address_book)

    current_mails = address_book.copy()
    current_mails |= [f.email for f in user.friends]

    auth_token = gdata.gauth.OAuth2Token(
        client_id=settings.GOOGLE_OAUTH2_CLIENT_ID,
        client_secret=settings.GOOGLE_OAUTH2_CLIENT_SECRET,
        scope=settings.GOOGLE_OAUTH2_CONTACTS_SCOPE,
        user_agent=settings.DEFAULT_USER_AGENT)

    auth_token.redirect_uri = 'http://{0}{1}'.format(
        settings.SITE_DOMAIN,
        settings.GOOGLE_OAUTH2_CONTACTS_REDIRECT_URI
    )

    # Heads UP: as of 20130104, "service" seems to be broken.
    # Google invites to use "client" instead.
    # Ref: https://code.google.com/p/gdata-python-client/issues/detail?id=549
    #client = gdata.contacts.service.ContactsService(source='1flow.io')
    client = gdata.contacts.client.ContactsClient(source='1flow.io')

    auth_token.get_access_token(request.GET['code'])
    auth_token.authorize(client)

    query = gdata.contacts.client.ContactsQuery()
    #query.updated_min = '2008-01-01'
    query.max_results = 1000

    feed = client.GetContacts(q=query)

    # The "all contacts" way, but it only return a limited subset of them.
    #feed = client.GetContacts()

    for entry in feed.entry:

        full_name = first_name = last_name = u''

        try:
            full_name = u'{0} {1}'.format(
                entry.name.given_name.text,
                entry.name.family_name.text
            )

        except AttributeError:
            try:
                full_name = entry.name.full_name.text

            except:
                pass

            else:
                try:
                    first_name, last_name = full_name.split(u' ', 1)

                except:
                    pass
        else:
            first_name = entry.name.given_name.text
            last_name  = entry.name.family_name.text

        for email in entry.email:

            if email.primary and email.primary == 'true':

                if email.address in current_mails:
                    if email.address in address_book:
                        user.ab_remove(email.address)

                        # NOTE: User is the Django User model here.
                        friend = User.get_or_create_friend(
                            email=email.address,
                            first_name=first_name,
                            last_name=last_name
                        )

                    else:
                        dupes += 1

                else:
                    user.address_book.append(
                        u'{0} {1}'.format(full_name or email.address,
                                          email.address))
                    imported += 1

        #for group in entry.group_membership_info:
        #    print '    Member of group: %s' % (group.href)

    if imported:
        user.save()

    return render(request, 'import-contacts.html', {
        'imported': imported, 'dupes': dupes
    })


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

            return redirect('home')

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
        messages.info(request, text)

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
        messages.info(request, text)

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
                    'status': 'running',
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
