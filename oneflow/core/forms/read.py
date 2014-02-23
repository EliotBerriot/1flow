# -*- coding: utf-8 -*-
"""
    Copyright 2013-2014 Olivier Cortès <oc@1flow.io>

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

from django import forms
from django.core.urlresolvers import reverse_lazy
from django.utils.translation import ugettext_lazy as _

from django_select2.widgets import HeavySelect2TagWidget

#from ..models import User
from .fields import UsersMultipleAndTagField


LOGGER = logging.getLogger(__name__)


class ReadShareForm(forms.Form):

    message = forms.CharField(label=_(u'Message'), required=False,
                              help_text=_(u'Type any text you want, in '
                                          u'<a href="#share-read-fields-help" '
                                          u'role="button" data-toggle="'
                                          u'submodal" data-target="#">simple '
                                          u'text <i class="icon-question-sign">'
                                          u'</i></a>.'))

    def __init__(self, *args, **kwargs):

        self.sharer = kwargs.pop('user')

        self.default_placeholder = \
            self.sharer.preferences.share.default_message or \
            _(u'Hi {{fullname}},\n\n'
              u'Here is the item “{{title}}”, you may find it interesting.\n'
              u'Read it on 1flow:\n\n'
              u'{{link}}\n\n'
              u'Cheers,\n'
              u'--\n{0}').format(self.sharer.get_full_name())

        super(ReadShareForm, self).__init__(*args, **kwargs)

        self.fields['recipients'] = UsersMultipleAndTagField(
            owner=self.sharer, label=_(u'Share with'),
            widget=HeavySelect2TagWidget(
                data_url=reverse_lazy('user_address_book')),
            required=True, help_text=_(u'Type to auto-complete, or separate '
                                       u'new email addresses with commas.'))

        self.fields['message'].widget = forms.Textarea(
            attrs={'data-placeholder': self.default_placeholder})

    def clean_message(self):

        # TODO: test formating the message
        # to avoid `.format()` errors afterwise.

        message = self.cleaned_data['message']

        try:
            message.format(**{
                'username': u'DUMMY',
                'fullname': u'DUMMY',
                'firstname': u'DUMMY',
                'lastname': u'DUMMY',
                'link': u'DUMMY',
                'title': u'DUMMY',
            })

        except Exception, e:
            raise forms.ValidationError(
                _(u'Your message does not validate. '
                  u'Please check for missing brackets or '
                  u'typos in fields names; raw error: %s.') % e)

        return message

    def save(self):

        # No need, it's not a ModelForm…
        #super(ReadShareForm, self).save(commit=False)

        message = self.cleaned_data['message']

        if message != self.sharer.preferences.share.default_message:
            self.sharer.preferences.share.default_message = message
            self.sharer.preferences.save()

        return message, self.cleaned_data['recipients']
