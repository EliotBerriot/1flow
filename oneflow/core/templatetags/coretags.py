# *-* coding: utf-8 -*-

import logging

from django import template
from django.core.urlresolvers import reverse
#from django.utils.translation import ugettext_lazy as _

from ..models.nonrel import Read

LOGGER = logging.getLogger(__name__)

register = template.Library()


@register.simple_tag()
def read_status_css(read):

    css = []

    for attr in Read.get_status_attributes():
        css.append(attr if getattr(read, attr) else (u'not_'+attr))

    return u' '.join(css)


@register.simple_tag()
def read_data_urls(read):

    rid = read.id

    return u'\n'.join(u'data-url-action-{0}={1}'.format(key, reverse('toggle',
                      kwargs={'klass': 'Read', 'oid': rid, 'key': key}))
                      for key in Read.get_status_attributes())


@register.inclusion_tag('snippets/read/read-action.html')
def read_action(read, action_name, with_text=True):

    action_value = getattr(read, action_name)

    return {
        'action_name': action_name,
        'action_data' : Read.status_data.get(action_name),
        'popover_class': '' if with_text else 'popover-tooltip',
        'do_start_hidden' : 'hide' if action_value else '',
        'undo_start_hidden' : '' if action_value else 'hide',
        'js_func': "toggle_status('{0}', '{1}')".format(
                   read.id, action_name)

    }


@register.inclusion_tag('snippets/read/read-action-status.html')
def read_action_status(read, action_name):

    return {
        'action_name': action_name,
        'action_data' : Read.status_data.get(action_name),
        'status_hidden' : '' if getattr(read, action_name) else 'hide',
    }
