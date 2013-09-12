# -*- coding: utf-8 -*-

import re

from django.template import Library, Node, TemplateSyntaxError
from django.template.base import Node, TemplateSyntaxError
from django.utils.encoding import smart_text
from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse

from sparks.foundations import utils as sfu

register = Library()


@register.simple_tag(takes_context=True)
def reverse_active(context, url, return_value=None):
    """ In the template:

            <!-- returns 'active' if the current path
                            matches the reverse url of "views.name" -->
            class="{% reverse_active "views.name" %}"

            <!-- returns 'my-active' if the current path
                            matches the reverse url of "views.name" -->
            class="{% reverse_active "views.name" "my-active" %}"

        Taken from http://gnuvince.wordpress.com/2007/09/14/a-django-template-tag-for-the-current-active-page/ #NOQA
        and extended a lot to simplify template calls…
    """

    if reverse(url) == context['request'].path:
        return return_value or u'active'

    return u''


@register.simple_tag(takes_context=True)
def active(context, pattern, return_value=None):
    """ Same as reverse active, but for URLs without any views.

        class="{% active request "/help/" "top-menu-element-active" %}"

    """

    if re.search(pattern, context['request'].path):
        return return_value or u'active'

    return u''


class CaptureasNode(Node):
    def __init__(self, nodelist, varname):
        self.nodelist = nodelist
        self.varname  = varname

    def render(self, context):
        output = self.nodelist.render(context)
        context[self.varname] = output
        return ''


class FirstOfAsNode(Node):
    def __init__(self, args, variable_name=None):
        self.vars = args
        self.variable_name = variable_name

    def render(self, context):
        for var in self.vars:
            value = var.resolve(context, True)

            if value:
                if self.variable_name:
                    context[self.variable_name] = value
                    break

                else:
                    return smart_text(value)

        return ''


@register.tag(name='captureas')
def do_captureas(parser, token):
    """ Taken from http://djangosnippets.org/snippets/545/ verbatim. Handy!
        Initial source: https://code.djangoproject.com/ticket/7239
    """

    try:
        tag_name, args = token.contents.split(None, 1)

    except ValueError:
        raise TemplateSyntaxError(
            "'captureas' node requires a variable name.")

    nodelist = parser.parse(('endcaptureas',))
    parser.delete_first_token()

    return CaptureasNode(nodelist, args)


@register.tag
def firstofas(parser, token):
    """ Original idea: https://code.djangoproject.com/ticket/12199 """

    bits = token.split_contents()[1:]
    variable_name = None
    expecting_save_as = bits[-2] == 'as'

    if expecting_save_as:
        variable_name = bits.pop(-1)
        bits = bits[:-1]

    if len(bits) < 1:
        raise TemplateSyntaxError(
            "'firstofas' statement requires at least one argument")

    return FirstOfAsNode([parser.compile_filter(bit) for bit in bits],
                         variable_name)


@register.inclusion_tag('snippets/countdown.html')
def countdown(value, redirect=None, limit=0, show_seconds=True,
              format=None, spacer=None):
    """ From http://www.plus2net.com/javascript_tutorial/countdown.php """

    if redirect is None:
        redirect = '/'

    if limit > 0:
        operation    = '+'
        round_value  = 0
        counter_test = '<='

    else:
        operation    = '-'
        round_value  = 0        # WAS: 2
        counter_test = '>='

    if format is None or format == 'long':
        separator = ', '
        short     = False
        units     = {
            'day': _('day'),
            'days': _('days'),
            'hour': _('hour'),
            'hours': _('hours'),
            'minute': _('minute'),
            'minutes': _('minutes'),
            'second': _('second'),
            'seconds': _('seconds'),
        }

    elif format == 'abbr':
        separator = ' '
        short     = True
        units     = {
            'day': _('day'),
            'days': _('days'),
            'hour': _('hour'),
            'hours': _('hours'),
            'minute': _('min'),
            'minutes': _('mins'),
            'second': _('sec'),
            'seconds': _('secs'),
        }
    elif format == 'short':
        separator = ' '
        short     = True
        units     = {
            'day': _('d'),
            'days': _('d'),
            'hour': _('h'),
            'hours': _('h'),
            'minute': _('m'),
            'minutes': _('m'),
            'second': _('s'),
            'seconds': _('s'),
        }
    else:
        raise TemplateSyntaxError("'countdown' 'format' keyword argument "
                                  "must be either 'short', 'abbr' or 'long'")

    return {
        'name': sfu.unique_hash(only_letters=True),
        'units': units,
        'short': short,
        'value': value,
        'limit': limit,
        'unit_sep': ' ' if spacer is None else spacer,
        'redirect': redirect,
        'operation': operation,
        'separator': separator,
        'round_value': round_value,
        'show_seconds': show_seconds,
        'counter_test': counter_test,
    }


