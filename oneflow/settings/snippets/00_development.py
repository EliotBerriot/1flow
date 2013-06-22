import sys

DEBUG = True
TEMPLATE_DEBUG = DEBUG
TASTYPIE_FULL_DEBUG = DEBUG

for celery_name in ('celery', 'celeryd', 'worker', 'flower'):
    if celery_name in sys.argv:
        # Avoid the infamous 'Using settings.DEBUG leads to a memory leak,
        # never use this setting in production environments!' message, cf.
        # http://stackoverflow.com/a/4806384/654755
        DEBUG = False
        break

# Development installs exhibit all admin models.
FULL_ADMIN = True
