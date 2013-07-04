import os
working_dir = os.path.dirname(__file__)
os.chdir(working_dir)
import settings
import django.core.management
django.core.management.setup_environ(settings)
