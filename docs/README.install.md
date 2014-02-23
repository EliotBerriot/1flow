
1flow installation how-to
~~~~~~~~~~~~~~~~~~~~~~~~~

# Introduction

1flow is a big project. It has a lot of external dependancies and uses 4 underlying engines, for different reasons and purposes (storage, cache...).

It is designed to be run as a scalale webservice, not a simple personal project.

Thus, big-projects rules and constraints apply. For example, it uses a *12-factor* like environment configuration. Django settings can be changed based on hostname or domain with a 2-lines settings file.

Please keep in mind that this was designed as a feature for an original startup project.I don't consider the project bloated regarding this state. It has many advantages for the current setup on 1flow.io, and is future-ready for the upcoming 1flow distributed web.

1flow installation process will probably feel long painful, probably because it is. [Hang on IRC][help] to ask for any help you need.

# Development environment

If you just want to test 1flow, it's the simplest way to go.

The purpose of a development environment is to run everything in debug mode on a sole machine. You can split distribute services afterwards, with another configuration.

The `1flow/fabfile.py` should give you plenty of examples if you are familiar with `Fabric`.

You can use a development environment for a personnal production instance, this won't hurt.


## Installation targets

1flow has been successfully deployed on:

- Ubuntu Server 12.04 LTS (physical hosts and LXCs; used by http://1flow.io/).
- Ubuntu 13.10 (physical hosts and LXCs; my sedentary development machine)
- OSX 10.8 and 10.9 (physical hosts; my mobile development machine)

.. warning:: There is currently an unknown bug with the `Cython` compilation of my `strainer` Python package **on OSX 10.9** which prevents the install to go smoothly. Any [help][] is apreciated.

**On OSX, you should have [brew][] installed before continuing.** Sparks is built upon it for the OSX features.

## Pre-installation

Bootstraping 1flow is done in a Python `virtualenv`.

You must have `virtualenv-wrapper` because `sparks` assumes you have it.

And `git`, obviously.

.. note:: the `virtualenv` is named `1flow` and this is intentional. The default configuration relies on this. You can change it, but you will have to alter the project fabfile in consequence.

You must have my hacked version of `Fabric` (see [notes][#notes]) to run `1flow`:

    # Adapt this to `brew` on OSX, and forget about *-software-properties-*
    sudo apt-get install -q git-core python python-dev \
        python-software-properties software-properties-common \
        virtualenvwrapper

    mkvirtualenv 1flow

    # We assume you are in the new virtualenv now.
    # Sometimes this requires logout/login to update your shell environment.

    pip install -e git+https://github.com/Karmak23/fabric.git#egg=Fabric
    pip install -e git+https://github.com/Karmak23/sparks.git#egg=sparks


## Anti-crazy checks


### Profile

Then, we will check that your `~/.bashrc` or `~/.profile` runs fully-silent in non-interactive mode.

Fabric receipes are very picky about this, and will crash if the result of a `grep` contains superfluous text. To be sure, run::

    export FABFILE="~/.virtualenvs/1flow/src/sparks/fabfile.py"
    fab -H localhost -f ${FABFILE} test

The output should be something like this::

    2014-02-12 13:35:34,031 sparks.fabric.utils[INFO] SPARKS_DOTFILES_PATH is unset, using default value "~/Dropbox/configuration/dotfiles".
    [localhost] Executing task 'test'
    [localhost] run: uname -a; uptime; cat /etc/lsb-release 2>/dev/null; echo $USER — $PWD
    [localhost] Passphrase for private key:
    [localhost] Login password for 'olive':
    [localhost] out: Linux 1flow-test-p9gwax 3.11.0-14-generic #21-Ubuntu SMP Tue Nov 12 17:04:55 UTC 2013 x86_64 x86_64 x86_64 GNU/Linux
    [localhost] out:  13:35:51 up 17 days,  5:08,  2 users,  load average: 8,88, 8,93, 8,95
    [localhost] out: DISTRIB_ID=Ubuntu
    [localhost] out: DISTRIB_RELEASE=13.10
    [localhost] out: DISTRIB_CODENAME=saucy
    [localhost] out: DISTRIB_DESCRIPTION="Ubuntu 13.10"
    [localhost] out: olive — /home/olive
    [localhost] out:


    Done.
    Disconnecting from localhost... done.

Pay attention to the lines starting with `out:`: **if you have something displayed before the `uname` output, 1flow installation will fail**. It's up to you to tweak your profile scripts to be compatible. If unsure, ask for [help][].


### Sudo & SSH

`Fabric` & `sparks` rely a lot on `SSH` and `sudo` for remote commands, even of your local machine. Remember that they are deployment tools, they don't care about if you are on `localhost` or `far.from.here.org`.

During 1flow installation, you will be asked for your passphrase and your password more than a hundred of times. You should heavily consider these things:

    # /etc/sudoers
    %sudo   ALL=(ALL:ALL) NOPASSWD: ALL

    # either
    ssh -A

    # or
    eval `ssh-agent`
    ssh-add

If you're worried by security concerns or don't fully understand, you can come and discuss [on IRC][help]. You are welcome submiting PRs to [sparks][] and [Fabric][] to fully support password/passphrase modes.

There are remote commands that halt because of sudo asking for a password and Fabric borking the input/output. Understand that **the installation will not work without these things** correctly setup.

## 1flow system pre-requisites

We need to pre-install and configure all databases. Most of the dirty job is handled by `sparks`, which will install needed PPAs on Ubuntu, and setup `launchd` on OSX.

    fab -H localhost -f ${FABFILE} db_postgresql db_mongodb db_redis db_memcached

Take a coffee. Small, though, it's quite fast here.

## Setup 1flow environment


### Database configuration


#### PostgreSQL

In the current section, replace all `<whoami>` occurences with your Linux login name.

You have to tweak your `/etc/postgresql/*/pg_hba.conf` and setup your user account as a trusted PostgreSQL user::

    # in /etc/postgresql/*/pg_hba.conf, add these lines:
    local   all             <whoami>                              trust
    host    all             <whoami>        127.0.0.1/32          trust

    # The following line should already be there:
    host    all             all             127.0.0.1/32          md5

Adapt the settings to OSX in the brew installation path if you're on OSX.

Make yourself a database administrator, and create the `oneflow_admin` database administrator (you can customize the name, but you have to alter the fabfile to match):

    sudo su - postgres
    psql
    CREATE ROLE <whoami> PASSWORD '<choose_a_password>' SUPERUSER LOGIN;

    CREATE ROLE oneflow_admin PASSWORD '<choose_a_password>' \
        CREATEDB CREATEUSER NOINHERIT LOGIN;


.. note:: the `oneflow_admin` user is not the database owner. It's used by sparks to create / update automatically the database owner, which will be automatically created later. This is a bit circonvoluted, but ensures the installation process is identical under Ubuntu and OSX via sparks.


#### MongoDB

You should make sure MongoDB listens on the network. **This is already the case on Ubuntu 13.10**, but not on 12.04 LTS.

On OSX this is usually OK, and `sparks` should have done the `launchd` stuff to start it automatically when the machine boots.


### Runtime configuration

Duplicate the `config/dot.env.example` file to `~/.env`, and include it in your shell environment::

    # In you .profile or .bashrc, on the last line:

    # Load a configuration environment if there is any.
    if [[ -e ~/.env ]]; then . ~/.env ; fi

#### Tweak `.env`

You have now to setup everything for 1flow. If you plan to allow social authentication, you'll have some work to do on Twitter API pages, Google API console and the like.

If you don't plan to use social features, you just have to set one or two names (eg `development` or `production`), and for development you need to put `127.0.0.1` in most places.

This section needs more documentation. If you're willing to help, [please apply][help] or [submit a PR][issue].


## Installation

Let `sparks` install 1flow and its direct dependancies::

    # optional
    mkdir ~/sources && cd ~/sources

    # required
    git clone git+https://github.com/1flow/1flow.git
    cd 1flow && make bootstrap

This will run a `fab local firstdeploy` and populate the PostgreSQL database with minimal fixtures data.

.. note:: This operation can be **very long** (eg. 1 hour or more), depending on your machine speed, you internet connection speed and other factors (speed of outside wind, children moving around you, good TV show on the TV, your machine going to sleep in the middle of the process...).

If anything fails, please [report it first on IRC][help], I will try to provide a patch as fast as possible. If nobody's here, please fill an [issue][] with the log output included.


# Running 1flow




# Notes

## About my hacked version of `Fabric`

This is the stock 1.6 version, with [a small patch][patch] applied. [Sparks][] rely on this patch; without this the deployments commands and the magic of `sparks` don't work.


  [patch]: https://github.com/Karmak23/fabric/commit/7bd2eee26d7255c7b0edac0b87c1ee196086668f
  [Sparks]: https://github.com/Karmak23/sparks
  [help]: irc://chat.freenode.net/#1flow
  [brew]: http://brew.sh/
  [Fabric]: http://fabfile.org/
  [issue]: https://github.com/1flow/1flow/issues
