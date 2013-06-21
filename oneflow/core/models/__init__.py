# -*- coding: utf-8 -*-

from sparks.foundations.classes import SimpleObject

from .reldb import * # NOQA
from .nonrel import * # NOQA
from .keyval import * # NOQA

RATINGS = SimpleObject(from_dict={
    'STARRED': 5.0,
    'RETWEET': 10.0,
})
