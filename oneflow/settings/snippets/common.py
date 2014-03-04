# -*- coding: utf-8 -*-
#
# Django common settings for oneflow project.
# These are overridden in hostname.py specific files.
#
# Here we define the settings for the test platform.
# Production will override only the needed directives.
#
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

import os
import sys
import warnings


from django.core.urlresolvers import reverse_lazy
from django.utils.translation import ugettext_lazy

# dummy ugettext function, as django's docs say
ugettext = lambda s: s

# This is imported here to benefit to all other included snippets.
from sparks import platform # NOQA

# We need to go down 2 times because the starting point of these settings is
# `project/settings/__init__.py`, instead of good old `project/settings.py`.
# NOTE: the `execfile()` on snippets doesn't add depth: even if the current
# file is `project/settings/snippets/common.py`, this doesn't count.
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
BASE_ROOT    = os.path.dirname(PROJECT_ROOT)

# This one is hardcoded for all admin links, to avoid the need to
# replace it everywhere when mongoadmin wants to change things…
NONREL_ADMIN = u'/admin/nonrel/'

ADMINS   = (('Olivier Cortès', 'oc@1flow.io'), )
MANAGERS = ADMINS

from oneflow import VERSION

GRAPPELLI_ADMIN_TITLE = u'1flow v%s administration%s' % (VERSION, u' — DEVEL'
                                                         if DEBUG else u'')
MONGOADMIN_OVERRIDE_ADMIN = True

ALLOWED_HOSTS = []
TIME_ZONE     = 'Europe/Paris'
LANGUAGE_CODE = 'en'

# Translation workflows:
# - in the DB: all languages variants are accessible and empty by default.
#      'en' takes precedence on 'en-US'. As translators have access to all
#       translations, this is a bit awkward, but we don't have the choice
#       because we must match the Django application languages. We could
#       manually hide the 'en-us' to avoid confusion, but this would imply
#       dirty hacking in all admin modules and I don't find it worth.
# - in the webapp: 'en' is *always* defined because the developers create
#       english strings. For translators to be able to override them
#       without needing commit access, we use the 'en-us' language, which
#       takes precedence. This is not perfect, because other 'en-*'
#       users will get the 'bare' strings which can have errors, but at
#       least our translators have access to en-US strings the same way
#       they access other languages.
LANGUAGES = (
    ('en', ugettext(u'English')),
    # We're not ready to handle a british translation (no resource…)
    #('en-gb', ugettext(u'English (UK)')),
    ('fr', ugettext(u'Français')),

    # Activate these later when we need them.
    #    ('es', ugettext(u'Español')),
    #    ('fr-CA', ugettext(u'Français (FR)')),
    #    ('es-XX', ugettext(u'Español (ES)')),
)

TRANSMETA_LANGUAGES = LANGUAGES + (
    # The 'nt' fake language is used by translators to keep
    # variants and translations notes handy in the admin interface.
    ('nt', ugettext(u'Notes — variants')),
)

# We use oneflow.base.models.User as a drop-in replacement.
AUTH_USER_MODEL = 'base.User'
SOCIAL_AUTH_USER_MODEL = 'base.User'

USE_I18N = True
USE_L10N = True
USE_TZ   = True

# Activate if bandwidth is limited, at some CPU cost.
#USE_ETAGS = True

MEDIA_ROOT = os.path.join(BASE_ROOT, 'media')
MEDIA_URL  = '/media/'

STATIC_ROOT = os.path.join(BASE_ROOT, 'static')
STATIC_URL  = '/static/'

SECRET_KEY = '1!ps20!7iya1ptgluj@2u50)r!fvl*%+6qbxar2jn9y$@=eme!'

ROOT_URLCONF = 'oneflow.urls'

WSGI_APPLICATION = 'oneflow.wsgi.application'

STATICFILES_DIRS = (
)

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

STATICFILES_STORAGE = 'pipeline.storage.PipelineCachedStorage'

#PIPELINE_ENABLED = False

# Until our own modules are ready to be wrapped, don't use this.
PIPELINE_DISABLE_WRAPPER = True

PIPELINE_COMPILERS = (
    'pipeline.compilers.less.LessCompiler',
    # We don't use the from django-pipeline-compass compiler,
    # it breaks bootstrap-responsive.
    #       'pipeline_compass.compiler.CompassCompiler',
    #
    # Intead, we use the one from django-pipeline-compass-rubygem, which
    # runs the official 'compass' Ruby binary in a subshell.
    #
    # WARNING, though: both packages install at the same location.
    # As of 20130524, django-pipeline-compass-rubygem is itself broken,
    # because it doesn't ship the __init__.py. Thus it doesn't work alone;
    # but it doesn't depend on django-pipeline-compass, which makes the
    # whole process heavily error-prone because we need to install both,
    # but it's not issued anywhere.
    #
    # Finally, after installing 2 python packages and Ruby + the rubygem,
    # everything works as expected. I personally prefer using the official
    # 'compass' and have a working CSS, than an un-maintained python erzatz
    # which doesnt work and breaks CSSs without any error displayed.
    'pipeline_compass.compass.CompassCompiler',
    'pipeline.compilers.coffee.CoffeeScriptCompiler',
)

PIPELINE_CSS = {

    # •••••••••••••••••••••••••••••••••••••••••••••••••••••••••• vendor

    # TODO: the 'vendor-all' target.

    # ——————————————————————————————————————————————————————————————— Bootstrap

    'bootstrap': {
        'source_filenames': (
            'vendor/bootstrap/3.0.3/less/bootstrap.less',
        ),
        'output_filename': 'css/bootstrap.css',
    },

    'bootstrap-2': {
        'source_filenames': (
            'vendor/bootstrap/2.3.2/less/bootstrap.less',
        ),
        'output_filename': 'css/bootstrap-2.css',
    },

    'bootstrap-2-responsive': {
        'source_filenames': (
            'vendor/bootstrap/2.3.2/less/bootstrap.less',
            'vendor/bootstrap/2.3.2/less/responsive.less',
        ),
        'output_filename': 'css/bootstrap-2-responsive.css',
    },

    # ———————————————————————————————————————————————————————————— Font-awesome

    'font-awesome': {
        'source_filenames': (
            'vendor/font-awesome/less/font-awesome.less',
        ),
        'output_filename': 'css/font-awesome.css',
    },
    'font-awesome-ie7': {
        'source_filenames': (
            'vendor/font-awesome/less/font-awesome-ie7.less',
        ),
        'output_filename': 'css/font-awesome-ie7.css',
    },

    # —————————————————————————————————————————————————————————————— 1flow core
    # The core uses Bootstrap 3. Either Detail-Admin donated by Erick Alvarez,
    # or any bootswatch theme: just change the value in the constance config.

    'core-bootswatch': {
        'source_filenames': (
            'sass/styles-core-bootswatch.scss',
        ),

        'output_filename': 'css/core-bootswatch.css',
    },

    'core-detail-admin': {
        'source_filenames': (
            'sass/styles-core-detail-admin.scss',
        ),
        'output_filename': 'css/core-detail-admin.css',
    },

    # —————————————————————————————————————————————————————— 1flow landing page
    # As of 201401xx, the landing page is still Bootstrap 2.

    'core-bootstrap-bare': {
        'source_filenames': (
            'sass/styles-core-bootstrap-bare.scss',
        ),
        'output_filename': 'css/core-bootstrap-bare.css',
    }
}

PIPELINE_JS = {

    # •••••••••••••••••••••••••••••••••••••••••••••••••••••••••• vendor

    'vendor-global': {
        # This one includes all external dependancies
        # (eg. non 1flow sources) for a one-file-only dep.
        'source_filenames': (
            'vendor/raven.js/1.0.8/raven.js',
            'vendor/underscorejs/1.5.1/underscore.js',
            'vendor/mousetrap/1.4.2/mousetrap.js',
            'vendor/hammerjs/1.0.5/hammer.js',
            'vendor/pnotify/1.2/jquery.pnotify.js',
            'vendor/jquery-easing/1.3/jquery.easing.js',
            'vendor/jquery-color/2.1.2/jquery.color.js',

            # WARNING: order matters: tooltip must be included before popover.
            # This order is a copy-n-paste of Bootstrap 3.0.3's Gruntfile.js.
            'vendor/bootstrap/3.0.3/js/transition.js',
            'vendor/bootstrap/3.0.3/js/alert.js',
            'vendor/bootstrap/3.0.3/js/button.js',
            'vendor/bootstrap/3.0.3/js/carousel.js',
            'vendor/bootstrap/3.0.3/js/collapse.js',
            'vendor/bootstrap/3.0.3/js/dropdown.js',
            'vendor/bootstrap/3.0.3/js/modal.js',
            'vendor/bootstrap/3.0.3/js/tooltip.js',
            'vendor/bootstrap/3.0.3/js/popover.js',
            'vendor/bootstrap/3.0.3/js/scrollspy.js',
            'vendor/bootstrap/3.0.3/js/tab.js',
            'vendor/bootstrap/3.0.3/js/affix.js',
        ),

        'output_filename': 'js/min/vendor-global.js',
    },
    #
    # TODO: find CDNs versions of these, and merge
    # the 2 vendor-* target for simplification.
    #
    'vendor-local': {
        'source_filenames': (

            'vendor/showdown/showdown.js',
            'vendor/showdown/extensions/twitter.js',

            'vendor/moment/moment.js',
            'vendor/moment/langs/*.js',

            'vendor/other/*.js',

            # NOTE: we use or own implementation
            # of django-endless-pagination JS.
        ),
        'output_filename': 'js/min/vendor-local.js',
    },

    # NOTE: we use or own implementation
    # of django-endless-pagination JS.
    'vendor-endless-pagination': {
        'source_filenames': (
            'endless_pagination/js/endless-pagination.js',
        ),
        'output_filename': 'js/min/endless-pagination.js',
    },

    # ••••••••••••••••••••••••••••••••••••••••••••••••••••••••••• 1flow

    'utils': {
        'source_filenames': (
            'js/utils/*.js',
            'js/common.js',
        ),
        'output_filename': 'js/min/utils.js',
    },

    'feed-selector': {
        'source_filenames': (
            'js/utils/*.js',
            'js/common.js',
            'js/feed-selector.js',
        ),
        'output_filename': 'js/min/feed-selector.js',
    },

    'read-endless': {
        'source_filenames': (
            'js/utils/*.js',
            'js/common.js',
            'js/read-one.js',
            'js/read-endless.js',
        ),
        'output_filename': 'js/min/read-endless.js',
    },

    'read-one': {
        'source_filenames': (
            'js/utils/*.js',
            'js/common.js',
            'js/read-one.js',
        ),
        'output_filename': 'js/min/read-one.js',
    },

    'core': {
        'source_filenames': (
            'js/utils/*.js',
            'js/common.js',
            'js/core-init.js',
        ),
        'output_filename': 'js/min/core.js',
    },

    'ember-core': {
        'source_filenames': (
            'js/ember-core/core.js',
            'js/ember-core/controllers/*.js',
            'js/ember-core/models/*.js',
            'js/ember-core/views/*.js',
            'js/ember-core/routes/*.js',
            'js/ember-core/helpers/*.js',
            'js/ember-core/end.js',
        ),
        'output_filename': 'js/min/ember-core.js',
    }
}

if TEMPLATE_DEBUG:
    # Because Django's cached templates doesn't use a proper caching
    # engine, it doesn't benefit from our DummyCache development setting…
    # We have to deactivate it completely for development.
    # cf. http://stackoverflow.com/a/4071488/654755
    TEMPLATE_LOADERS = (
        'django.template.loaders.filesystem.Loader',
        'django.template.loaders.app_directories.Loader',
    )

else:
    TEMPLATE_LOADERS = (
        ('django.template.loaders.cached.Loader', (
            'django.template.loaders.filesystem.Loader',
            'django.template.loaders.app_directories.Loader',
        )),
    )

# We always include the *Cache* middlewares. In development &
# pre-production it's a dummy cache, allowing to keep them here.
MIDDLEWARE_CLASSES = (
    #'ConditionalGetMiddleware',
    ('raven.contrib.django.raven_compat.middleware.'
        'SentryResponseErrorIdMiddleware'),
    'raven.contrib.django.raven_compat.middleware.Sentry404CatchMiddleware',
    'django.middleware.cache.UpdateCacheMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    # TODO: test and activate this.
    #'django.middleware.transaction.TransactionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',

    # account's MW must come after 'auth', else they crash.
    #
    # BTW, account's LocaleMiddleware produces a strange bug
    # where /en/ doesn't exist anymore and we have two /fr/
    # entries, making / fail to load. The logout process
    # behave badly because of that. BTW again, I didn't see
    # what it brought / added to the current implementation,
    # leaving it disabled changes nothing.
    #'account.middleware.LocaleMiddleware',
    'account.middleware.TimezoneMiddleware',

    # TODO: activate this if needed.
    #'social_auth.middleware.SocialAuthExceptionMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'maintenancemode.middleware.MaintenanceModeMiddleware',
    'django.middleware.gzip.GZipMiddleware',
    'django.middleware.cache.FetchFromCacheMiddleware',
)

if not DEBUG:
    MIDDLEWARE_CLASSES = MIDDLEWARE_CLASSES[:-1] + (
        'pipeline.middleware.MinifyHTMLMiddleware',
    ) + MIDDLEWARE_CLASSES[-1:]

#SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"
SESSION_ENGINE = 'redis_sessions.session'

TEMPLATE_DIRS = (
    os.path.join(PROJECT_ROOT, 'templates')
)

# cf. https://docs.djangoproject.com/en/1.5/ref/settings/#template-context-processors # NOQA
TEMPLATE_CONTEXT_PROCESSORS = (
    # NOTE: ….debug is added only if DEBUG=True, later in another snippet.
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.static',
    'django.core.context_processors.tz',
    'django.core.context_processors.request',
    'absolute.context_processors.absolute',
    'constance.context_processors.config',
    'django.contrib.auth.context_processors.auth',
    'account.context_processors.account',
    'django.contrib.messages.context_processors.messages',

    # Only one of them is needed.
    #'social_auth.context_processors.social_auth_by_name_backends',
    'social_auth.context_processors.social_auth_backends',
    #'social_auth.context_processors.social_auth_login_redirect',

    # `base` processors
    'oneflow.base.context_processors.oneflow_version',
    'oneflow.base.context_processors.django_settings',
    'oneflow.base.context_processors.maintenance_mode',

    # `core` processors
    'oneflow.core.context_processors.mongodb_user',
    'oneflow.core.context_processors.social_things',
)

# NOTE: INSTALLED_APPS is a list (not a tuple)
# in 1flow, because of the conditional landing.
INSTALLED_APPS = [
    'raven.contrib.django.raven_compat',
    'django.contrib.auth',
    'account',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    #'django.contrib.sites',

    # We could use Django's `humanize`, it produces more
    # detailled `*delta()` than the external `humanize` module.
    #'django.contrib.humanize',

    'django.contrib.messages',
    'django.contrib.staticfiles',
    #'grappelli.dashboard',
    'grappelli',
    'mongoadmin',
    'django.contrib.admin',
    #'django.contrib.admindocs',
    'django_reset',
    'django_shell_ipynb',
    'gunicorn',
    'south',
    'south_admin',
    #'maintenancemode', — not needed at all, the middleware is sufficient.
    'transmeta',

    # Order matters for inplace & friends.
    'inplaceeditform_bootstrap',
    'inplaceeditform',
    #'inplaceeditform_extra_fields',
    #'bootstrap3_datetime',

    'logentry_admin',
    'constance',
    'tastypie',
    'tastypie_mongoengine',
    'overextends',
    'redis_sessions',
    #'django_markdown',
    'writingfield',
    #'redisboard',
    'djcelery',
    'memcache_status',
    'markdown_deux',
    'djangojs',
    'django_select2',
    'pipeline',
    'absolute',
    'endless_pagination',

    # `infinite_pagination` doesn't work on MongoEngine QuerySet.
    #'infinite_pagination',

    # We don't use `mathfilters` as of 20130831.
    #'mathfilters',

    'widget_tweaks',
    'oneflow.base',
    'oneflow.profiles',
    'oneflow.core',
    # OMG: order matters! as DSA depends on user model,
    # it must come after 'oneflow.base' wich contains it.
    # Without this, tests fail to create database!
    'social_auth',
]

# ———————————————————————————————————————————————————————— django-user-accounts

ACCOUNT_EMAIL_UNIQUE = True
ACCOUNT_EMAIL_CONFIRMATION_REQUIRED = True
# ACCOUNT_LOGIN_REDIRECT_URL =
ACCOUNT_LOGOUT_REDIRECT_URL = u'signin'
ACCOUNT_EMAIL_CONFIRMATION_ANONYMOUS_REDIRECT_URL = u'signin'
ACCOUNT_EMAIL_CONFIRMATION_AUTHENTICATED_REDIRECT_URL = u'home'
ACCOUNT_PASSWORD_CHANGE_REDIRECT_URL = u'profile'
ACCOUNT_PASSWORD_RESET_REDIRECT_URL = u'signin'

# —————————————————————————————————————————————————————————— django-inplaceedit

INPLACEEDIT_EDIT_EMPTY_VALUE = ugettext_lazy(u'Click to edit')
INPLACEEDIT_AUTO_SAVE = True
INPLACEEDIT_EVENT = "click"
#INPLACEEDIT_DISABLE_CLICK = True  # For inplace edit text into a link tag
#INPLACEEDIT_EDIT_MESSAGE_TRANSLATION = 'Write a translation' # transmeta option
INPLACEEDIT_SUCCESS_TEXT = ugettext_lazy(u'Successfully saved')
INPLACEEDIT_UNSAVED_TEXT = ugettext_lazy(u'You have unsaved changes')
#INPLACE_ENABLE_CLASS = 'form-control'
DEFAULT_INPLACE_EDIT_OPTIONS = {
    'auto_height': 1,            # be gentle, don't try to guess anything.
    'class_inplace': 'form',     # Be a little bootstrap compatible.
    'tag_name_cover': 'div',     # Make the editables more clickable.
    '__widget_class': 'form-control',   # DOES NOT WORK, ISSUE Github #53
}
# modify the behavior of the DEFAULT_INPLACE_EDIT_OPTIONS usage, if True
# then it use the default values not specified in your template, if False
# it uses these options only when the dictionnary is empty (when you do put
            # any options in your template)
#DEFAULT_INPLACE_EDIT_OPTIONS_ONE_BY_ONE = True
ADAPTOR_INPLACEEDIT_EDIT = 'oneflow.base.models.OwnerOrSuperuserEditAdaptor'
ADAPTOR_INPLACEEDIT = {
    #example: 'tiny': 'inplaceeditform_extra_fields.fields.AdaptorTinyMCEField'
    #'date': 'inplaceeditform_bootstrap.fields.AdaptorDateBootStrapField',
    #'datetime': 'inplaceeditform_bootstrap.fields.AdaptorDateTimeBootStrapField',
}
#INPLACE_GET_FIELD_URL = None # to change the url where django-inplaceedit use to get a field
#INPLACE_SAVE_URL = None # to change the url where django-inplaceedit use to save a field

# A django-inplaceedit-bootstrap setting.
INPLACEEDIT_EDIT_TOOLTIP_TEXT = ugettext_lazy(u'Click to edit')

# ———————————————————————————————————————————————————— django-endlesspagination

ENDLESS_PAGINATION_PER_PAGE = 100

# This is done directly in the templates.
#ENDLESS_PAGINATION_LOADING  = ugettext_lazy(u'loading more entries…')

# —————————————————————————————————————————————————————————————— django-select2

AUTO_RENDER_SELECT2_STATICS = False
GENERATE_RANDOM_SELECT2_ID = True
ENABLE_SELECT2_MULTI_PROCESS_SUPPORT = True
# See cache.py for Select2 memcache settings.

# ———————————————————————————————————————————————————— Other

JS_CONTEXT_PROCESSOR = 'oneflow.base.utils.JsContextSerializer'

RAVEN_CONFIG = {
    # We send flower bugs to a dedicated sentry project,
    # it pollutes us too much.
    'dsn': os.environ.get('RAVEN_DSN_FLOWER'
                          if 'flower' in sys.argv or 'shell_ipynb' in sys.argv
                          else 'RAVEN_DSN'),
}

STATSD_HOST   = os.environ.get('STATSD_HOST')
STATSD_PORT   = int(os.environ.get('STATSD_PORT', 8125))
STATSD_PREFIX = os.environ.get('STATSD_PREFIX', '1flow')

MAINTENANCE_MODE = os.path.exists(os.path.join(BASE_ROOT, 'MAINTENANCE_MODE'))

MAINTENANCE_IGNORE_URLS = (
    r'^/admin/.*',
)

MARKDOWN_DEUX_STYLES = {
    'default': {
        'extras': {
            # html2text uses _ by default for EM…
            #'code-friendly': None,
            'cuddled-lists': None,

        },
        'safe_mode': 'escape',
    },
    'code': {
        'extras': {
            'code-friendly': None,
            'cuddled-lists': None,

        },
        'safe_mode': 'escape',
    },
    'raw': {
        'extras': {
            # html2text uses _ by default for EM…
            #'code-friendly': None,
            'cuddled-lists': None,

        },
        'safe_mode': False,
    },
    'code-raw': {
        'extras': {
            'code-friendly': None,
            'cuddled-lists': None,

        },
        'safe_mode': False,
    }
}

# CONSTANCE_* is to be found in 'snippets/constance*'

# Defaults to ['json', 'xml', 'yaml', 'html', 'plist']
TASTYPIE_DEFAULT_FORMATS = ('json', )
API_LIMIT_PER_PAGE = 10


AUTHENTICATION_BACKENDS = (
    # WARNING: when activating Twitter, we MUST implement the email pipeline,
    # else the social-only registration will fail because user has no mail.
    #'social_auth.backends.twitter.TwitterBackend',
    #'social_auth.backends.facebook.FacebookBackend',
    #'social_auth.backends.google.GoogleOAuthBackend',
    'social_auth.backends.google.GoogleOAuth2Backend',
    #'social_auth.backends.google.GoogleBackend',
    #'social_auth.backends.yahoo.YahooBackend',
    #'social_auth.backends.browserid.BrowserIDBackend',
    #'social_auth.backends.contrib.linkedin.LinkedinBackend',
    #'social_auth.backends.contrib.disqus.DisqusBackend',
    #'social_auth.backends.contrib.livejournal.LiveJournalBackend',
    #'social_auth.backends.contrib.orkut.OrkutBackend',
    #'social_auth.backends.contrib.foursquare.FoursquareBackend',
    #'social_auth.backends.contrib.github.GithubBackend',
    #'social_auth.backends.contrib.vk.VKOAuth2Backend',
    #'social_auth.backends.contrib.live.LiveBackend',
    #'social_auth.backends.contrib.skyrock.SkyrockBackend',
    #'social_auth.backends.contrib.yahoo.YahooOAuthBackend',
    #'social_auth.backends.contrib.readability.ReadabilityBackend',
    #'social_auth.backends.contrib.fedora.FedoraBackend',
    #'social_auth.backends.OpenIDBackend',
    'django.contrib.auth.backends.ModelBackend',
)

# ••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••• Social Auth
# See snippets/api_keys_*.py for API keys.


from libgreader.auth import OAuth2Method

# Get the google reader scope.
GOOGLE_OAUTH_EXTRA_SCOPE           = OAuth2Method.SCOPE
# We need this to be able to refresh tokens
# See http://stackoverflow.com/a/10857806/654755 for notes.
GOOGLE_OAUTH2_AUTH_EXTRA_ARGUMENTS = {'access_type': 'offline'}

GOOGLE_OAUTH2_CONTACTS_SCOPE = 'https://www.google.com/m8/feeds'
GOOGLE_OAUTH2_CONTACTS_REDIRECT_URI = reverse_lazy('import_contacts_authorized')

# See http://django-social-auth.readthedocs.org/en/latest/configuration.html#urls-options # NOQA
# for social_auth specific URLs.
LOGIN_URL          = reverse_lazy('signin')
LOGOUT_URL         = reverse_lazy('signout')
LOGIN_REDIRECT_URL = reverse_lazy('home')
LOGIN_ERROR_URL    = reverse_lazy('signin_error')
#SOCIAL_AUTH_BACKEND_ERROR_URL = reverse_lazy('signin_error')

# See SOCIAL_AUTH_USER_MODEL earlier in this file.
#SOCIAL_AUTH_SANITIZE_REDIRECTS = False
#SOCIAL_AUTH_PROTECTED_USER_FIELDS = ['email',]
SOCIAL_AUTH_EXTRA_DATA = True
SOCIAL_AUTH_SESSION_EXPIRATION = False
# SOCIAL_AUTH_RAISE_EXCEPTIONS = True

SOCIAL_AUTH_PIPELINE = (
    'social_auth.backends.pipeline.social.social_auth_user',
    #
    # WARNING: `associate_by_email` is safe unless we use backends which
    #       don't check email validity. We will have to implement email
    #       hash_code checking when we activate our own account system.
    #
    'social_auth.backends.pipeline.associate.associate_by_email',
    'social_auth.backends.pipeline.user.get_username',
    'social_auth.backends.pipeline.user.create_user',
    'social_auth.backends.pipeline.social.associate_user',
    'social_auth.backends.pipeline.social.load_extra_data',
    'social_auth.backends.pipeline.user.update_user_details',

    #'oneflow.core.social_pipeline.check_1flow_requirements',
    'oneflow.core.social_pipeline.get_social_avatar',

    # Given the current configuration, we do allow any user to register,
    # or not. In both cases, we create the account, but will deactivate
    # it if registration is disabled.
    'oneflow.core.social_pipeline.throttle_new_user_accounts',
)

# —————————————————————————————————————————————————————————————— 1flow settings


DEFAULT_USER_AGENT = u'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.8; rv:21.0) Gecko/20100101 Firefox/21.0' # NOQA


# ••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••• Logging

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'formatters': {
        'verbose': {
            'format': '[contactor] %(levelname)s %(asctime)s %(message)s'
        },
    },
    'handlers': {
        # Send all messages to console
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
        },
        # Send info messages to syslog
        # 'syslog':{
        #     'level':'INFO',
        #     'class': 'logging.handlers.SysLogHandler',
        #     'facility': SysLogHandler.LOG_LOCAL2,
        #     'address': '/dev/log',
        #     'formatter': 'verbose',
        # },
        # ERROR messages are sent to admin emails
        'mail_admins': {
            # We don't want any mail for every warning on earth.
            #'level': 'WARNING',
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler',
            'include_html': True,
        },
        # WARNINGs and critical errors are logged to sentry
        'sentry': {
            'level': 'WARNING',
            #'filters': ['require_debug_false'],
            'class': 'raven.contrib.django.handlers.SentryHandler',
        },
    },
    'loggers': {
        # Don't log SQL queries, this bothers me.
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'INFO',
        },

        # This is the "catch all" logger
        '': {
            'handlers': ['console', 'mail_admins', 'sentry'],  # 'syslog',
            'level': 'DEBUG',
            'propagate': False,
        },
    }
}
