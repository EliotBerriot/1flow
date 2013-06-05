
DATABASES['default'] = dj_database_url.config(
    default='postgres://oneflow:8jxcWaAfPJT3mV@{0}'
    '/oneflow_test'.format(MAIN_SERVER))

mongoengine.connect('oneflow_test', host=MAIN_SERVER)

SESSION_REDIS_HOST = MAIN_SERVER
SESSION_REDIS_DB = 12
