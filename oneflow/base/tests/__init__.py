# -*- coding: utf-8 -*-

import redis

from mongoengine.connection import connect, disconnect

from django.conf import settings

TEST_REDIS = redis.StrictRedis(host=settings.REDIS_TEST_HOST,
                               port=settings.REDIS_TEST_PORT,
                               db=settings.REDIS_TEST_DB)


def connect_mongodb_testsuite():
    disconnect()
    connect('{0}_testsuite'.format(settings.MONGODB_NAME))


__all__ = ('TEST_REDIS', 'connect_mongodb_testsuite', )
