
DATABASES['default'] = dj_database_url.config(
    default='postgres://oneflow:8jxcWaAfPJT3mV@{0}'
    '/oneflow_dev'.format(MAIN_SERVER))

mongoengine.connect('oneflow_dev', host=MAIN_SERVER)

REDIS_DB = 0

SESSION_REDIS_HOST = MAIN_SERVER
SESSION_REDIS_DB = 2

