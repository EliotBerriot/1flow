# -*- coding: utf-8 -*-
#
# Default constance keys, and their values.
#

import datetime

#CONSTANCE_REDIS_CONNECTION is to be found in 'snippets/databases*'
CONSTANCE_BACKEND      = 'constance.backends.redisd.RedisBackend'
CONSTANCE_REDIS_PREFIX = 'c0s1f:'

CONSTANCE_CONFIG = {

    # •••••••••••••••••••••••••••••••••••••••••••••••••••••••••• RSS feed fetch

    # SEMANTIC NOTE: we use 'disabled' (and not 'enabled') because the rss
    # refreshing is something that is enabled in normal conditions. Stopping
    # it is an unusual / rare action, so the setting is named accordingly.
    'FEED_FETCH_DISABLED': (False, ugettext(u'Set this to True for '
                            u'maintenance operations and wait for all '
                            u'fetchers to terminate. It should take at '
                            u'most FEED_FETCH_DEFAULT_INTERVAL seconds.')),

    'FEED_FETCH_GHOST_ENABLED': (False, ugettext(u'Enable Ghost fetching or '
                                 u'not. Disabled by default, make OSX Python '
                                 u'crash.')),

    'FEED_FETCH_MAX_ERRORS': (90, ugettext(u'The maximum number of errors '
                              u'a feed can meet before beiing automatically '
                              u'closed.')),

    'FEED_FETCH_DEFAULT_INTERVAL': (43200, ugettext(u'Default feed fetch '
                                    u'interval in seconds. You can tune the '
                                    u'interval for each feed after creation.')),

    'FEED_FETCH_MIN_INTERVAL': (300, ugettext(u'The minimum interval between '
                                u'fetches of the same feed. Warning: anything '
                                u'under 60 will not be taken in account.')),

    'FEED_FETCH_MAX_INTERVAL': (259200, ugettext(u'The maximum interval between '
                                u'fetches of the same feed. Warning: anything '
                                u'more than 7 days (expressed in seconds) will '
                                u'not be taken in account.')),

    'FEED_FETCH_RAISE_THRESHOLD': (10, ugettext(u'If this feed produces more '
                                   u'new articles than this number, it will '
                                   u'be fetched more fast than a feed that '
                                   u'produces less. Minimum value: 5.')),

    'FEED_FETCH_PARALLEL_LIMIT': (16, ugettext(u'Default number of articles '
                                  u'fetchable from the same feed at the same '
                                  u'time. Workers should adjust the value '
                                  u'automatically as time passes.')),

    # •••••••••••••••••••••••••••••••••••••••••••••••• Feed admin configuration

    'FEED_REFRESH_RANDOMIZE': (True, ugettext(u'Set this to False if you want '
                               u'all feeds with the same fetch interval to '
                               u'fetch at the same time. Default is to '
                               u'randomize the refreshs not to hammer our '
                               u'machines.')),

    'FEED_ADMIN_LIST_PER_PAGE': (100, ugettext(u'How many feeds per page in '
                                 u'the Django admin. Increase only if '
                                 u'performance is acceptable; do NOT abuse!')),

    'FEED_ADMIN_MEANINGFUL_DELTA': (6 * 365 / 12, ugettext(u'We see how many '
                                    u'articles feeds have produced during this '
                                    u'delta (in days), to see if we can close '
                                    u'them or not (if they got 0 new '
                                    u'articles).')),

    'FEED_CLOSED_WARN_LIMIT': (5, ugettext(u'Number of days during which a '
                               u'just closed feed will be warned about to '
                               u'site managers via mail.')),

    # ••••••••••••••••••••••••••••••••••••••••••••••••••••••••• Article parsing

    'ARTICLE_FETCHING_DEBUG': (False, ugettext(u'Enable this to log '
                               u'intermediate article versions. Default: '
                                  u'not enabled in normal conditions.')),

    'ARTICLE_ABSOLUTIZING_DISABLED': (False, ugettext(u'Disable or not the '
                                      u'article URL absolutization. Default: '
                                      u'enabled in normal conditions (and '
                                      u'without it we will have a lot of '
                                      u'duplicate content that will need '
                                      u'post-processing).')),

    'ARTICLE_FETCHING_DISABLED': (False, ugettext(u'Disable or not '
                                  u'global fetching operations for all '
                                  u'content types. Default: '
                                  u'enabled in normal conditions.')),

    'ARTICLE_FETCHING_TEXT_DISABLED': (False, ugettext(u'Disable or not '
                                       u'text fetching operations. Default: '
                                       u'enabled in normal conditions.')),

    'ARTICLE_FETCHING_VIDEO_DISABLED': (False, ugettext(u'Disable or not '
                                        u'video fetching operations. Default: '
                                        u'enabled in normal conditions.')),

    'ARTICLE_FETCHING_IMAGE_DISABLED': (False, ugettext(u'Disable or not '
                                        u'image fetching operations. Default: '
                                        u'enabled in normal conditions.')),

    'ARTICLE_MARKDOWN_DISABLED': (False, ugettext(u'Disable or not the HTML '
                                  u'to Markdown internal conversion. '
                                  u'Default: enabled in normal conditions.')),

    'ARTICLE_ARCHIVE_BATCH_SIZE': (100 if DEBUG else 50000,
                                   ugettext(u'how much articles will be '
                                   u'archived at each archive task run.')),

    # •••••••••••••••••••••••••••••••••••••••••••••••••••• Google Reader Import

    # GR_LOAD_LIMIT * GR_WAVE_LIMIT must equals GR_MAX_ARTICLES:
    # In the worst case, a user could have only one feed containing all its
    # articles. In this case, if WAVE_LIMIT is too low, the import tasks will
    # stop because of waves exhaustion, but the global import will never stop
    # because neither GR_MAX_ARTICLES nor total_starred nor total_reads would
    # have been reached.
    'GR_MAX_ARTICLES': (25 if DEBUG else 500000, ugettext(u'maximum number '
                        u'of Google Reader articles imported for a user. '
                        u'WARNING: GR_LOAD_LIMIT * GR_WAVE_LIMIT must equals '
                        u'GR_MAX_ARTICLES, else you risk never-ending '
                        u'imports in some rare cases.')),

    'GR_MAX_FEEDS': (2 if DEBUG else 1000, ugettext(u'maximum number of '
                     u'articles imported from Google Reader for any user.')),

    'GR_LOAD_LIMIT': (10 if DEBUG else 500, ugettext(u'maximum number of '
                      u'articles in each wave of Google Reader feed import. '
                      u'WARNING: stop all imports before raising this, or '
                      u'some data will be missed by running tasks. No such '
                      u'problem if your lower it.')),

    'GR_WAVE_LIMIT': (10 if DEBUG else 1000, ugettext(u'maximum number of '
                      u'import waves for each Google Reader feed.')),

    'GR_IMPORT_ALLOWED': (True, ugettext(u'Are users allowed to import from '
                          u'Google Reader? Set to False if we reach limits '
                          u'too quickly.')),

    'GR_MAX_RETRIES': (5, ugettext(u'How many retries to attempt if a '
                       u'Google Reader Operation fails.')),

    # WARNING: keep this a date(), which is neither naive nor TZ aware.
    'GR_END_DATE': (datetime.date(2013, 07, 01),
                    ugettext(u'Google Reader official end date')),

    # NOTE about GR_STORAGE_LIMIT:
    # It's about the physical storage limit on duncan.licorn.org. On my
    # development machine, 260K articles = 1.7Gb only of storage reported in
    # MongoHub, but 6.5Gb really occupied on disk. Duncan's maximum storage
    # availability is ~650Gb, which leads us to a neat 27000000 articles.
    'GR_STORAGE_LIMIT': (100000 if DEBUG else 27000000, ugettext(u'Maximum '
                         u'number of articles in database, after which the '
                         u'Google Reader imports will be disabled.')),

}
