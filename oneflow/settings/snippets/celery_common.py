#
# NOTE: this snippet should come *after* the other celery_*
#       because it uses the BROKER_URL that should have been
#       defined in these.
#

#from datetime import timedelta
from celery.schedules import crontab

CELERY_RESULT_BACKEND = BROKER_URL
CELERY_RESULT_PERSISTENT = True

# Allow our remote workers to get tasks faster if they have a
# slow internet connection (yes Gurney, I'm thinking of you).
CELERY_MESSAGE_COMPRESSION = 'gzip'

# One day is already the default
#CELERY_TASK_RESULT_EXPIRES = 86400

# The current default:
#CELERY_MAX_CACHED_RESULTS = 5000

# I use these to debug kombu crashes; we get a more informative message.
#CELERY_TASK_SERIALIZER = 'json'
#CELERY_RESULT_SERIALIZER = 'json'

CELERY_TRACK_STARTED = True
CELERY_SEND_TASK_SENT_EVENT = True

# Disabled by default and I like it, because we use Sentry for this.
#CELERY_SEND_TASK_ERROR_EMAILS = False

CELERYBEAT_SCHEDULER = 'djcelery.schedulers.DatabaseScheduler'

CELERYBEAT_SCHEDULE = {
    # 'celery-beat-test': {
    #     'task': 'oneflow.base.tasks.celery_beat_test',
    #     'schedule': timedelta(seconds=15),
    #     'schedule': timedelta(seconds=5),
    #     'schedule': crontab(minute='*'),
    # },
    'refresh-access-tokens-00': {
        'task': 'oneflow.base.tasks.refresh_access_tokens',
        'schedule': crontab(hour='*/4', minute='0,48'),
    },
    'refresh-access-tokens-12': {
        'task': 'oneflow.base.tasks.refresh_access_tokens',
        'schedule': crontab(hour='3,7,11,19,23', minute=12),
    },
    'refresh-access-tokens-24': {
        'task': 'oneflow.base.tasks.refresh_access_tokens',
        'schedule': crontab(hour='2,6,8,14,18,22', minute=24),
    },
    'refresh-access-tokens-36': {
        'task': 'oneflow.base.tasks.refresh_access_tokens',
        'schedule': crontab(hour='1,5,9,13,17,21', minute=36),
    },
    'clean-obsolete-redis-keys': {
        'task': 'oneflow.core.tasks.clean_obsolete_redis_keys',
        'schedule': crontab(hour='2', minute='2'),
    },
}
