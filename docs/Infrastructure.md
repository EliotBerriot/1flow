
# Hosts


## On Lafayette.licorn.org

On the `10.0.3.0` network:

- 1      PG/redis/MongoDB (duncan, physical host, production + preview)
- 40     mail.1flow.io
- 90     archive.1flow.io (MongoDB archive database, on port 27018 (host) and 27017 (LXC))

- 99    worker (LXC TEMPLATE, must stay down and thus unreachable)

- 100   dbcache.1flow.io (PostgreSQL, redis, memcache)
    # remote
    sudo route add default gw 10.0.3.1
    
    # local
    fab -H dbcache tasks.pkg.update tasks.lxc_base_and_dev \
        tasks.db_postgresql tasks.db_redis tasks.db_memcached

- 101   data.1flow.io (MongoDB, possibly a cluster)

    # local
    fab -H dbcache tasks.pkg.update tasks.lxc_base_and_dev tasks.db_mongodb

- 109   archive.1flow.io (MongoDB archive database)

- 110    dev.1flow.net (production, sentry)
- 111    cutie.1flow.io (statsd, graphite)

- 112    1flow.io (production, web instance)

- 113    worker-01 (production worker, high queue, flower)
- 114    worker-03 (production worker, medium queues, iPython shell)
- 115    worker-05 (production worker, low queues)

- 116    worker-02 (aux. production worker, high + swarm queues)
- 117    worker-04 (aux. production worker, medium + fetch queues)
- 118    worker-06 (aux. production worker, low + background queues)



## On Gurney.licorn.org

On the `10.0.3.0` network:

- 1     PG/redis/MongoDB (Gurney, physical host, preview + tests)
- 10    worbi (preview worker)
- 11    zero (scratch tests, single node web+worker+flower)
- 12    twenty (idem)
- [disabled] 113    worker-02 (aux. production worker, low + medium queues)


## On Orni.licorn.org OBSOLETE 20140222

On the `10.0.3.0` network:

- 1     PG/redis/MongoDB (duncan, physical host, production + preview)
- 109    worker (LXC TEMPLATE, must stay down and thus unreachable)
- 110    dev.1flow.net (production, sentry)
- 112    1flow.io (production, web instance)

- 113    worker-01 (production worker, high queue, flower)
- 114    worker-03 (production worker, medium queues, iPython shell)
- 115    worker-05 (production worker, low queues)


## On Heighliner.licorn.org OBSOLETE 20140222

On the `10.0.3.0` network:

- 1     host, physical machine
- ??    dev (sentry, has its own PG/redis/memcache)
- 90     archive.1flow.io (MongoDB archive database, on port 27018 (host) and 27017 (LXC))

- 116    worker-02 (aux. production worker, high + swarm queues)
- 117    worker-04 (aux. production worker, medium + fetch queues)
- 118    worker-06 (aux. production worker, low + background queues)

# Databases

# Redis

## Configuration

    databases 20

## Numbering and accesses

development & production use same numbers: obviously they are never on the same
machine, there can't be any collision, unlike production & preview which are
on the same machine as of 2013-06-07.

- Main 1flow database (comments, ratings…) is **0**.
    - on preview we could set it to **10**, to avoid mixing prod/preview, except
      if it's a desired behavior (cutting edge code on real data).

- Celery broker and results is **1**.
    - except on preview, where is it **11**. This allows eventually running production and preview on the same Redis server.

- Redis-sessions is **2**,
    - on preview, **12**.

- Test redis database is 9
    - 19 on preview


## Installing a new node

Actions in telegraphic style:

    # OVH: manager
    # edit DNS entries…

    export ENV=production
    export ADMIN=olive
    export WORKER=worker-99.1flow.io

    ssh ${MAIN_SERVER}
    # edit pg_hba.conf ? (if not already OK via global-config)
    # edit ~groups/local_config/iptables/iptables.d/* ? (idem)

    ssh ${LXC_HOST}
    sudo lxc-create -n ${WORKER} -t ubuntu -- -b ${ADMIN}
    # edit …/config -> lxc.network.ipv4 = …
    # edit /etc/rc.local

    vim ~/.ssh/config
    # >>> User olive
    cd ~/sources/global-config

    # NOTE: not needed in sparks 2.0
    #fab -H ${WORKER} -- sudo apt-get -q update

    fab -H ${WORKER} tasks.lxc_base_and_dev

    ssh ${ADMIN}@${WORKER}
    sudo adduser 1flow --force-badname
    # pick a password for the ssh-copy-id
    sudo adduser 1flow sudo

    # LOCAL
    vim ~/.ssh/config
    # >>> "User 1flow"

    ssh-copy-id ${WORKER}
    scp ~/.bashrc ${WORKER}:
    workon 1flow

    # IF: worker
    # DOESN'T WORK: fab -H worbi.1flow.io test deploy
    fab ${ENV} pick:${WORKER} deploy

# Adding / Changing workers / queues

Works since sparks 3.5.

## Adding new workers to a running pool

    # hack fabfile to add new queues / workers
    fab prod pick:w1,w2 restart


## Adding new queues to existing workers without restarting everything

Works since sparks 3.6.

    # hack fabfile to add new queues
    fab prod role:queue restart

## Removing a given queue on all workers of its type

Works since sparks 3.6.

    # DO NOT touch fabfile

    fab prod role:queue remove

    # hack fabfile to remove all references to the queue

## Removing a given queue on only *some* of its workers

Works since sparks 3.6.

    # DO NOT touch fabfile

    fab prod role:queue pick:w1 remove

    # hack fabfile to remove the machine from the role
