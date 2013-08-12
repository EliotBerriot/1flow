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

# Make the main deployment tasks immediately accessible
runable, deploy, fast_deploy = sdf.runable, sdf.deploy, sdf.fast_deploy
maintenance_mode, operational_mode = sdf.maintenance_mode, sdf.operational_mode
run_command, restart_services = sdf.run_command, sdf.restart_services
stop, start, status = sdf.stop_services, sdf.start_services, sdf.status_services
remove, pick, role = sdf.remove_services, sdf.pick, sdf.role

USE_JENKINS = pwd.getpwuid(os.getuid()).pw_name == 'jenkins'

# The Django project name
env.project    = 'oneflow'
env.virtualenv = '1flow'
env.parallel   = True

# WARNING: don't set `env.user` here, it creates false-negatives when
# bare-connecting to servers manually from the current directory. Eg.:
#       paramiko.transport[DEBUG] userauth is OK
#       paramiko.transport[INFO] Authentication (publickey) failed.
# Whereas everything is OK from outside this directory.
# Conclusion: it seems `env.user` overrides even the ~/.ssh/config values.

# Where is the django project located
if USE_JENKINS:
    env.root         = '/var/lib/jenkins/jobs/1flow_django_jenkins/workspace'
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
        env.root         = '/var/lib/jenkins/jobs/1flow_django_jenkins/workspace'
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
def workers():
    """ Just setup the workers roles so we can act easily on all of them. """

    #TODO: set worker_roles
    env.roles = worker_roles[:] + ['beat']


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
        'worker_high': ['worker-01.1flow.io', ],
        'worker_medium': ['worker-03.1flow.io', ],
        'worker_low': ['worker-05.1flow.io', ],
        'worker_swarm': ['worker-99.1flow.io', ],
        'worker_fetch': ['worker-04.1flow.io',
                         'worker-99.1flow.io', ],
    })
    env.sparks_options = {
        'repository': {
            # We need to patch this because worker-04 is an LXC on the same
            # physical host than dev.1flow.net, and getting from it directly
            # doesn't work because of my NAT configuration.
            'worker-04.1flow.io': 'git@10.0.3.110:1flow.git',
        },
        'worker_concurrency': {
            # setting only 'worker-99.1flow.io'
            # would override worker_swarm setting.
            'worker_fetch@worker-99.1flow.io': 16,

            'worker_swarm': 48,
            '__all__': 8,
        },
        'worker_queues': {
            # The 3 fetchers help on main queues.
            'worker_fetch@worker-02.1flow.io': 'fetch,low',
            'worker_fetch@worker-04.1flow.io': 'fetch,high',
            'worker_fetch@worker-99.1flow.io': 'fetch,medium',
        },
        'worker_soft_time_limit': {
            'worker_swarm': '30',
        },
        # Eventlet is definitively broken, the worker halts every now and then.
        # 'worker_pool': {
        #     'worker_swarm': 'eventlet',
        # },
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
    sdf.putdata('./oneflow/fixtures/djcelery_2013-06-30_0001.json')


@task(aliases=('first', ))
def firstdeploy():
    deploy()
    firstdata()
