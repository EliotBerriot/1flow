# -*- coding: utf-8 -*-
#
# Default constance keys, and their values.
#
"""
    Copyright 2013 Olivier Cortès <oc@1flow.io>

    This file is part of the 1flow project.

    1flow is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of
    the License, or (at your option) any later version.

    1flow is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public
    License along with 1flow.  If not, see http://www.gnu.org/licenses/

"""

import datetime

#CONSTANCE_REDIS_CONNECTION is to be found in 'snippets/databases*'
CONSTANCE_BACKEND      = 'constance.backends.redisd.RedisBackend'
CONSTANCE_REDIS_PREFIX = 'c0s1f:'

CONSTANCE_CONFIG = {

    # ————————————————————————————————————————————————————————————— Staff stuff


    'STAFF_HAS_FULL_ACCESS': (False, ugettext(u'Allow staff to have full '
                              u'access to anything. We use this mostly for '
                              u'debugging purposes, but this can be dangerous '
                              u'and liberticide in some conditions. NOTE: '
                              u'disabling this does not prevent any malicious '
                              u'code which bypasses this configuration flag.')),


    # ———————————————————————————————————————————————————— System announcements


    'ANNOUNCEMENT_USER': (u'', ugettext(u'Announcement for all users. '
                          u'Markdown accepted. Leave empty for none.')),

    'ANNOUNCEMENT_USER_PREFIX': (ugettext_lazy('*Announcement:* '),
                                 ugettext(u'User announcement '
                                 u'prefix. Set to whatever you want. '
                                 u'Markdown accepted.')),

    'ANNOUNCEMENT_USER_PRIORITY': (u'', ugettext(u'User announcement '
                                   u'priority. Accepted values: info, '
                                   u'success, error or nothing at all.')),

    'ANNOUNCEMENT_USER_START': (datetime.date(1970, 01, 01),
                                ugettext(u'User announcement start '
                                u'date. Leave in the past for immediate '
                                u'display.')),

    'ANNOUNCEMENT_USER_END': (datetime.date(2099, 12, 31),
                              ugettext(u'User announcement end '
                              u'date. Leave in the far future for endless '
                              u'display.')),

    'ANNOUNCEMENT_STAFF': (u'', ugettext(u'Announcement for staff members '
                           u'only. Markdown accepted. Leave empty for none.')),

    'ANNOUNCEMENT_STAFF_PREFIX': (ugettext_lazy('*STAFF:* '),
                                 ugettext(u'Staff announcement '
                                 u'prefix. Set to whatever you want. '
                                 u'Markdown accepted.')),

    'ANNOUNCEMENT_STAFF_PRIORITY': (u'', ugettext(u'Staff announcement '
                                   u'priority. Accepted values: info, '
                                   u'success, error or nothing at all.')),

    'ANNOUNCEMENT_STAFF_START': (datetime.date(1970, 01, 01),
                                 ugettext(u'Staff announcement start '
                                 u'date. Leave in the past for immediate '
                                 u'display.')),

    'ANNOUNCEMENT_STAFF_END': (datetime.date(2099, 12, 31),
                               ugettext(u'Staff announcement end '
                               u'date. Leave in the far future for endless '
                               u'display.')),

    # •••••••••••••••••••••••••••••••••••••••••••••• WEB / Templates / JS & CSS

    'WEB_CDNS_ENABLED': (False, ugettext(u'Enable This to use public CDNs for '
                         u'common JS and CSS (jQuery, bootstrap...). Disabled '
                         u'by default to avoid tracking and allow autonomous '
                         u'run.')),

    'WEB_BOOTSWATCH_THEME': (u'', ugettext(u'Choose your bootswatch '
                             u'theme here. If you have CDNs enabled, you '
                             u'must choose a public theme. Default: no '
                             u'bootswatch theme, meaning that 1flow uses its '
                             u'original detail-admin. Possible values include '
                             u'"flatly", "yeti", and all other bootswatch '
                             u'themes, including your own if you deactivate '
                             u'the CDN utilization.')),

    'WEB_THEME_NAVBAR_INVERSE': (True, ugettext(u'Does the bootstrap navbar '
                                 u'uses inverse colors. Default: true, for '
                                 u'detail-admin theme.')),

    # HEADS UP: the 3 next are translatable, to allow providing
    #           different addresses for multi-language support.

    'SUPPORT_EMAIL_ADDRESS': (ugettext(u'supportREMOVETHIS@1flow.io'),
                              ugettext(u'Support email address. Set empty '
                                       u'to disable displaying it in the '
                                       u'support text message.')),

    'IRC_SUPPORT_CHANNEL': (ugettext(u'#1flow'), ugettext(u'Support IRC '
                            u'channel. Set empty to disable displaying it '
                            u'in the support text message.')),

    'IRC_SUPPORT_SERVER': (ugettext(u'irc.freenode.net'),
                            ugettext(u'Support IRC server.')),

    # ———————————————————————————————————————————— Allow new users to register?

    'SOCIAL_LOGIN_ENABLED': (True, ugettext(u'Already known users are allowed '
                             u'to sign in via social network accounts. '
                             u'Default: True. See SOCIAL_REGISTRATION_ENABLED '
                             u'for new accounts.')),

    'SOCIAL_REGISTRATION_ENABLED': (True, ugettext(u'New users are allowed to '
                                    u'auto-register accounts via social '
                                    u'networks signins. Default: False.')),

    'LOCAL_LOGIN_ENABLED': (True, ugettext(u'Already known users are allowed '
                            u'to sign in via local accounts. Default: True. '
                            u'You can disable this to allow only social '
                            u'signins.')),

    'LOCAL_REGISTRATION_ENABLED': (True, ugettext(u'New users are allowed to '
                                    u'register local accounts. Default: '
                                    u'False. NOTE2: the underlying code does '
                                    u'not currently use this dynamic '
                                    u'configuration. We have to contribute a '
                                    u'patch, but the configuration directive '
                                    u'exists, at least.')),

    # ••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••• Read webapp

    'DOCUMENTS_ARCHIVING_DISABLED': (False, ugettext(u'Set this to True to '
                            u'disable maintenance archiving operations. '
                            u'Useful for archive database migrations (BUT '
                            u'NOT SUFFICIENT, because of `original_data` that '
                            u'must be disabled too, via `*_FETCH_DISABLED`).')),

    # ••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••• Read webapp

    'READ_INFINITE_AUTOSCROLL_ENABLED': (True, ugettext(u'Make the read view '
                                         u'(either list or tiles) '
                                         u'automatically load new content '
                                         u'when reaching end of page.')),

    'READ_INFINITE_ITEMS_PER_FETCH': (ENDLESS_PAGINATION_PER_PAGE,
                                      ugettext(u'Number of items per ajax '
                                      u'fetch on infinite pagination pages.')),

    'READ_ARTICLE_MIN_LENGTH': (24, ugettext(u'Minimum length of an article '
                                u'content. Set to 0 to always display '
                                u'Markdown content to users, whatever it is.')),

    # Cf. http://mindbluff.com/askread.htm
    'READ_AVERAGE_READING_SPEED': (200, ugettext(u'The average number of '
                                   u'words per minutes that an adult can '
                                   u'read. When the user has not configured '
                                   u'his/her own, this one will be used.')),

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

    'FEED_REFRESH_RANDOMIZE_DELAY': (40, ugettext(u'Number of seconds max for '
                                     u'the randomization (eg. between 0 and '
                                     u'this number). Warning: keep this '
                                     u'lower than the peridicity of the feed '
                                     u'refresher, else some tasks will be '
                                     u'duplicated.')),

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

    'ARTICLE_ARCHIVE_OLDER_THAN': (62, ugettext(u'Only articles older than '
                                   u'that will be archived, regarding their '
                                   u'`date_published` field. This delta is '
                                   u'expressed in days. Set to 0 to archive '
                                   u'everything without mercy.')),

    # ••••••••••••••••••••••••••••••••••••••••••• Various checks and core tasks

    'CHECK_SUBSCRIPTIONS_DISABLED': (False, ugettext(u'Disable or not the '
                                     u'night subscription check that will '
                                     u'check_reads() all subscriptions that '
                                     u'do not have the same number of '
                                     u'articles than the feed they belong '
                                     u'to. Default: enabled.')),

    'CHECK_DUPLICATES_DISABLED': (False, ugettext(u'Disable or not the '
                                  u'night duplicates check that will '
                                  u'ensure all duplicate articles have '
                                  u'no read left in the system. Default: '
                                  u'let it run (=enabled).')),

    'CHECK_READS_DISABLED': (False, ugettext(u'Disable or not the night '
                             u'reads check that will switch on-and-off their '
                             u'`is_good` attribute. Default: let it run '
                             u'(=enabled).')),

    # ——————————————————————————————————————————————————————— Exerpt generation

    'EXCERPT_PARAGRAPH_MIN_LENGTH': (64, ugettext(u'Number of characters '
                                     u'below which a paragraph does not '
                                     u'have enough data (words) to be '
                                     u'considered informational.')),

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
