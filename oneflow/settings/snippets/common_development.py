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


ALLOWED_HOSTS += [
    'localhost',
]

INSTALLED_APPS += ('django_nose', 'devserver', )

DEVSERVER_DEFAULT_ADDR = '0.0.0.0'
DEVSERVER_DEFAULT_PORT = 8000

TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'

NOSE_ARGS = ['--stop']

import logging
import south.logger
logging.getLogger('south').setLevel(logging.CRITICAL)
