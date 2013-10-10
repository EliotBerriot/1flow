# *-* coding: utf-8 -*-

import re
import logging

from math import pow

from django import template
from django.core.urlresolvers import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _


from ...base.utils.dateutils import now, naturaldelta as onef_naturaldelta

from ..models.nonrel import Read

LOGGER = logging.getLogger(__name__)

register = template.Library()


# http://www.christianfaur.com/color/
# http://www.christianfaur.com/color/Site/Picking%20Colors.html
#
# And then: http://stackoverflow.com/q/3116260/654755
# http://ux.stackexchange.com/q/8297
letters_colors = {
    u'a': ((0, 0, 180), u'rgba(0, 0, 180, 1)', u'blue'),
    u'b': ((175, 13, 102), u'rgba(175, 13, 102, 1)', u'red-violet'),
    u'c': ((146, 248, 70), u'rgba(146, 248, 70, 1)', u'green-yellow'),
    u'd': ((255, 200, 47), u'rgba(255, 200, 47, 1)', u'yellow-orange'),
    u'e': ((255, 118, 0), u'rgba(255, 118, 0, 1)', u'orange'),
    u'f': ((185, 185, 185), u'rgba(185, 185, 185, 1)', u'light-gray'),
    u'g': ((235, 235, 222), u'rgba(235, 235, 222, 1)', u'off-white'),
    u'h': ((100, 100, 100), u'rgba(100, 100, 100, 1)', u'gray'),
    u'i': ((255, 255, 0), u'rgba(255, 255, 0, 1)', u'yellow'),
    u'j': ((55, 19, 112), u'rgba(55, 19, 112, 1)', u'dark-purple'),
    u'k': ((255, 255, 150), u'rgba(255, 255, 150, 1)', u'light-yellow'),
    u'l': ((202, 62, 94), u'rgba(202, 62, 94, 1)', u'dark-pink'),
    u'm': ((205, 145, 63), u'rgba(205, 145, 63, 1)', u'dark-orange'),
    u'n': ((12, 75, 100), u'rgba(12, 75, 100, 1)', u'teal'),
    u'o': ((255, 0, 0), u'rgba(255, 0, 0, 1)', u'red'),
    u'p': ((175, 155, 50), u'rgba(175, 155, 50, 1)', u'dark-yellow'),
    u'q': ((0, 0, 0), u'rgba(0, 0, 0, 1)', u'black'),
    u'r': ((37, 70, 25), u'rgba(37, 70, 25, 1)', u'dark-green'),
    u's': ((121, 33, 135), u'rgba(121, 33, 135, 1)', u'purple'),
    u't': ((83, 140, 208), u'rgba(83, 140, 208, 1)', u'light-blue'),
    u'u': ((0, 154, 37), u'rgba(0, 154, 37, 1)', u'green'),
    u'v': ((178, 220, 205), u'rgba(178, 220, 205, 1)', u'cyan'),
    u'w': ((255, 152, 213), u'rgba(255, 152, 213, 1)', u'pink'),
    u'x': ((0, 0, 74), u'rgba(0, 0, 74, 1)', u'dark blue'),
    u'y': ((175, 200, 74), u'rgba(175, 200, 74, 1)', u'olive-green'),
    u'z': ((63, 25, 12), u'rgba(63, 25, 12, 1)', u'red-brown'),
}

html_letters_re = re.compile(ur'[^\w]', re.UNICODE | re.IGNORECASE)


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


@register.simple_tag
def html_first_letters(name, number=1):

    name = html_letters_re.sub(u'', name)

    if number > len(name):
        number = 1

    try:
        return name[:number].title()

    except:
        # OMG… Unicode characters everywhere…
        return name[:number]


@register.simple_tag
def html_background_color_for_name(name, opacity=1):

    name = html_letters_re.sub(u'', name)

    try:
        letter = name[0].lower()

    except:
        # OMG… Unicode characters everywhere…
        letter = u'a'

    try:
        return letters_colors[letter][1].replace(u', 1)',
                                                 u', {0})'.format(opacity))

    except:
        # Still, some unicode characters can
        # lower() but are not in the table.
        return letters_colors[u'a'][1].replace(u', 1)',
                                               u', {0})'.format(opacity))


@register.simple_tag
def html_foreground_color_for_name(name):
    """ TODO: pre-compute these values for our colors. """

    name = html_letters_re.sub(u'', name)

    try:
        letter = name[0].lower()

    except:
        # OMG… Unicode characters everywhere…
        letter = u'a'

    try:
        R, G, B = letters_colors[letter][0]

    except:
        # Still, some unicode characters can
        # lower() but are not in the table.
        R, G, B = letters_colors[u'a'][0]

    Y = (0.2126 * pow(R / 255, 2.2)
         + 0.7151 * pow(G / 255, 2.2)
         + 0.0721 * pow(B / 255, 2.2))

    return u'white' if Y <= 0.18 else u'black'
