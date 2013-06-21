
# Hosts

## On Duncan.licorn.org

On the `10.0.3.0` network:

- 1     PG/redis/MongoDB (duncan, physical host, production + preview)
- 109    worker (LXC TEMPLATE, must stay down and thus unreachable)
- 110    dev.1flow.net (production, sentry)
- 111    obi (preview, web instance)
- 112    1flow.io (production, web instance)
- 113    worker-01 (production worker, high queue)
- 114    worker-03 (production worker, low+default queue)
- 115    worker-05 (production worker, low+default queue)

## On Gurney.licorn.org

On the `10.0.3.0` network:

- 1     PG/redis/MongoDB (Gurney, physical host, preview + tests)
- 10    worbi (preview worker)
- 11    zero (scratch tests, single node web+worker+flower)
- 12    twenty (idem)
- 13    worker-02 (production worker + flower)

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


## Installing a new node

Actions in telegraphic style:

    # OVH: manager
    # edit DNS entries…

    # SSH: duncan
    # edit pg_hba.conf ?
    # edit ~groups/local_config/iptables/iptables.d/* ?

    # SSH: gurney
    sudo lxc-create -n worbi.1flow.io -t ubuntu -- -b olive
    # edit …/config -> lxc.network.ipv4 = …
    # edit /etc/rc.local

    # LOCAL
    # edit .ssh/config … user:olive
    cd ~/Dropbox

    # NOTE: not needed in sparks 2.0
    #fab -H worbi.1flow.io -- sudo apt-get -q update

    fab -H worbi.1flow.io tasks.lxc_base

    # SSH:worbi
    sudo adduser 1flow --force-badname
    sudo adduser 1flow sudo

    # LOCAL
    # edit .ssh/config … user:1flow
    ssh-copy-id worbi
    scp .bashrc worbi:

    # SSH: worbi
    install supervisor

    # LOCAL
    workon 1flow
    cd ~/sources/1flow

    # IF: worker
    fab -H worbi.1flow.io test deploy

    # IF: web
