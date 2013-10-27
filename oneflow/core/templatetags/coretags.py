# *-* coding: utf-8 -*-

import re
import logging
import difflib

from math import pow

from constance import config
from markdown_deux import markdown

from django import template
from django.conf import settings
from django.core.urlresolvers import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _


from ...base.utils.dateutils import now, naturaldelta as onef_naturaldelta

from ..models.nonrel import Read, CONTENT_TYPE_MARKDOWN

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

    # Original f & g, not used because grey means "disabled"
    # and G is not visible enough when opacity < 1.
    #
    #    u'f': ((185, 185, 185), u'rgba(185, 185, 185, 1)', u'light-gray'),
    #    u'g': ((235, 235, 222), u'rgba(235, 235, 222, 1)', u'off-white'),
    #
    # Instead, we use w & y colors, which are the most near on the graph.

    u'f': ((255, 152, 213), u'rgba(255, 152, 213, 1)', u'pink'),
    u'g': ((175, 200, 74), u'rgba(175, 200, 74, 1)', u'olive-green'),
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

reading_lists = {

    'web_import': (_(u'Imported elements'),
                   #tooltip_both,
                   _(u'You have {0} newly imported items.'),
                   #tooltip_unread
                   _(u'You have {0} newly imported items, out of {1} so far'),
                   #tooltip_all,
                   _(u'You imported {0} web items so far'),
                   #tooltip_none
                   _(u'You did not import anything until now'),
                   ),

    'read_all':         (_(u'All articles'),
                         _(u'You have {0} articles in 1flow'),
                         'all_articles_count'),
    'read':             (_(u"All unread"),
                         _(u'You have {0} unread articles'),
                         'unread_articles_count'),
    'read_later':       (_(u"Read later"),
                         _(u'You have {0} articles to read later'),
                         'bookmarked_articles_count'),
    'read_starred':     (_(u'Starred'),
                         _(u'You have {0} starred articles'),
                         'starred_articles_count'),

    'read_fun':         (_(u'Funbox'),
                         _(u'You have {0} fun articles'),
                         'fun_articles_count'),

    'read_facts':       (_(u'Facts'),
                         _(u'You have {0} articles marked as fact(s)'),
                         'fact_articles_count'),
    'read_numbers':     (_(u'Numbers'),
                         _(u'You have {0} articles marked as number(s)'),
                         'number_articles_count'),
    'read_analysis':    (_(u'Analysis'),
                         _(u'You have {0} articles marked as analysis'),
                         'analysis_articles_count'),
    'read_prospective': (_(u'Prospective'),
                         _(u'You have {0} articles marked as prospective'),
                         'prospective_articles_count'),
    'read_know_how':    (_(u'Best-practices'),
                         _(u'You have {0} articles marked as best-practices'),
                         'knowhow_articles_count'),
    'read_rules':       (_(u'Regulations'),
                         _(u'You have {0} articles marked as regulation/legal'),
                         'rules_articles_count'),
    'read_quotes':      (_(u'Quotes'),
                         _(u'You have {0} articles marked as quote(s)'),
                         'quote_articles_count'),
    'read_knowledge':   (_(u'Knowledge'),
                         _(u'You have {0} articles marked as knowledge'),
                         'knowledge_articles_count'),
}


@register.simple_tag
def reading_list_with_count(user, view_name, show_unreads=False,
                            css_classes=None):

    list_name, tooltip, count_attr_name = reading_lists[view_name]

    if user.preferences.selector.lists_show_unread_count:
        count_span = u'&nbsp; <small class="unread-count">({0})</small>'
    else:
        count_span = u''

    count = getattr(user, count_attr_name)

    if show_unreads and count:
        has_unread_start = u'<span class="has-unread">'
        has_unread_end   = u'</span>'

    else:
        has_unread_start = u''
        has_unread_end   = u''

    return mark_safe(
        (
            u'{5}<a href="{0}" class="{1} name" title="{2}" '
            u'data-toggle="tooltip">{3}{4}</a>{6}'
        ).format(
            reverse(view_name), css_classes or u'nowrap',
            tooltip.format(count), list_name, count_span.format(count),
            has_unread_start, has_unread_end
        )
    )


@register.simple_tag
def special_subscription_list_with_count(user, special_name, css_classes=None):

    list_name, tooltip_both, tooltip_unread, tooltip_all, tooltip_none = \
                                            reading_lists[special_name]

    subscription = getattr(user, special_name + u'_subscription')
    all_count    = subscription.all_articles_count
    unread_count = subscription.unread_articles_count

    count_span = u''
    make_span  = False

    if unread_count and unread_count == all_count:
        tooltip   = tooltip_both.format(unread_count, all_count)
        make_span = True

    elif unread_count:
        tooltip   = tooltip_unread.format(unread_count, all_count)
        make_span = True

    elif all_count:
        tooltip = tooltip_all.format(all_count)

    else:
        tooltip = _(u'You have nothing in this list yet.')

    if make_span and user.preferences.selector.lists_show_unread_count:
        count_span = (u'&nbsp; <small class="unread-count">'
                      u'({0})</small>'.format(unread_count))

    if unread_count:
        has_unread_start = u'<span class="has-unread">'
        has_unread_end   = u'</span>'

    else:
        has_unread_start = u''
        has_unread_end   = u''

    return mark_safe(
        (
            u'{5}<a href="{0}" class="{1} name" title="{2}" '
            u'data-toggle="tooltip">{3}{4}</a>{6}'
        ).format(
            reverse('read_all_feed', kwargs={'feed': subscription.id}),
            css_classes or u'nowrap', tooltip, list_name, count_span,
            has_unread_start, has_unread_end
        )
    )


@register.simple_tag
def feed_reading_list_with_count(view_name, subscription, attrname,
                                 translation, css_classes=None,
                                 always_show=False):

    # u'<a href="{0}" class="{1} {2} async-get" data-async-get="count">{3}'
    # u'<span class="count"></span></a>'

    count = getattr(subscription, attrname + '_articles_count')

    if always_show or count > 0:
        count_as_digits = unicode(count)

        small_class = u''
        add_title   = False

        if len(count_as_digits) > 6:
            small_class     = u'small'
            count_as_digits = count_as_digits[0] + unicode(_(u'M+'))
            add_title       = True

        elif len(count_as_digits) > 3:
            small_class     = u'small'
            count_as_digits = count_as_digits[0] + unicode(_(u'k+'))
            add_title       = True

        elif len(count_as_digits) > 2:
            small_class = u'small'

        return mark_safe((
            u'<a href="{url}" class="{class1} {class2}" {title}>{trans}'
            u'&nbsp;<span class="unread-count count muted {small}">'
            u'({count})</span></a>'
        ).format(
            url=reverse(view_name, kwargs={'feed': subscription.id}),
            class1=view_name,
            class2=css_classes or u'nowrap',
            title=(u'title="%s" data-toggle="tooltip"' %
                   _(u'{0} articles').format(count))
                    if add_title else u'',
            trans=translation,
            small=small_class,
            count=count_as_digits))

    return u''


@register.simple_tag
def read_action_toggle_url(read):

    any_key = Read.get_status_attributes()[0]
    url_base = reverse('toggle', kwargs={'klass': 'Read',
                       'oid': read.id, 'key': any_key}).replace(
                        any_key, u'@@KEY@@')

    return u'data-url-action-toggle={0}'.format(url_base)


def article_full_content_display(article):

    if article.content_type == CONTENT_TYPE_MARKDOWN:

        if len(article.content) > config.READ_ARTICLE_MIN_LENGTH:

            # START temporary measure.
            # TODO: please get rid of this…

            title_len = len(article.title)

            transient_content = article.content

            if title_len > 10:
                search_len = title_len * 2

                diff = difflib.SequenceMatcher(None,
                                               article.content[:search_len],
                                               article.title)

                if diff.ratio() > 0.51:
                    for blk in reversed(diff.matching_blocks):
                        # Sometimes, last match is the empty string… Skip it.
                        if blk[-1] != 0:
                            transient_content = article.content[
                                                        blk[0] + blk[2]:]
                            break

            # END temporary measure.

            try:
                return markdown(transient_content)

            except Exception:
                LOGGER.exception(u'Live Markdown to HTML conversion '
                                 u'failed for article %s', article)
                return None


def article_excerpt_content_display(article):

    excerpt = article.excerpt

    if excerpt:
        if len(excerpt) > config.READ_ARTICLE_MIN_LENGTH:
            # HTML content…
            # if re.search(r'<[^>]+>', excerpt):

            return excerpt

            # try:
            #     return markdown(excerpt)
            # except Exception:
            #     LOGGER.exception(u'Live Markdown to HTML conversion '
            #                      u'failed for article %s', article)
            #     return None

    #
    # Now, if we don't have any excerpt, just cut down the content a lot
    # to be sure WE are not cut down by repressive laws from another age.
    #

    if article.content_type == CONTENT_TYPE_MARKDOWN:

        try:
            # Save it for next time / user to cool CPU usage.    save=True
            return article.make_excerpt()

        except Exception:
            LOGGER.exception(u'Live Markdown to HTML conversion '
                             u'failed for article %s', article)
            return None


@register.inclusion_tag('snippets/read/read-content.html', takes_context=True)
def read_content(context, read, django_user):

    user_prefs = read.user.preferences

    if django_user.is_superuser and user_prefs.staff.super_powers_enabled:
        content = article_full_content_display(read.article)
        excerpt = False

    else:
        content = article_excerpt_content_display(read.article)
        excerpt = True

    return {
        # Make these up, because the context is not forwarded
        # to the final template. And that's a Django feature.
        # http://stackoverflow.com/q/5842538/654755
        'article_url': read.article.url,
        'STATIC_URL': settings.STATIC_URL,

        # We don't mark_safe() here, else mark_safe(None) outputs "None"
        # in the templates, and "if content" tests fail because content
        # is "None" instead of plain `None`.
        'content': content,
        'excerpt': excerpt
    }


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

    try:
        # Try to get the capitalized letters to make a nice name.
        capitalized = ''.join(c for c in name if c.isupper() or c.isdigit())

    except:
        # If that fails, just start with the full name.
        cleaned = html_letters_re.sub(u'', name)

    else:
        caplen = len(capitalized)

        # If it succeeded, make sure we have enough letters
        if caplen > 0:

            # If we don't have enough letters, take
            # what's left after the last capital.
            if caplen < number:
                capitalized += name[name.index(capitalized[-1]) + 1:]

            cleaned = html_letters_re.sub(u'', capitalized)

        else:
            cleaned = html_letters_re.sub(u'', name)

    if len(cleaned) == 0:
        number = 3
        cleaned   = u';-)'

    if number > len(cleaned):
        number = 1

    try:
        return cleaned[:number].title()

    except:
        # OMG… Unicode characters everywhere…
        return cleaned[:number]


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
