# -*- coding: utf-8 -*-
#
# NOTE: this snippet should come *after* the other celery_*
#       because it uses the BROKER_URL that should have been
#       defined in these.
#
"""
    Copyright 2013 Olivier Cortès <oc@1flow.io>

    This file is part of the 1flow project.

    1flow is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of
    the License, or (at your option) any later version.

    1flow is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public
    License along with 1flow.  If not, see http://www.gnu.org/licenses/

"""

#from datetime import timedelta
import djcelery
djcelery.setup_loader()
from celery.schedules import crontab
from kombu import Exchange, Queue

# Avoid sharing the same celery states file
# when multiple workers run on the same machine.
try:
    index = sys.argv.index('--hostname')
except:
    CELERYD_STATE_DB = 'celery.states'
else:
    # get 'medium' from 'medium.worker-03.1flow.io'
    CELERYD_STATE_DB = 'celery.states.{0}'.format(
                            sys.argv[index + 1].split('.', 1)[0])
    del index

# 2014-03-09: I benchmarked with 0/1/2 on a 15K-items queue, with various
# other parameters (mtpc=0/1/4/16/64, crc=16/32/64) and having no prefetching
# is the option that gives the best continuous throughput, with excellent
# peaks. All other options make the process-group master stop children to
# ack and re-prefetch next jobs, which in turn make all other process groups
# wait. This produce a lot of hickups in the global processing tunnel. Thus, 0.
CELERYD_PREFETCH_MULTIPLIER = 0

CELERY_DEFAULT_QUEUE = 'medium'

CELERY_QUEUES = (
    Queue('high', Exchange('high'), routing_key='high'),
    Queue('medium', Exchange('medium'), routing_key='medium'),
    Queue('low', Exchange('low'), routing_key='low'),
    Queue('fetch', Exchange('fetch'), routing_key='fetch'),
    Queue('swarm', Exchange('swarm'), routing_key='swarm'),
    Queue('clean', Exchange('clean'), routing_key='clean'),
    Queue('background', Exchange('background'), routing_key='background'),
)

BROKER_URL = os.environ.get('BROKER_URL')

# Disabling the heartbeat because workers seems often disabled in flower,
# thanks to http://stackoverflow.com/a/14831904/654755
BROKER_HEARTBEAT = 0

CELERY_RESULT_BACKEND = BROKER_URL
CELERY_RESULT_PERSISTENT = True

# Allow to recover from any unknown crash.
CELERY_ACKS_LATE = True

# Sometimes, Ask asks us to enable this to debug issues.
# BTW, it will save some CPU cycles.
CELERY_DISABLE_RATE_LIMITS = True

# Allow our remote workers to get tasks faster if they have a
# slow internet connection (yes Gurney, I'm thinking of you).
#
# 20140309: no more remote worker and we have very small messages (only
# IDs, no full instance), so stop wasting CPU cycles.
#CELERY_MESSAGE_COMPRESSION = 'gzip'

# Avoid long running and retried tasks to be run over-and-over again.
BROKER_TRANSPORT_OPTIONS = {'visibility_timeout': 86400}

# Half a day is enough
CELERY_TASK_RESULT_EXPIRES = 43200

# The default beiing 5000, we need more than this.
CELERY_MAX_CACHED_RESULTS = 32768

# NOTE: I don't know if this is compatible with upstart.
CELERYD_POOL_RESTARTS = True

# Since Celery 3.1/3.2, no 'pickle' anymore.
# JSON is my prefered option, anyway.
CELERY_ACCEPT_CONTENT = ['pickle', 'json']

CELERY_TASK_SERIALIZER = 'pickle'
CELERY_RESULT_SERIALIZER = 'json'

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
        'schedule': crontab(hour='*', minute='*'),
    },

    'global-checker-task': {
        'task': 'oneflow.core.tasks.global_checker_task',
        'schedule': crontab(hour='1', minute='1'),
    },

    # •••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••• Statistics

    # We update stats regularly to avoid "loosing" data and desynchronization.
    # UDP packets are not reliable. But that's the point of it, isn't it?
    'synchronize-statsd-gauges': {
        'task': 'oneflow.core.stats.synchronize_statsd_gauges',
        'schedule': crontab(minute='59'),
        'args': (True, ),
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
