# -*- coding: utf-8 -*-

from django.conf import settings
from django.conf.urls import patterns, include, url
from django.conf.urls.i18n import i18n_patterns
from django.views.generic import TemplateView
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

# We use mongoadmin, which already includes Django's admin site
from django.contrib import admin as django_admin

try:
    django_admin.autodiscover()
except ImportError, e:
    raise RuntimeError("you probably need to patch Django's auth admin module "
                       "not to auto-discover auth when User._meta.swapped. "
                       "Original exception: %s." % e)

import mongoadmin as admin

from .api import v1_api


handler404 = 'oneflow.base.views.not_found_handler'
handler500 = 'oneflow.base.views.error_handler'
handler503 = 'oneflow.base.views.maintenance_mode'

# urlpatterns = patterns('',
#     url(r'^sitemap\.xml$', 'sitemap.view', name='sitemap_xml'),
# )

urlpatterns = patterns(
    '',
    url(r'', include('oneflow.base.urls')),
    url(r'', include('social_auth.urls')),
    url(r'^robots\.txt$', TemplateView.as_view(template_name='robots.txt',
        content_type='text/plain')),
    url(r'^humans\.txt$', TemplateView.as_view(template_name='humans.txt',
        content_type='text/plain')),
    url(r'^i18n/', include('django.conf.urls.i18n')),
    url(r'^djangojs/', include('djangojs.urls')),
)

urlpatterns += i18n_patterns(
    '',
    # NEVER use r'^$', this won't work as expected. Use r''.
    url(r'', include('oneflow.landing.urls')),
    url(r'', include('oneflow.core.urls')),
)

# WARNING: when sites are spread across different machines, rosetta
# must be migrated to run on only one dedicated, to avoid messing
# with partially translated .PO files on many 1flow servers.
if 'rosetta' in settings.INSTALLED_APPS:
    urlpatterns += patterns(
        '', url(r'^translate/', include('rosetta.urls')),
    )

urlpatterns += patterns(
    '',
    url(r'^grappelli/', include('grappelli.urls')),
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    url(r'^admin/', include(admin.site.urls)),
)

urlpatterns += patterns(
    '',
    url(r'^api/', include(v1_api.urls)),
)

# This will add urls only when DEBUG=True
# cf. https://docs.djangoproject.com/en/1.5/ref/contrib/staticfiles/
#           #django.contrib.staticfiles.urls.staticfiles_urlpatterns
urlpatterns += staticfiles_urlpatterns()
