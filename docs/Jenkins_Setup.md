
# Harware / system

    export SRV=ci.1flow.net
    export JENK=jenkins@${SRV}
    export LXC_HOST=gurney

    ssh $LXC_HOST
        lxc-clone -n ci.1flow.net -o zero.1flow.io

    ssh ${SRV}
        sudo apt-get install sloccount
        sudo vim /etc/postgres/*/pg_hba.conf

            host    all             postgres            127.0.0.1/32        trust

        sudo service postgresql restart

    fab -H ci tasks.db_redis tasks.db_postgres tasks.db_mongodb tasks.db_memcache tasks.sys_easy_sudo


# Jenkins Install

    install & config see
        https://sites.google.com/site/kmmbvnr/home/django-jenkins-tutorial

    ssh ${SRV}

        wget -q -O - http://pkg.jenkins-ci.org/debian/jenkins-ci.org.key | sudo apt-key add -
        sudo sh -c 'echo deb http://pkg.jenkins-ci.org/debian binary/ > /etc/apt/sources.list.d/jenkins.list'
        sudo apt-get update
        sudo apt-get install jenkins

        sudo adduser jenkins sudo

        sudo su - jenkins
        ssh-keygen -t dsa

        cat ~/.ssh/id_dsa.pub
        # install it in gitolite

        # for Jenkins can do:
        #       fab -H localhost …
        cat ~/.ssh/id_dsa.pub >> ~/.ssh/authorized_keys

        # if we need to pull a local branch (not required in normal conditions):
        # as user olive:
        #cat ~jenkins/.ssh/id_dsa.pub >> ~/.ssh/authorized_keys

        git config --global user.email 'jenkins@1flow.net'
        git config --global user.name "Jenkins for 1flow"

    scp ~/sources/global-config/ENVs/oneflow/developement.env ${JENK}:.env


## Install git plugin


    http://ci.1flow.net/pluginManager/?

    and install “jenkins git plugin”

## Configure security

https://wiki.jenkins-ci.org/display/JENKINS/Standard+Security+Setup

# configure the settingd.py for jenkins

# create .profile for jenkins


# configure remote build

insert a token on remote triguer on the job configuration

# 1flow job configuration

- create a new free style job
    - name "1flow"
- configure the git repo, bash script, etc.

## New execute shell:

    #!/bin/bash -e

    . ~/.env
    virtualenv venv --distribute
    . venv/bin/activate

    mkdir -p $JENKINS_HOME/cache/$JOB_NAME

    export HTTP_PROXY=http://10.0.3.1:3128/
    export http_proxy=http://10.0.3.1:3128/
    export FTP_PROXY=http://10.0.3.1:3128/
    export ftp_proxy=http://10.0.3.1:3128/
    export DJANGO_SETTINGS_MODULE=oneflow.settings
    export SPARKS_VERBOSE=1
    export SPARKS_JENKINS=1
    export SPARKS_PG_SUDO_USER=postgres

    pip install cython --download-cache=$JENKINS_HOME/cache/$JOB_NAME
    pip install -r config/requirements.txt --download-cache=$JENKINS_HOME/cache/$JOB_NAME
    pip install -r config/dev-requirements.txt --download-cache=$JENKINS_HOME/cache/$JOB_NAME

    #
    # temp workaround until fix of mongoadmin
    #
    (cd venv/src/mongoadmin; git reset --hard HEAD~2)

    fab -H localhost sdf.fabfile.dev
    fab -H localhost sdf.fabfile.dev_web
    fab -H localhost sdf.fabfile.dev_django_full
    fab -H localhost sdf.compilemessages

    fab -H localhost sdf.createdb
    #fab -H localhost sdf.syncbd
    #fab -H localhost sdf.migrate

    sudo su - postgres -c 'echo "ALTER ROLE oneflow WITH CREATEDB;" | psql'

    unset HTTP_PROXY
    unset http_proxy
    unset FTP_PROXY
    unset ftp_proxy

    python manage.py jenkins --traceback


## report config

publish new junit test report

    reports/*.xml


# configure git hook


# build the job
