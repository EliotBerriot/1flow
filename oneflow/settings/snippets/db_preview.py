
DATABASES['default'] = dj_database_url.config(
    default='postgres://oneflow:8jxcWaAfPJT3mV@{0}'
    '/oneflow_test'.format(MAIN_SERVER))

mongoengine.connect('oneflow_test', host=MAIN_SERVER)

# Redis DB is 10 to avoid clashing with production, which is 0, in case
# both are stored on the same Redis server (which *is*, at project start).
REDIS_DB = 10

SESSION_REDIS_HOST = MAIN_SERVER
SESSION_REDIS_DB = 12
