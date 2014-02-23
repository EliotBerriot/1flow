# -*- coding: utf-8 -*-
"""
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

import redis

from mongoengine.connection import connect, disconnect

from django.conf import settings

TEST_REDIS = redis.StrictRedis(host=settings.REDIS_TEST_HOST,
                               port=settings.REDIS_TEST_PORT,
                               db=settings.REDIS_TEST_DB)


def connect_mongodb_testsuite():
    disconnect()
    connect('{0}_testsuite'.format(settings.MONGODB_NAME),
            tz_aware=settings.USE_TZ)


__all__ = ('TEST_REDIS', 'connect_mongodb_testsuite', )
