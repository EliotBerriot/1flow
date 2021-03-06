# -*- coding: utf-8 -*-
""" Global timezone aware functions.

    ____________________________________________________________________

    Copyright 2012-2014 Olivier Cortès <oc@1flow.io>

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

import logging

import time as pytime
import datetime as pydatetime
from humanize.i18n import django_language
import humanize.time as humanize_time

from django.conf import settings
from django.utils.timezone import (is_aware, is_naive, # NOQA
                                   make_aware, utc,
                                   now as dj_now)

LOGGER = logging.getLogger(__name__)

# ••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••• Local aliases


dt_combine       = pydatetime.datetime.combine
dt_fromtimestamp = pydatetime.datetime.fromtimestamp


# ••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••• Naive aliases


today     = pydatetime.date.today
timedelta = pydatetime.timedelta


def naturaltime(*args, **kwargs):
    with django_language():
        return humanize_time.naturaltime(*args, **kwargs)


def naturaldelta(*args, **kwargs):

    with django_language():
        return humanize_time.naturaldelta(*args, **kwargs)


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

    return pytime.strftime('%Y-%m-%d %H:%M')


class benchmark(object):
    """http://dabeaz.blogspot.fr/2010/02/context-manager-for-timing-benchmarks.html """ # NOQA

    def __init__(self, name=None):
        self.name = name or u'Generic benchmark'

    def __enter__(self):
        self.start   = pytime.time()
        self.dtstart = stats_datetime()

    def __exit__(self, ty, val, tb):
        LOGGER.info("%s started %s, ran in %s.", self.name, self.dtstart,
                    naturaldelta(pytime.time() - self.start))
        return False


__all__ = ('today', 'timedelta', 'naturaltime', 'naturaldelta',
           'now', 'ftstamp', 'tzcombine', 'combine', 'time', 'datetime',
           'is_aware', 'is_naive',
           'until_tomorrow_delta', 'stats_datetime', 'benchmark',
           'pytime', 'pydatetime')
