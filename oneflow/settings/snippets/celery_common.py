#
# NOTE: this snippet should come *after* the other celery_*
#       because it uses the BROKER_URL that should have been
#       defined in these.
#

CELERY_RESULT_BACKEND = BROKER_URL

# I use these to debug kombu crashes; we get a more informative message.
#CELERY_TASK_SERIALIZER = 'json'
#CELERY_RESULT_SERIALIZER = 'json'

CELERY_SEND_TASK_SENT_EVENT = True
