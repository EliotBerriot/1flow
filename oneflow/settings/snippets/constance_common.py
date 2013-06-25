
#
# Default constance keys, and their values.
#

import datetime

CONSTANCE_CONFIG = {

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

    # No need (constance handles dates correctly), but just in case:
    # time.mktime(datetime.date(2013,07,01).timetuple())
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
