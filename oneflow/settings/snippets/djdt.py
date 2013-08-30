# Debug-toolbar related

INSTALLED_APPS += (
    'debug_toolbar',
    #'debug_toolbar_user_panel',
    #'template_timings_panel',
    #'debug_toolbar_mongo',
)

MIDDLEWARE_CLASSES += ('debug_toolbar.middleware.DebugToolbarMiddleware', )

INTERNAL_IPS = (
    '127.0.0.1',
    # gurney.licorn.org
    '109.190.93.141',
    # my LAN
    '192.168.111.23',
    '192.168.111.111',
)

# If it becomes too slow, activate this.
#DEBUG_TOOLBAR_MONGO_STACKTRACES = False

DEBUG_TOOLBAR_PANELS = (
    'debug_toolbar.panels.request_vars.RequestVarsDebugPanel',
    'debug_toolbar.panels.headers.HeaderDebugPanel',
    'debug_toolbar.panels.template.TemplateDebugPanel',
    #'template_timings_panel.panels.TemplateTimings.TemplateTimings',
    #'debug_toolbar_mongo.panel.MongoDebugPanel',
    'debug_toolbar.panels.sql.SQLDebugPanel',
    #'debug_toolbar.panels.timer.TimerDebugPanel',
    #'debug_toolbar.panels.logger.LoggingPanel',
    #'debug_toolbar_user_panel.panels.UserPanel',
    #'debug_toolbar.panels.signals.SignalDebugPanel',
    'debug_toolbar.panels.settings_vars.SettingsVarsDebugPanel',
    'debug_toolbar.panels.version.VersionDebugPanel',
)

DEBUG_TOOLBAR_CONFIG = {
    'INTERCEPT_REDIRECTS': False,
    'ENABLE_STACKTRACES' : False,
    #'SHOW_TOOLBAR_CALLBACK': custom_show_toolbar,
    #'EXTRA_SIGNALS': ['myproject.signals.MySignal'],
    #'HIDE_DJANGO_SQL': False,
    #'TAG': 'div',
}
