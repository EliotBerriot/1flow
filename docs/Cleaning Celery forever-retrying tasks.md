
# Getting rid of old tasks

These tasks keep retrying infinitely.

Cf. http://dev.1flow.net/webapps/1flow/group/6290/

The solution involves finding tasks to revoke (cf. IPython notebook):

    import os
    import itertools
    import requests
    import simplejson as json
    from django.conf import settings

    from mongoengine import Document
    from oneflow.core.models.nonrel import *

    ftot=lambda x: '\n'.join('    %s: %s' % (l,w) for (l,w) in sorted(x.iteritems()))

    from celery import Celery
    from celery.events.state import State
    from celery.task.control import inspect, revoke

    i = inspect()
    registered_tasks = i.registered_tasks()

    with open('revoked-tasks.ids', 'rb') as f:
        all_revoked = set(x.strip() for x in f.readlines())

    # <codecell>

    revoked = counter = last_revoked = 0

    tasks    = requests.get('http://flower.1flow.net/api/tasks?limit=100000&state=RECEIVED',
                            auth=('obi1', 'kenobi')).json()
    to_fetch = []

    for tid, task in tasks.iteritems():
        last_revoked = revoked

        if task['name'] == 'Article.fetch_content' and task['args'].startswith('(<Article: '):
            revoke(tid, terminate=True)
            article_id = task['args'].split(' (#', 1)[1][:24]
            #print u'RVK %s@%s>%s, %s ' % (tid, task['hostname'].split('.', 1)[0], article_id, task['args'][:70])
            to_fetch.append(article_id)
            all_revoked.add(tid)
            revoked += 1

        counter += 1

        if revoked != last_revoked and (revoked % 100) == 0:
            print '>> %s/%s done…' % (revoked, counter)

    to_fetch_final = to_fetch_final.union(set(to_fetch))

    print '\n\n>> Revoked %s/%s tasks (total %s/%s)' % (revoked, counter, len(all_revoked), len(to_fetch_final))

    print u'\n'.join(u'>> revoked on %s: %s' % (k, len(v)) for k, v in i.revoked().iteritems())

    # We need to revoke them regularly, because workers are restarted
    for tid in all_revoked:
        revoke(tid, terminate=True) # , signal=9

    # save tasks IDs, to clear them from REDIS
    with open('revoked-tasks.ids', 'wb') as f:
        f.write(u'\n'.join(all_revoked) + u'\n')


## Definitive removing from broker

If we don't do this, the revocation is not sufficient. Some of the tasks come back over and over again after the retry-delay.

    while read ID
    do
        redis-cli -n 1 del celery-task-meta-${ID}
    done < /home/lxc/data/worker-03.1flow.io/rootfs/home/1flow/www/src/revoked-tasks.ids

    # doesn't work, probably redis-cli mixes stdout and stderr
    # | grep ' 1' | wc -l
