
import dj_database_url
import mongoengine

# will be filled by sub-snippets
DATABASES = {
    'default': dj_database_url.config()
}

mongoengine.connect(os.environ.get('MONGODB_NAME'),
                    host=os.environ.get('MONGODB_HOST'))

REDIS_HOST = os.environ.get('REDIS_HOST', MAIN_SERVER)
REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
REDIS_DB   = int(os.environ.get('REDIS_DB'))

REDIS_TEST_HOST = os.environ.get('REDIS_TEST_HOST', MAIN_SERVER)
REDIS_TEST_PORT = int(os.environ.get('REDIS_TEST_PORT', REDIS_PORT))
REDIS_TEST_DB   = int(os.environ.get('REDIS_TEST_DB'))

REDIS_DESCRIPTORS_HOST = os.environ.get('REDIS_DESCRIPTORS_HOST', MAIN_SERVER)
REDIS_DESCRIPTORS_PORT = int(os.environ.get('REDIS_DESCRIPTORS_PORT', REDIS_PORT))
REDIS_DESCRIPTORS_DB   = int(os.environ.get('REDIS_DESCRIPTORS_DB'))

REDIS_FEEDBACK_HOST = os.environ.get('REDIS_FEEDBACK_HOST', MAIN_SERVER)
REDIS_FEEDBACK_PORT = int(os.environ.get('REDIS_FEEDBACK_PORT', REDIS_PORT))
REDIS_FEEDBACK_DB   = int(os.environ.get('REDIS_FEEDBACK_DB'))

CONSTANCE_REDIS_CONNECTION = os.environ.get('CONSTANCE_REDIS_CONNECTION')

SESSION_REDIS_PREFIX = 'sss'
SESSION_REDIS_HOST   = os.environ.get('SESSION_REDIS_HOST', MAIN_SERVER)
SESSION_REDIS_DB     = int(os.environ.get('SESSION_REDIS_DB'))
SESSION_REDIS_PORT   = int(os.environ.get('SESSION_REDIS_PORT', REDIS_PORT))

# TODO: if we ever need this, move it to $ENV!
#SESSION_REDIS_PASSWORD = 'password'
