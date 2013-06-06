BROKER_URL = 'redis://{0}:6379/1'.format(MAIN_SERVER)
CELERY_RESULT_BACKEND = BROKER_URL

# I use these to debug kombu crashes; we get a more informative message.
#CELERY_TASK_SERIALIZER = 'json'
#CELERY_RESULT_SERIALIZER = 'json'
