
DATABASES['default'] = dj_database_url.config(
    default='postgres://oneflow:8jxcWaAfPJT3mV@{0}'
    '/oneflow'.format(MAIN_SERVER))

mongoengine.connect('oneflow', host=MAIN_SERVER)

REDIS_DB = 0

CONSTANCE_REDIS_CONNECTION = 'redis://{0}:6379/{1}'.format(
    MAIN_SERVER, REDIS_DB)

SESSION_REDIS_HOST = MAIN_SERVER
SESSION_REDIS_DB = 2
