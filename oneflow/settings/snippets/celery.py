# -*- coding: utf-8 -*-
#
# NOTE: this snippet should come *after* the other celery_*
#       because it uses the BROKER_URL that should have been
#       defined in these.
#

#from datetime import timedelta
import djcelery
djcelery.setup_loader()
from celery.schedules import crontab
from kombu import Exchange, Queue

CELERY_DEFAULT_QUEUE = 'medium'

CELERY_QUEUES = (
    Queue('high', Exchange('high'), routing_key='high'),
    Queue('medium', Exchange('medium'), routing_key='medium'),
    Queue('low', Exchange('low'), routing_key='low'),
    Queue('fetch', Exchange('fetch'), routing_key='fetch'),
    Queue('swarm', Exchange('swarm'), routing_key='swarm'),
)

BROKER_URL = os.environ.get('BROKER_URL')

CELERY_RESULT_BACKEND = BROKER_URL
CELERY_RESULT_PERSISTENT = True

# Allow to recover from any unknown crash.
CELERY_ACKS_LATE = True

# Sometimes, Ask asks us to enable this to debug issues.
#CELERY_DISABLE_RATE_LIMITS=True

# Allow our remote workers to get tasks faster if they have a
# slow internet connection (yes Gurney, I'm thinking of you).
CELERY_MESSAGE_COMPRESSION = 'gzip'

# Avoid long running and retried tasks to be run over-and-over again.
BROKER_TRANSPORT_OPTIONS = {'visibility_timeout': 43200}

# One day is already the default
#CELERY_TASK_RESULT_EXPIRES = 86400

# The default beiing 5000, we need more than this.
CELERY_MAX_CACHED_RESULTS = 32768

# NOTE: I don't know if this is compatible with upstart.
CELERYD_POOL_RESTARTS = True

# I use these to debug kombu crashes; we get a more informative message.
#CELERY_TASK_SERIALIZER = 'json'
#CELERY_RESULT_SERIALIZER = 'json'

#CELERY_ALWAYS_EAGER=True

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
    #
    # •••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••• Core tasks

    'refresh-all-feeds': {
        'task': 'oneflow.core.tasks.refresh_all_feeds',
        'schedule': crontab(hour='*', minute='*/5'),
    },
    'global-feeds-checker': {
        'task': 'oneflow.core.tasks.global_feeds_checker',
        'schedule': crontab(hour='1', minute='1'),
    },

    # •••••••••••••••••••••••••••••••••••••••••••••••••••••••••• Cleaning tasks

    'clean-obsolete-redis-keys': {
        'task': 'oneflow.core.tasks.clean_obsolete_redis_keys',
        'schedule': crontab(hour='2', minute='2'),
    },

    # ••••••••••••••••••••••••••••••••••••••••••••••••••••• Social auth refresh

    'refresh-access-tokens-00': {
        'task': 'oneflow.base.tasks.refresh_access_tokens',
        'schedule': crontab(hour='*/4', minute='0,48'),
    },
    'refresh-access-tokens-12': {
        'task': 'oneflow.base.tasks.refresh_access_tokens',
        'schedule': crontab(hour='3,7,11,15,19,23', minute=12),
    },
    'refresh-access-tokens-24': {
        'task': 'oneflow.base.tasks.refresh_access_tokens',
        'schedule': crontab(hour='2,6,10,14,18,22', minute=24),
    },
    'refresh-access-tokens-36': {
        'task': 'oneflow.base.tasks.refresh_access_tokens',
        'schedule': crontab(hour='1,5,9,13,17,21', minute=36),
    },
}
