# -*- coding: utf-8 -*-
""" Global timezone aware functions. """

import time as pytime
import datetime as pydatetime
import humanize.time as humanize_time

from django.conf import settings
from django.utils.timezone import (is_aware, is_naive, # NOQA
                                   make_aware, utc,
                                   now as dj_now)


# ••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••• Local aliases


dt_combine       = pydatetime.datetime.combine
dt_fromtimestamp = pydatetime.datetime.fromtimestamp


# ••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••• Naive aliases


today     = pydatetime.date.today
timedelta = pydatetime.timedelta

naturaltime  = humanize_time.naturaltime
naturaldelta = humanize_time.naturaldelta


# ••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••• Aware aliases


if settings.USE_TZ:
    now       = dj_now
    ftstamp   = lambda x: dt_fromtimestamp(x, utc)
    tzcombine = lambda x, y: make_aware(dt_combine(x, y), utc)
    time      = lambda *args: pydatetime.time(*args, tzinfo=utc)
    datetime  = lambda *args: pydatetime.datetime(*args, tzinfo=utc)

else:
    now       = pydatetime.datetime.now
    ftstamp   = dt_fromtimestamp
    tzcombine = dt_combine
    time      = pydatetime.time
    datetime  = pydatetime.datetime

combine  = dt_combine


# ••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••• functions


def until_tomorrow_delta(time_of_tomorrow=None):
    """ This should probably go to ``oneflow.base.something``. """

    tomorrow = today() + timedelta(days=1)

    if time_of_tomorrow is None:
        time_of_tomorrow = time(0, 0, 0)

    return combine(tomorrow, time_of_tomorrow) - now()


def stats_datetime():

    return pytime.strftime('%Y%m%d %H:%M')


__all__ = ('today', 'timedelta', 'naturaltime', 'naturaldelta',
           'now', 'ftstamp', 'tzcombine', 'combine', 'time', 'datetime',
           'is_aware', 'is_naive',
           'until_tomorrow_delta',
           'pytime', 'pydatetime')
