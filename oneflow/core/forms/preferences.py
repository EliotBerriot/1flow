# -*- coding: utf-8 -*-

import logging

from mongodbforms import DocumentForm

from ..models import (HomePreferences, ReadPreferences,
                      SelectorPreferences, StaffPreferences)

LOGGER = logging.getLogger(__name__)


class HomePreferencesForm(DocumentForm):

    class Meta:
        model = HomePreferences

        # Other fields are not yet ready
        exclude = ('style', )


class ReadPreferencesForm(DocumentForm):

    class Meta:
        model = ReadPreferences


class SelectorPreferencesForm(DocumentForm):

    class Meta:
        model = SelectorPreferences


class StaffPreferencesForm(DocumentForm):

    class Meta:
        model = StaffPreferences
