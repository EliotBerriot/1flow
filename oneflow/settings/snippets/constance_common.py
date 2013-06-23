
#
# Default constance keys, and their values.
#

import time, datetime

CONSTANCE_CONFIG = {
    'GR_MAX_ARTICLES': (25 if DEBUG else 250000, ugettext(u'maximum number '
                        u'of Google Reader articles imported for a user.')),
    'GR_MAX_FEEDS': (2 if DEBUG else 1000, ugettext(u'maximum number of '
                     u'articles imported from Google Reader for any user.')),
    'GR_LOAD_LIMIT': (10 if DEBUG else 500, ugettext(u'maximum number of '
                      u'articles in each wave of Google Reader feed import.')),
    'GR_WAVE_LIMIT': (10 if DEBUG else 300, ugettext(u'maximum number of '
                      u'import waves for each Google Reader feed.')),

    'GR_IMPORT_ALLOWED': (True, ugettext(u'Are users allowed to import from '
                          u'Google Reader? Set to False if we reach limits '
                          u'too quickly.')),

    # No need (constance handles dates correctly), but just in case:
    # time.mktime(datetime.date(2013,07,01).timetuple())
    'GR_END_DATE': (datetime.date(2013, 07, 01),
                    ugettext(u'Google Reader official end date')),

    # NOTE about GR_STORAGE_LIMIT:
    # It's about the physical storage limit on duncan.licorn.org
    # Karmak has 160K articles = 7Gb MongoDB, Max disk size = 700Gb
    # 1.5M could still blow duncan's disk in some corner-case conditions,
    # But it's a start, and via constance it's dynamically settable.
    'GR_STORAGE_LIMIT': (100000 if DEBUG else 15000000, ugettext(u'Maximum '
                         u'number of articles in database, after which the '
                         u'Google Reader imports will be disabled.')),

}
