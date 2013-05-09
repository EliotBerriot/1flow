# -*- coding: utf-8 -*-
"""
    1flow fabfile, which relies on sparks.

    Example calls:

        # migrate() must have the *named* `args` argument,
        # else it will conflicts with the implicit `remote_configuration`.
        fab local oneflowapp sdf.migrate:args='redisboard --fake'

        # Thus, this won't work:
        fab local oneflowapp sdf.migrate:'redisboard --fake'

        # copy model data from a DB to another:
        fab test oneflowapp sdf.getdata:landing
        fab local oneflowapp sdf.putdata

        # and then to production:
        fab production oneflowapp sdf.putdata

"""
import os
import pwd

from fabric.api import env, task

from sparks.fabric import with_remote_configuration
import sparks.django.fabfile as sdf

# Make the main deployment tasks immediately accessible
runable, deploy, fast_deploy = sdf.runable, sdf.deploy, sdf.fast_deploy

# The Django project name
env.project        = 'oneflow'
env.virtualenv     = '1flow'
env.user           = '1flow'
# Where is the django project located
env.root           = '/home/1flow/www/src'
env.host_string    = 'obi.1flow.net'
env.environment    = 'test'
env.pg_superuser   = 'oneflow_admin'
env.pg_superpass   = 'ZQmeDuNF7b2GMC'


@task
def local():
    env.host_string = 'localhost'
    env.environment = 'test'
    env.user        = pwd.getpwuid(os.getuid()).pw_name
    env.root        = os.path.expanduser('~/sources/1flow')
    env.env_was_set = True


@task
def test():
    """ This is the default config, we don't need to set anything more. """
    env.env_was_set = True


@task
def oneflowapp():
    """ 1flowapp.com parameters; must be used with test or production. """

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


@task(alias='prod')
def production():
    env.host_string = '1flow.net'
    env.environment = 'production'
    env.env_was_set = True


@task
@with_remote_configuration
def testapps(remote_configuration):

    project_apps = (app.split('.', 1)[1] for app
                    in remote_configuration.django_settings.INSTALLED_APPS
                    if app.startswith('{0}.'.format(env.project)))

    print(str(list(project_apps)))
