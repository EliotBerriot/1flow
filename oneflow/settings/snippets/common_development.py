#
# Include your development machines hostnames here.
#
# NOTE: this is not strictly needed, as Django doesn't enforce
# the check if DEBUG==True. But Just in case you wanted to disable
# it temporarily, this could be a good thing to have your hostname
# here.
#
# If you connect via http://localhost:8000/, everything is already OK.

TEMPLATE_CONTEXT_PROCESSORS += (
    'django.core.context_processors.debug',
)

EMAIL_SUBJECT_PREFIX='[1flow DEV] '

INTERNAL_IPS = (
    '127.0.0.1',
    # gurney.licorn.org
    '109.190.93.141',
    # my LAN address
    '192.168.111.23',

    # My LAN's proxy address, else the nginx proxy makes debug disappear.
    '192.168.111.111',
)

PROJECT_APPS = (
    'oneflow.base',
    'oneflow.landing',
    'oneflow.core',
)

JENKINS_TASKS = (
    'django_jenkins.tasks.with_coverage',
    'django_jenkins.tasks.django_tests',   # select one django or
    #'django_jenkins.tasks.dir_tests'      # directory tests discovery

    # Doesn't work.
    #'django_jenkins.tasks.run_flake8',

    # Superseded by flake8
    'django_jenkins.tasks.run_pep8',
    'django_jenkins.tasks.run_pyflakes',

    #'django_jenkins.tasks.run_pylint',
    #'django_jenkins.tasks.run_jslint',
    #'django_jenkins.tasks.run_csslint',
    'django_jenkins.tasks.run_sloccount',
    #'django_jenkins.tasks.lettuce_tests',
)

ALLOWED_HOSTS += [
    'localhost',
]

INSTALLED_APPS += ('django_jenkins', 'django_nose', 'devserver', )
                   #'template_debug', )

DEVSERVER_DEFAULT_ADDR = '0.0.0.0'
DEVSERVER_DEFAULT_PORT = 8000

TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'
JENKINS_TEST_RUNNER='django_jenkins.nose_runner.CINoseTestSuiteRunner'

NOSE_ARGS = ['--stop'] #, '--ipdb', '--ipdb-failures', ]



import logging
import south.logger
logging.getLogger('south').setLevel(logging.CRITICAL)
