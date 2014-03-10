# -*- coding: utf-8 -*-
"""
    1flow fabfile, which relies on sparks.

    Example calls:

        # migrate() must have the *named* `args` argument,
        # else it will conflicts with the implicit `remote_configuration`.
        fab local sdf.migrate:args='redisboard --fake'

        # Thus, this won't work:
        fab local sdf.migrate:'redisboard --fake'

        # copy model data from a DB to another:
        fab test sdf.getdata:landing
        fab local sdf.putdata

        # and then to production:
        fab production sdf.putdata

"""
import os
import pwd

from fabric.api import env, task, roles, local as fablocal

from sparks.fabric import (with_remote_configuration,
                           set_roledefs_and_parallel,
                           worker_roles)
import sparks.django.fabfile as sdf

# Make the main deployment tasks and my other favorites immediately accessible
runable, deploy, fast_deploy = sdf.runable, sdf.deploy, sdf.fast_deploy
maintenance_mode, operational_mode = sdf.maintenance_mode, sdf.operational_mode
run_command, restart_services = sdf.run_command, sdf.restart_services
stop, start, status = sdf.stop_services, sdf.start_services, sdf.status_services
remove, pick, role = sdf.remove_services, sdf.pick, sdf.role
push_environment, git_pull = sdf.push_environment, sdf.git_pull

USE_JENKINS  = pwd.getpwuid(os.getuid()).pw_name == 'jenkins'
JENKINS_JOB  = os.environ.get('JOB_NAME', '1flow')
JENKINS_ROOT = '/var/lib/jenkins/jobs/{0}/workspace'.format(JENKINS_JOB)

# The Django project name
env.project    = 'oneflow'
env.virtualenv = '1flow'
env.parallel   = {'true': True, 'false': False}[
    os.environ.get('SPARKS_PARALLEL', 'true').lower()]
env.encoding   = 'utf-8'
# cf. http://stackoverflow.com/q/9181153/654755
env.shell      = '/bin/bash -l -c'

# WARNING: don't set `env.user` here, it creates false-negatives when
# bare-connecting to servers manually from the current directory. Eg.:
#       paramiko.transport[DEBUG] userauth is OK
#       paramiko.transport[INFO] Authentication (publickey) failed.
# Whereas everything is OK from outside this directory.
# Conclusion: it seems `env.user` overrides even the ~/.ssh/config values.

# Where is the django project located
if USE_JENKINS:
    env.root = JENKINS_ROOT
else:
    env.root = '/home/1flow/www/src'

env.environment  = 'test'
env.repository   = 'git@dev.1flow.net:1flow.git'


def get_current_git_branch():
    return fablocal('git rev-parse --abbrev-ref HEAD',
                    capture=True).strip()


@task
def local():
    # NOTE: in theory a local environment doesn't need any roledef, because
    # we use Profile.development for running processes and all fabric
    # operations should be run via local(). BUT, in fact, they are run via
    # run() or sudo() (sparks doesn't make any difference, all tasks are
    # "remote"), that's why we populate roledefs, to benefit from all sparks
    # tasks.
    set_roledefs_and_parallel({
        'db': ['localhost'],
        'web': ['localhost'],
        'lang': ['localhost'],
        'beat': ['localhost'],
        'shell': ['localhost'],
        'flower': ['localhost'],
        'worker': ['localhost'],
    })

    # As of sparks 2.2+, it should not be needed to set env.host_string anymore,
    # but it's still comfortable to have it when lanching tasks that are not
    # fully roledefs-compatible (eg. sdf.compilemessages ran alone).
    env.host_string = 'localhost'

    if USE_JENKINS:
        env.root = JENKINS_ROOT
    else:
        env.root = os.path.expanduser('~/sources/1flow')

    env.env_was_set = True


@task(alias='test')
def preview(branch=None):
    """ This is the default config, we don't need to set anything more.

        To create a new test environment:

        adapt .ssh/config
        ssh duncan
        lxc-clone
        in the LXC rootfs, clean /etc/supervisor/conf.d/*
        edit firewall / iptables
        start LXC

    """

    #
    # WARNING: when adding preview machine(s),
    # don't forget to add django settings files for them…
    #
    set_roledefs_and_parallel({
        'db': ['obi.1flow.io'],
        'web': ['obi.1flow.io'],
        'lang': ['obi.1flow.io'],
        'beat': ['obi.1flow.io'],
        'shell': ['worbi.1flow.io'],
        'flower': ['worbi.1flow.io'],
        'worker_high': ['obi.1flow.io'],
        'worker_medium': ['worbi.1flow.io'],
        'worker_low': ['worbi.1flow.io'],
    })

    if branch is None:
        env.branch = get_current_git_branch()
    # implicit: else: branch will be 'develop',
    # set directly from the sparks defaults.
    env.sparks_options = {
        'nice_arguments': {
            'worker_low': '-n 5',
            'worker_medium': '-n 1',
            'worker_high': '-n -3',
            'worker_medium': '-n 1',
        },

        'worker_concurrency': {
            'worker_low': 4,
            'worker_medium': 4,
            'worker_high': 6,
        }
    }

    # we force the user because we can login as standard user there
    env.user        = '1flow'
    env.env_was_set = True


@task(aliases=('work', ))
def workers(with_shell=False, with_flower=False):
    """ Just setup the workers roles so we can act easily on all of them. """

    #
    # NOTE: don't try to simply set:
    #       env.roles = worker_roles[:] + ['beat']
    #
    #       This will not work as expected for hosts assuming more than
    #       one role (the first of them will get run multiple times).
    #
    roles = worker_roles[:] + ['beat']

    if with_shell:
        roles.append('shell')

    if with_flower:
        roles.append('flower')

    role(*roles)


@task(aliases=('kill', ))
def reboot(more=False):
    run_command("ps ax | grep 'celery.*worker' | grep -v grep "
                "| awk '{print $1}' | sudo xargs -I% kill % || true")
    if more:
        run_command("ps ax | grep 'celery.*worker' | grep -v grep "
                    "| awk '{print $1}' | sudo xargs -I% kill -9 % || true")


@task
def count():
    run_command("ps ax | grep 'celery.*worker' | grep -v grep "
                "| wc -l")


@task(alias='prod')
def production():
    # we force the user because we can login as standard user there
    env.user        = '1flow'
    env.environment = 'production'
    set_roledefs_and_parallel({
        'db': ['1flow.io'],
        'web': ['1flow.io'],
        'beat': ['worker-01.1flow.io', ],
        'shell': ['worker-03.1flow.io', ],
        'flower': ['worker-01.1flow.io', ],

        'worker_high':       ['worker-01.1flow.io',
                              'worker-02.1flow.io',
                              'worker-03.1flow.io',
                              'worker-04.1flow.io', ],

        'worker_medium':     ['worker-02.1flow.io',
                              'worker-03.1flow.io',
                              'worker-04.1flow.io', ],

        'worker_low':        ['worker-03.1flow.io',
                              'worker-04.1flow.io', ],

        'worker_fetch':      ['worker-02.1flow.io',
                              'worker-03.1flow.io',
                              'worker-04.1flow.io', ],

        'worker_swarm':      ['worker-03.1flow.io',
                              'worker-04.1flow.io', ],

        'worker_clean':      ['worker-04.1flow.io', ],

        'worker_background': ['worker-04.1flow.io', ],
    })
    env.sparks_options = {
        'nice_arguments': {
            'worker_low': '-n 3',
            'worker_fetch': '-n 5',
            'worker_background': '-n 10',
            'worker_swarm': '-n 2',
            'worker_medium': '-n 1',
            'worker_high': '-n -3',
            'shell': '-n -1',
        },

        'ionice_arguments': {
            #'shell': '-n -1',
        },

        'repository': {
            # We need to patch this because worker-04 is an LXC on the same
            # physical host than dev.1flow.net, and getting from it directly
            # doesn't work because of my NAT configuration.
            '__all__': 'git@10.0.3.110:1flow.git',
        },

        'autoscale': {
            'worker_swarm': '32,2',
            'worker_fetch': '24,1',
            'worker_background': '4,0',
            'worker_high': '8,1',

            # Maximum one worker to avoid hammering
            # the database with huge requests.
            'worker_clean': '1,0',

            '__all__': '8,0',
        },

        'max_tasks_per_child': {
            # 2014-03-10: whereas many things have improved with celery 3.1,
            # we still face the problem of slowly leaking workers. Surely it
            # comes from our code, but I didn't find an easy way to find out
            # exactly where. Thus, we relaunch workers every now and then.
            #'worker_swarm': '16',

            # Fetchers can literally eat memory. RECYCLE.
            'worker_fetch': '8',

            # Cleaning tasks are long; worker consumes ~500Mb after first run.
            'worker_clean': '1',

            '__all__': '32',
        },

        # Time-limit is useless because there is already the socket timeout.
        # And anyway, it's leaking memory in celery 3.0.x.
        'worker_soft_time_limit': {
            'worker_swarm': '120',

            # I consider that 5 minutes is enough to convert an article to
            # markdown. If it doesn't acheive the conversion in this time
            # frame, there is probably a more serious problem. Note that it
            # can take time because of high niceness of worker processes,
            # eg. they run at low priority, and a bunch of them on only a
            # few cpu cores. So we have to let them a fair amount of time.
            'worker_fetch': '60',
        },
    }

    env.env_was_set = True


@task
def zero(branch=None):
    """ A master clone, restarted from scratch everytime to test migrations. """

    set_roledefs_and_parallel({
        'db': ['zero.1flow.io'],
        'web': ['zero.1flow.io'],
        'beat': ['zero.1flow.io'],
        'shell': ['zero.1flow.io'],
        'worker': ['zero.1flow.io'],
        'flower': ['zero.1flow.io'],
    })

    if branch is None:
        env.branch = 'develop'
    else:
        env.branch = get_current_git_branch()

    env.host_string = 'zero.1flow.io'

    env.sparks_options = {
        'worker_concurrency': {
            '__all__': 2,
        }
    }

    # env.user is set via .ssh/config
    env.env_was_set = True


@task
def oneflowapp():
    """ 1flowapp.com parameters; must be used with test or production. """

    raise RuntimeError('As of 20130510, this environment '
                       'should not be used anymore.')

    if not hasattr(env, 'env_was_set'):
        # Without this, settings can be messed up.
        raise RuntimeError('Type `oneflowapp` *AFTER* test|production|local !')

    if env.environment == 'production':
        env.sparks_djsettings = '1flowapp_com'

    elif env.environment == 'test':
        if env.host_string == 'localhost':
            env.sparks_djsettings = 'chani_app'
        else:
            env.sparks_djsettings = 'obi_1flowapp_com'

    else:
        raise RuntimeError('environment not supported')


@task
@with_remote_configuration
def testapps(remote_configuration):

    project_apps = (app.split('.', 1)[1] for app
                    in remote_configuration.django_settings.INSTALLED_APPS
                    if app.startswith('{0}.'.format(env.project)))

    print(str(list(project_apps)))


@task
@roles('db')
def firstdata():
    sdf.putdata('./oneflow/landing/fixtures/landing_2013-05-14_final-before-beta-opening.json') # NOQA
    sdf.putdata('./oneflow/base/fixtures/base_2013-05-14_final-before-beta-opening.json') # NOQA

    # No need, this will fail in many cases,
    # and the first run will do it anyway.
    #sdf.putdata('./oneflow/fixtures/djcelery_2013-06-30_0001.json')


@task(aliases=('first', ))
def firstdeploy():
    deploy()
    firstdata()
