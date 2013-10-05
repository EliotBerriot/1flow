# *-* coding: utf-8 -*-

import logging

from django import template
from django.core.urlresolvers import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _


from ...base.utils.dateutils import now, naturaldelta as onef_naturaldelta

from ..models.nonrel import Read

LOGGER = logging.getLogger(__name__)

register = template.Library()


@register.filter
def naturaldelta(the_datetime):

    return onef_naturaldelta(now() - the_datetime)


@register.simple_tag
def feature_not_ready():

    return mark_safe(u' title="{0}" data-toggle="tooltip" '.format(
                     _(u'Feature coming soon. More information on the '
                       u'1flow blog http://blog.1flow.io/ or Twitter '
                       u'@1flow_io.')))


@register.simple_tag
def read_status_css(read):

    css = []

    for attr in Read.get_status_attributes():
        css.append(attr if getattr(read, attr) else (u'not_'+attr))

    return u' '.join(css)


@register.simple_tag
def reading_list_with_count(view_name, translation, css_classes=None):

    return mark_safe((
        u'<a href="{0}" class="{1}">{2}'
        u'<span data-async-get="count"></span></a>'
    ).format(
        reverse(view_name), css_classes or u'nowrap', translation))


@register.simple_tag
def feed_reading_list_with_count(view_name, subscription, attrname,
                                 translation, css_classes=None):

    # u'<a href="{0}" class="{1} {2} async-get" data-async-get="count">{3}'
    # u'<span class="count"></span></a>'

    count = getattr(subscription, attrname + '_articles_count')

    if count:
        return mark_safe((
            # last space at end of second line is needed.
            u'<a href="{0}" class="{1} {2}">{3}'
            u'&nbsp;(<span class="count">{4}</span>)</a> '
        ).format(
            reverse(view_name, kwargs={'feed': subscription.id}),
            view_name, css_classes or u'nowrap', translation, count))

    return u''


@register.simple_tag
def read_action_toggle_url(read):

    any_key = Read.get_status_attributes()[0]
    url_base = reverse('toggle', kwargs={'klass': 'Read',
                       'oid': read.id, 'key': any_key}).replace(
                        any_key, u'@@KEY@@')

    return u'data-url-action-toggle={0}'.format(url_base)


@register.inclusion_tag('snippets/read/read-action.html')
def read_action(read, action_name, with_text=True, popover_direction=None):

    action_value = getattr(read, action_name)

    return {
        'with_text': with_text,
        'popover_direction' : popover_direction or 'top',
        'action_name': action_name,
        'action_data' : Read.status_data.get(action_name),
        'popover_class': '' if with_text else 'popover-tooltip',
        'do_start_hidden' : 'hide' if action_value else '',
        'undo_start_hidden' : '' if action_value else 'hide',
        'js_func': "toggle_status('{0}', '{1}')".format(
                   read.id, action_name)

    }


@register.inclusion_tag('snippets/read/read-action-status.html')
def read_action_status(read, action_name, with_text=False):

    return {
        'with_text': with_text,
        'action_name': action_name,
        'action_data' : Read.status_data.get(action_name),
        'status_hidden' : '' if getattr(read, action_name) else 'hide',
    }
