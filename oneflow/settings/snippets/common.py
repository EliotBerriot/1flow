# -*- coding: utf-8 -*-
# Django common settings for oneflow project.
# These are overridden in hostname.py specific files.
#
# Here we define the settings for the test platform.
# Production will override only the needed directives.

import os

from django.core.urlresolvers import reverse_lazy

# This is imported here to benefit to all other included snippets.
from sparks import platform # NOQA

try:
    MAIN_SERVER

except NameError:
    raise RuntimeError('MAIN_SERVER setting must be defined '
                       'before common.py inclusion!')

# We need to go down 2 times because the starting point of these settings is
# `project/settings/__init__.py`, instead of good old `project/settings.py`.
# NOTE: the `execfile()` on snippets doesn't add depth: even if the current
# file is `project/settings/snippets/common.py`, this doesn't count.
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
BASE_ROOT    = os.path.dirname(PROJECT_ROOT)

ADMINS   = (('Olivier Cortès', 'oc@1flow.io'), )
MANAGERS = ADMINS

GRAPPELLI_ADMIN_TITLE = '1flow administration'

ALLOWED_HOSTS = []
TIME_ZONE     = 'Europe/Paris'
LANGUAGE_CODE = 'en'

# dummy ugettext function, as django's docs say
ugettext = lambda s: s

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

# FOR NOW, pipeline is disabled because
# compression messes the JS ember tastypie adapter.
PIPELINE_ENABLED = False
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

    'bootstrap': {
        'source_filenames': (
            'vendor/bootstrap/less/bootstrap.less',
        ),
        'output_filename': 'css/bootstrap.css',
    },
    'bootstrap-responsive': {
        'source_filenames': (
            'vendor/bootstrap/less/bootstrap.less',
            'vendor/bootstrap/less/responsive.less',
        ),
        'output_filename': 'css/bootstrap-responsive.css',
    },

    'font-awesome': {
        'source_filenames': (
            'vendor/font-awesome/font-awesome.less',
        ),
        'output_filename': 'css/font-awesome.css',
    },
    'font-awesome-ie7': {
        'source_filenames': (
            'vendor/font-awesome/font-awesome-ie7.less',
        ),
        'output_filename': 'css/font-awesome-ie7.css',
    },

    # ••••••••••••••••••••••••••••••••••••••••••••••••••••••••••• 1flow

    'landing': {
        # This one is not "compiled" but simply copied. We wanted it
        # to be integrated into the pipeline for consistency only.
        'source_filenames': (
            'css/landing-styles.css',
        ),
        'output_filename': 'css/landing.css',
    },

    'core': {
        'source_filenames': (
            'sass/styles.scss',
        ),
        'output_filename': 'css/core.css',
    }
}

PIPELINE_JS = {

    # •••••••••••••••••••••••••••••••••••••••••••••••••••••••••• vendor

    'bootstrap': {
        'source_filenames': (
            # WARNING: order matters: tooltip must be included before popover.
            'vendor/bootstrap/js/bootstrap-[a-o]*.js',
            'vendor/bootstrap/js/bootstrap-t*.js',
            'vendor/bootstrap/js/bootstrap-p*.js',
            'vendor/bootstrap/js/bootstrap-[q-s]*.js',
            'vendor/bootstrap/js/bootstrap-[u-z]*.js',
        ),
        'output_filename': 'js/bootstrap.js',
    },
    'showdown': {
        'source_filenames': (
            'vendor/showdown/showdown.js',
            'vendor/showdown/extensions/twitter.js',
        ),
        'output_filename': 'js/showdown.js',
    },
    'moment': {
        'source_filenames': (
            'vendor/moment/moment.js',
            'vendor/moment/langs/*.js',
        ),
        'output_filename': 'js/moment.js',
    },

    # TODO: to be removed; see core/templates/…/home.html
    'temp_handlebars_rc4': {
        'source_filenames': (
            'js/workarounds/handlebars-1.0.0-rc4/handlebars.js',
        ),
        'output_filename': 'js/handlebars-1.0.0-rc4.js',
    },

    # ••••••••••••••••••••••••••••••••••••••••••••••••••••••••••• 1flow

    'utils': {
        'source_filenames': (
            'js/utils/*.js',
        ),
        'output_filename': 'js/utils.js',
    },

    'core': {
        'source_filenames': (
            'js/core/core.js',
            'js/core/controllers/*.js',
            'js/core/models/*.js',
            'js/core/routes/*.js',
            'js/core/helpers/*.js',
            'js/core/init.js',
        ),
        'output_filename': 'js/core.js',
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
    # TODO: activate this if needed.
    #'social_auth.middleware.SocialAuthExceptionMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'maintenancemode.middleware.MaintenanceModeMiddleware',
    'django.middleware.gzip.GZipMiddleware',
    #'pipeline.middleware.MinifyHTMLMiddleware',
    'django.middleware.cache.FetchFromCacheMiddleware',
)

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
    'django.contrib.messages.context_processors.messages',

    # TODO: activate one of these when needed.
    #'social_auth.context_processors.social_auth_by_name_backends',
    'social_auth.context_processors.social_auth_backends',
    #'social_auth.context_processors.social_auth_login_redirect',

    # One day, if we have some:
    #'oneflow.base.context_processors.…',
    #'oneflow.core.context_processors.…',
)


INSTALLED_APPS = (
    'raven.contrib.django.raven_compat',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    #'grappelli.dashboard',
    'grappelli',
    'django.contrib.admin',
    'django.contrib.admindocs',
    'django_reset',
    'gunicorn',
    'south',
    'south_admin',
    #'maintenancemode', — not needed at all, the middleware is sufficient.
    'transmeta',
    'logentry_admin',
    'constance',
    'tastypie',
    'tastypie_mongoengine',
    'overextends',
    'redis_sessions',
    'redisboard',
    'djcelery',
    'memcache_status',
    'social_auth',
    'markdown_deux',
    'djangojs',
    'pipeline',
    'absolute',
    'ember',
    'widget_tweaks',
    'oneflow.base',
    'oneflow.profiles',
    'oneflow.landing',
    'oneflow.core',
)

JS_CONTEXT_PROCESSOR = 'oneflow.base.utils.JsContextSerializer'

import djcelery
djcelery.setup_loader()
# BROKER and other settings are in celery_* snippets.

MAINTENANCE_MODE = os.path.exists(os.path.join(BASE_ROOT, 'MAINTENANCE_MODE'))

MAINTENANCE_IGNORE_URLS = (
    r'^/admin/.*',
)

MARKDOWN_DEUX_STYLES = {
    'default': {
        'extras': {
            'code-friendly': None,
            'cuddled-lists': None,

        },
        'safe_mode': 'escape',
    },
    'raw': {
        'extras': {
            'code-friendly': None,
            'cuddled-lists': None,

        },
        'safe_mode': False,
    }
}

CONSTANCE_BACKEND = 'constance.backends.redisd.RedisBackend'
# CONSTANCE_REDIS_CONNECTION is to be found in db_*
CONSTANCE_REDIS_PREFIX = 'c0s1f:'
CONSTANCE_CONFIG = {
    'GR_MAX_ARTICLES': (25 if DEBUG else 250000, ugettext(u'maximum number '
                        u'of Google Reader articles imported for a user.')),
    'GR_MAX_FEEDS': (2 if DEBUG else 1000, ugettext(u'maximum number of '
                     u'articles imported from Google Reader for any user.')),
    'GR_LOAD_LIMIT': (500, ugettext(u'maximum number of articles '
                      u'in each wave of Google Reader feed import.')),
    'GR_WAVE_LIMIT': (25, ugettext(u'maximum number of import waves for each '
                      u'Google Reader feed.')),
}
# Defaults to ['json', 'xml', 'yaml', 'html', 'plist']
TASTYPIE_DEFAULT_FORMATS = ('json', )

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
    'social_auth.backends.contrib.linkedin.LinkedinBackend',
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

# See http://django-social-auth.readthedocs.org/en/latest/configuration.html#urls-options # NOQA
# for social_auth specific URLs.
LOGIN_URL          = reverse_lazy('signin')
LOGOUT_URL         = reverse_lazy('signout')
LOGIN_REDIRECT_URL = reverse_lazy('home')
LOGIN_ERROR_URL    = reverse_lazy('signin_error')

# See SOCIAL_AUTH_USER_MODEL earlier in this file.
#SOCIAL_AUTH_SANITIZE_REDIRECTS = False
#SOCIAL_AUTH_PROTECTED_USER_FIELDS = ['email',]
SOCIAL_AUTH_EXTRA_DATA = True
SOCIAL_AUTH_SESSION_EXPIRATION = False

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
        # Warning messages are sent to admin emails
        'mail_admins': {
            'level': 'WARNING',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler',
            'include_html': True,
        },
        # critical errors are logged to sentry
        'sentry': {
            'level': 'ERROR',
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
