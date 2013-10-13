# -*- coding: utf-8 -*-

from django.conf.urls import patterns, url
from django.views.generic import TemplateView
from django.views.decorators.cache import never_cache
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required

from .models.nonrel import Read

import views


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

# This builds "read_later_feed", "read_starred_feed" and so on.
read_patterns += tuple(
    url(attrval.get('list_url_feed'),
        login_required(never_cache(
            getattr(views, 'read_{0}_feed_with_endless_pagination'.format(
                attrval.get('view_name')))
            )
        ),
        name=u'read_' + attrval.get('view_name') + u'_feed')
    for attrkey, attrval
        in Read.status_data.items()
        if 'list_url_feed' in attrval
)

urlpatterns = patterns(
    'oneflow.core.views',
    url(_(r'^home/$'), login_required(never_cache(views.home)), name='home'),

    # This is the individual preference toggling.
    url(_(r'^preference/(?P<base>\w+)[\./](?P<sub>\w+)/(?P<value>\w+)/?$'),
        login_required(never_cache(views.set_preference)),
        name='set_preference'),

    # This is the user preferences view, where he can change them graphically.
    url(_(r'^preferences/$'), login_required(never_cache(views.preferences)),
        name='preferences'),

    url(_(r'^profile/$'), login_required(never_cache(views.profile)),
        name='profile'),

    url(_(r'^read/all/$'), never_cache(views.read_with_endless_pagination),
        name='read_all', kwargs={'all': True}),

    url(_(r'^read/all/feed/(?P<feed>(?:[0-9a-f]{24,24})+)$'),
        never_cache(views.read_all_feed_with_endless_pagination),
        name='read_all_feed'),

    url(_(r'^read/$'), login_required(never_cache(
        views.read_with_endless_pagination)), name='read',
        kwargs={'is_read': False}),  # , 'is_bookmarked': False}),

    url(_(r'^read/feed/(?P<feed>(?:[0-9a-f]{24,24})+)$'),
        login_required(never_cache(views.read_feed_with_endless_pagination)),
        name='read_feed'),

    url(_(r'^read/([0-9a-f]{24,24})/$'),
        login_required(views.read_one),
        name='read_one'),

    url(_(r'^selector/$'),
        login_required(never_cache(views.source_selector)),
        name='source_selector'),

    url(_(r'^folder/new/$'),
        login_required(never_cache(views.manage_folder)),
        name='add_folder'),

    url(_(r'^folder/(?P<folder>(?:[0-9a-f]{24,24})+)/delete$'),
        login_required(never_cache(views.delete_folder)),
        name='delete_folder'),

    url(_(r'^folder/(?P<folder>(?:[0-9a-f]{24,24})+)$'),
        login_required(never_cache(views.manage_folder)),
        name='edit_folder'),

    url(_(r'^subscription/(?P<subscription>(?:[0-9a-f]{24,24})+)$'),
        login_required(never_cache(views.edit_subscription)),
        name='edit_subscription'),

    url(_(r'^(?P<klass>\w+)/(?P<oid>\w+)/toggle/(?P<key>\w+.\w+)/?$'),
        login_required(never_cache(views.toggle)), name='toggle'),

    url(_(r'^help/$'), login_required(views.help), name='help'),

    url(_(r'^register/$'), views.register, name='register'),
    url(_(r'^signin_error/$'), TemplateView.as_view(
        template_name='signin_error.html'), name='signin_error'),

    # •••••••••••••••••••••••••••••••••••••••••••••••••••••••••••  Google Reader

    url(_(r'^grimport/(?:(?P<user_id>\d+)/)?$'),
        login_required(views.google_reader_import),
        name='google_reader_import'),
    url(_(r'^grstop/(?P<user_id>\d+)/$'),
        staff_member_required(views.google_reader_import_stop),
        name='google_reader_import_stop'),
    url(_(r'^grtoggle/(?P<user_id>\d+)/$'),
        staff_member_required(views.google_reader_can_import_toggle),
        name='google_reader_can_import_toggle'),
    url(_(r'^grstatus/$'), login_required(views.google_reader_import_status),
        name='google_reader_import_status'),

    # •••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••• Staff only

    url(_(r'^feed/(?P<feed_id>\w+)/close/toggle/$'),
        staff_member_required(views.feed_closed_toggle),
        name='feed_closed_toggle'),

    *read_patterns
)

urlpatterns += patterns(
    'django.contrib.auth.views',
    url(_(r'^signin/$'), 'login',
        {'template_name': 'signin.html'}, name='signin'),
    url(_(r'^signout/$'), 'logout',
        {'template_name': 'signout.html'}, name='signout'),
)
