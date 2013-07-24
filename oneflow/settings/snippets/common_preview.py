#
# Add test/preview machines hostnames here.
#

TEMPLATE_CONTEXT_PROCESSORS += (
    'django.core.context_processors.debug',
)

EMAIL_SUBJECT_PREFIX='[OBI.1flow] '


ALLOWED_HOSTS += [
    'obi.1flow.io',
    'obi.1flow.net',
]
