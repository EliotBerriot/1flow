# -*- coding: utf-8 -*-

from django.conf.urls import patterns, url
from django.views.generic import TemplateView
from django.views.decorators.cache import cache_page, never_cache
from django.utils.translation import ugettext_lazy as _, pgettext_lazy
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required

from .models.nonrel import Read

import views

LONG_CACHE = 3600*24


# This builds "read_later", "read_starred" and so on.
read_patterns = tuple(
    url(attrval.get('list_url'),
        login_required(never_cache(
            views.read_with_endless_pagination)),
        name=u'read_' + attrval.get('view_name'),
        kwargs={attrkey: True})
    for attrkey, attrval
        in Read.status_data.items()
        if 'list_url' in attrval
)

# This builds all feeds and folders related URLs, and there are a lot.
for url_trans, url_untrans in (
            # HEADS UP: sync this list with views.py
            (pgettext_lazy(u'part of url regex', u'feed'), u'feed'),
            (pgettext_lazy(u'part of url regex', u'folder'), u'folder')):

    suffix = u'_' + url_untrans

    type_url = ur'%s/(?P<%s>(?:[0-9a-f]{24,24})+)$' % (url_trans, url_untrans)

    read_patterns += tuple((
        url(
            _(ur'^read/') + type_url,
            login_required(
                never_cache(
                    getattr(views, 'read_%s_with_endless_pagination'
                            % url_untrans)
                )
            ),
            name=u'read' + suffix),
        url(
            _(ur'^read/all/') + type_url,
            login_required(
                never_cache(
                    getattr(views, 'read_all_%s_with_endless_pagination'
                            % url_untrans)
                )
            ),
            name='read_all' + suffix),
        ))

    read_patterns += tuple(
        url(attrval.get('list_url').replace(u'$', type_url),
            login_required(never_cache(
                getattr(views, 'read_{0}_feed_with_endless_pagination'.format(
                    attrval.get('view_name')))
                )
            ),
            name=u'read_' + attrval.get('view_name') + suffix)
        for attrkey, attrval
            in Read.status_data.items()
            if 'list_url' in attrval
    )

urlpatterns = patterns(
    'oneflow.core.views',
    url(_(ur'^home/$'), login_required(never_cache(views.home)), name='home'),

    url(_(ur'^skip-welcome-beta/$'), login_required(
        never_cache(views.skip_welcome_beta)), name='skip_welcome_beta'),

    # This is the individual preference assignment.
    url(_(ur'^preference/(?P<base>\w+)[\./](?P<sub>\w+)/(?P<value>\w+)/?$'),
        login_required(never_cache(views.set_preference)),
        name='set_preference'),

    # This is the individual preference toggling.
    url(_(ur'^preference/toggle/(?P<base>\w+)[\./](?P<sub>\w+)/?$'),
        login_required(never_cache(views.preference_toggle)),
        name='preference_toggle'),

    # This is the user preferences view, where he can change them graphically.
    url(_(ur'^preferences/$'), login_required(never_cache(views.preferences)),
        name='preferences'),

    url(_(ur'^profile/$'), login_required(never_cache(views.profile)),
        name='profile'),

    url(_(ur'^read/all/$'), never_cache(views.read_with_endless_pagination),
        name='read_all', kwargs={'all': True}),

    url(_(ur'^read/meta/([0-9a-f]{24,24})/$'),
        login_required(never_cache(views.read_meta)),
        name='read_meta'),

    url(_(ur'^read/$'), login_required(never_cache(
        views.read_with_endless_pagination)), name='read',
        kwargs={'is_read': False}),  # , 'is_bookmarked': False}),

    url(_(ur'^article/([0-9a-f]{24,24})/$'),
        login_required(never_cache(views.article_content)),
        name='article_content'),

    url(_(ur'^read/([0-9a-f]{24,24})/$'),
        login_required(never_cache(views.read_one)),
        name='read_one'),

    url(_(ur'^selector/$'),
        login_required(never_cache(views.source_selector)),
        name='source_selector'),

    url(_(ur'^folder/new/$'),
        login_required(never_cache(views.manage_folder)),
        name='add_folder'),

    url(_(ur'^folder/(?P<folder>(?:[0-9a-f]{24,24})+)/delete$'),
        login_required(never_cache(views.delete_folder)),
        name='delete_folder'),

    url(_(ur'^folder/(?P<folder>(?:[0-9a-f]{24,24})+)$'),
        login_required(never_cache(views.manage_folder)),
        name='edit_folder'),

    url(_(ur'^subscription/new/$'),
        login_required(never_cache(views.add_subscription)),
        name='add_subscription'),

    # Required by the add_subscription autocompleter.
    # TODO: once we have an expirable cache mechanism, switch to
    # VERY_LONG_CACHE and make it expire on feeds changes (closing,
    # creation, etc).
    url(_(ur'^json/feeds-completer/$'),
        login_required(cache_page(LONG_CACHE)(
                       views.FeedsCompleterView.as_view())),
        name='feeds_completer'),

    url(_(ur'^subscription/(?P<subscription>(?:[0-9a-f]{24,24})+)/delete$'),
        login_required(never_cache(views.delete_subscription)),
        name='delete_subscription'),

    url(_(ur'^subscription/(?P<subscription>(?:[0-9a-f]{24,24})+)$'),
        login_required(never_cache(views.edit_subscription)),
        name='edit_subscription'),

    url(_(ur'^webimport/$'),
        login_required(never_cache(views.import_web_pages)),
        name='import_web_pages'),

    url(_(ur'^(?P<klass>\w+)/(?P<oid>\w+)/toggle/(?P<key>\w+.\w+)/?$'),
        login_required(never_cache(views.toggle)), name='toggle'),

    url(_(ur'^help/$'), login_required(views.help), name='help'),

    url(_(ur'^register/$'), views.register, name='register'),
    url(_(ur'^signin_error/$'), TemplateView.as_view(
        template_name='signin_error.html'), name='signin_error'),

    # •••••••••••••••••••••••••••••••••••••••••••••••••••••••••••  Google Reader

    url(_(ur'^grimport/(?:(?P<user_id>\d+)/)?$'),
        login_required(views.google_reader_import),
        name='google_reader_import'),
    url(_(ur'^grstop/(?P<user_id>\d+)/$'),
        staff_member_required(views.google_reader_import_stop),
        name='google_reader_import_stop'),
    url(_(ur'^grtoggle/(?P<user_id>\d+)/$'),
        staff_member_required(views.google_reader_can_import_toggle),
        name='google_reader_can_import_toggle'),
    url(_(ur'^grstatus/$'), login_required(views.google_reader_import_status),
        name='google_reader_import_status'),

    # •••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••• Staff only

    url(_(ur'^feed/(?P<feed_id>\w+)/close/toggle/$'),
        staff_member_required(views.feed_closed_toggle),
        name='feed_closed_toggle'),

    *read_patterns
)

urlpatterns += patterns(
    'django.contrib.auth.views',
    url(_(ur'^signin/$'), 'login',
        {'template_name': 'signin.html'}, name='signin'),
    url(_(ur'^signout/$'), 'logout',
        {'template_name': 'signout.html'}, name='signout'),
)
