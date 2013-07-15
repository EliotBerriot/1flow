
import dj_database_url
import mongoengine

# will be filled by sub-snippets
DATABASES = {
    'default': dj_database_url.config()
}

SESSION_REDIS_PREFIX = 'sss'

# TODO: if we ever need them, move them to $ENV!
#SESSION_REDIS_PORT = 6379
#SESSION_REDIS_PASSWORD = 'password'

mongoengine.connect(os.environ.get('MONGODB_NAME'),
                    host=os.environ.get('MONGODB_HOST'))

REDIS_DB             = int(os.environ.get('REDIS_DB'))
REDIS_TEST_DB        = int(os.environ.get('REDIS_TEST_DB'))
REDIS_DESCRIPTORS_DB = int(os.environ.get('REDIS_DESCRIPTORS_DB'))

CONSTANCE_REDIS_CONNECTION = os.environ.get('CONSTANCE_REDIS_CONNECTION')

SESSION_REDIS_HOST = os.environ.get('SESSION_REDIS_HOST')
SESSION_REDIS_DB   = int(os.environ.get('SESSION_REDIS_DB'))
