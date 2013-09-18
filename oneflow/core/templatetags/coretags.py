# *-* coding: utf-8 -*-

import logging

from django import template
from django.core.urlresolvers import reverse

LOGGER = logging.getLogger(__name__)

register = template.Library()


@register.simple_tag()
def read_status_css(read):

    css = []

    css.append('is_read' if read.is_read else 'not_is_read')
    css.append('is_starred' if read.is_starred else 'not_is_starred')
    css.append('is_bookmarked' if read.is_bookmarked else 'not_is_bookmarked')

    return u' '.join(css)


@register.simple_tag()
def read_data_urls(read):

    return u'\n'.join(u'data-url-action-{0}={1}'.format(key, reverse('toggle',
                      kwargs={'klass': 'Read', 'oid': read.id , 'key': key}))
                      for key in ('is_read', 'is_starred', 'is_bookmarked'))
