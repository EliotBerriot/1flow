# -*- coding: utf-8 -*-
""" Global timezone aware functions. """

import datetime as pydatetime

from django.conf import settings
from django.utils.timezone import make_aware, utc, now as timezone_now

# ••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••• Local aliases
dt_combine       = pydatetime.datetime.combine
dt_fromtimestamp = pydatetime.datetime.fromtimestamp


# ••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••• Naive aliases


today     = pydatetime.date.today
timedelta = pydatetime.timedelta


# ••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••• Aware aliases


if settings.USE_TZ:
    now      = timezone_now
    ftstamp  = lambda x: make_aware(dt_fromtimestamp(x), utc)
    combine  = lambda x, y: make_aware(dt_combine(x, y), utc)
    time     = lambda *args: pydatetime.time(*args, tzinfo=utc)
    datetime = lambda *args: pydatetime.datetime(*args, tzinfo=utc)
else:
    now      = pydatetime.datetime.now
    ftstamp  = dt_fromtimestamp
    combine  = dt_combine
    time     = pydatetime.time
    datetime = pydatetime.datetime


# ••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••• functions


def until_tomorrow_delta(time_of_tomorrow=None):
    """ This should probably go to ``oneflow.base.something``. """

    tomorrow = today() + timedelta(days=1)

    if time_of_tomorrow is None:
        time_of_tomorrow = time(0, 0, 0)

    # don't use our combine(), time_of_tomorrow is already aware.
    return dt_combine(tomorrow, time_of_tomorrow) - now()


__all__ = ('today', 'timedelta',
           'now', 'ftstamp', 'combine', 'time', 'datetime',
           'until_tomorrow_delta', )
