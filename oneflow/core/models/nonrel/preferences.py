# -*- coding: utf-8 -*-

from mongoengine import Document, EmbeddedDocument
from mongoengine.fields import (IntField, BooleanField, StringField,
                                EmbeddedDocumentField)

from django.utils.translation import ugettext_lazy as _

from common import DocumentHelperMixin

# •••••••••••••••••••••••••••••••••••••••••••••••••••••••••••• User preferences


class SnapPreferences(Document, DocumentHelperMixin):
    select_paragraph = BooleanField(verbose_name=_(u'Select whole paragraph '
                                    u'on click'), default=False)
    default_public = BooleanField(verbose_name=_(u'Grows public by default'),
                                  default=True)


class NotificationPreferences(EmbeddedDocument):
    """ Email and other web notifications preferences. """
    pass


AUTO_MARK_READ_DELAY_CHOICES = (
    (150, _(u'Immediately')),
    (1000, _(u'After one second')),
    (2000, _(u'After two seconds')),
    (4500, _(u'After 4.5 seconds (default)')),
    (10000, _(u'After 10 seconds')),
    (30000, _(u'After 30 seconds')),
    (-1, _(u'Never (do not auto mark as read)')),
)


class ReadPreferences(EmbeddedDocument):
    """ Reading list preferences. """

    starred_marks_read = BooleanField(
        verbose_name=_(u'Star marks read'),
        help_text=_(u'When you mark an article starred, this will '
                    u'automatically mark it as read (default: true).'),
        default=True)

    starred_removes_bookmarked = BooleanField(
        verbose_name=_(u'Star unmarks “read later”'),
        help_text=_(u'When you mark an article starred, this will '
                    u'automatically remove it from the “read later” '
                    u'list. (default: true).'), default=True)

    bookmarked_marks_unread = BooleanField(
        verbose_name=_(u'Reading later marks unread'),
        help_text=_(u'Marking an article to read later marks it as unread '
                    u'(default: true).'), default=True)

    auto_mark_read_delay = IntField(
        verbose_name=_(u'Auto mark-read delay'),
        help_text=_(u'The delay after which an open article in any reading '
                    u'list will be automatically marked as read if it is not.'),
                    default=4500, choices=AUTO_MARK_READ_DELAY_CHOICES)

    read_switches_to_fullscreen = BooleanField(
        verbose_name=_(u'Switch to full-screen while reading'),
        help_text=_(u'Automatically hide navigation bars when opening an '
                    u'article for reading (default: false).<br />'
                    u'When enabled, fullscreen will remain active while you '
                    u'switch from one open article to another. Navigation bars '
                    u'will reappear when you close the current opened article '
                    u'without opening a new one (eg. when you return to the '
                    u'list view).<br />'
                    u'Whatever this setting, you can always show or hide '
                    u'navbars manually with the `shift`+`f` keyboard '
                    u'shortcut.'), default=False)

    show_bottom_navbar = BooleanField(
        verbose_name=_(u'Show the bottom “jump to” navbar'),
        help_text=_(u'When you are in any reading list, either reading '
                    u'articles or just scrolling the list, you can have '
                    u'a navigation bar at the bottom of the screen, allowing '
                    u'you to quickly jump to other reading lists, or back to '
                    u'the sources selector.<br />'
                    u'<span class="muted">Default is not to show this '
                    u'navigation bar.</span>'), default=False)


class SelectorPreferences(EmbeddedDocument):
    """ Source selector preferences. """

    titles_show_unread_count = BooleanField(
        verbose_name=_(u'Feed names show unread count'),
        help_text=_(u'Activate this if you want to see the articles '
                    u'unread count in parenthesis near the feed titles.'),
        default=False)

    folders_show_unread_count = BooleanField(
        verbose_name=_(u'Folders show unread count'),
        help_text=_(u'Each folder is appended the sum of unread articles '
                    u'of each of its subfolders and subscriptions.'),
        default=False)

    show_closed_streams = BooleanField(
        verbose_name=_(u'Show closed streams'),
        help_text=_(u'Display streams that have been closed by the system '
                    u'but to which you are still subscribed. As there will '
                    u'never be new content in them, it is safe to hide them '
                    u'in the selector. Unread articles from closed streams '
                    u'still show in the unread list.'),
                    # TODO: use reverse_lazy('read') and make a link.
                    # 20131004: it just crashes because of a circular
                    # import loop in mongoadmin, to change.
        default=False)


class StaffPreferences(EmbeddedDocument):
    """ Preferences for staff members / super users. """

    super_powers_enabled = BooleanField(
        verbose_name=_(u'Super powers enabled'),
        help_text=_(u'Globaly enable or not every bit of staff/superuser '
                    u'features in the 1flow interface. If disabled, only the '
                    u'<strong>MAINTENANCE_MODE</strong> label in the navbar '
                    u'will visible, and this preference pane to be able to '
                    u're-enable the features once deactivated.<br />'
                    u'<span class="muted">Default: enabled.</span>'),
        default=True)

    reading_lists_show_bad_articles = BooleanField(
        verbose_name=_(u'Show duplicates, orphaned and other transient data'),
        help_text=_(u'<strong>Warning</strong>: this breaks keyboard shortcut '
                    u'navigation whenever the first bad article is '
                    u'encountered.<br />'
                    u'<span class="muted">Default: disabled.</span>'),
        default=False)

    selector_shows_admin_links = BooleanField(
        verbose_name=_(u'Selector shows admin links'),
        help_text=_(u'Automatically link to the admin from the selector '
                    u'whenever folder/subscription has missing data.<br />'
                    u'<span class="muted">Default: enabled.</span>'),
        default=True)


HOME_STYLE_CHOICES = (
    (u'RL', _(u'Reading list')),
    (u'TL', _(u'Tiled News')),
    (u'T1', _(u'Tiled experiment #1')),
    (u'DB', _(u'Dashboard')),
)


READ_SHOWS_CHOICES = (
    (1, _(u'Unread articles')),
    (2, _(u'Source selector')),
)


class HomePreferences(EmbeddedDocument):
    """ Various HOME settings. """

    style_templates = {
        u'RL': 'snippets/read/read-list-item.html',
        u'TL': 'snippets/read/read-tiles-tile.html',
        u'T1': 'snippets/read/read-tiles-experimental-tile.html',
    }
    style = StringField(verbose_name=_(u'How the user wants his 1flow '
                        u'home to appear'), max_length=2,
                        choices=HOME_STYLE_CHOICES, default=u'RL')

    read_shows = IntField(verbose_name=_(u'Clicking <code>Read</code> '
                          u'displays:'),
                          choices=READ_SHOWS_CHOICES, default=2,
                          help_text=_(u'Define what 1flow will display when '
                                      u'you click on the <code>Read</code> '
                                      u'link in the top navbar of the '
                                      u'interface. <br />'
                                      u'<span class="muted">Default: shows '
                                      u'the <strong>sources '
                                      u'selector</strong>.</span>'))

    def get_template(self):
        return HomePreferences.style_templates.get(self.style)


class HelpWizards(EmbeddedDocument):
    """ Stores if the user viewed the wizards / assistants or not.
        Special attribute is :attr:`show_all` via which the user
        can avoid them to be showed complely or not.
    """
    show_all     = BooleanField(default=True)
    welcome_beta = BooleanField(default=False)


class Preferences(Document, DocumentHelperMixin):
    snap         = EmbeddedDocumentField(u'SnapPreferences',
                                         default=SnapPreferences)
    notification = EmbeddedDocumentField(u'NotificationPreferences',
                                         default=NotificationPreferences)
    home         = EmbeddedDocumentField(u'HomePreferences',
                                         default=HomePreferences)
    read         = EmbeddedDocumentField(u'ReadPreferences',
                                         default=ReadPreferences)
    selector     = EmbeddedDocumentField(u'SelectorPreferences',
                                         default=SelectorPreferences)
    wizards      = EmbeddedDocumentField(u'HelpWizards',
                                         default=HelpWizards)
    staff        = EmbeddedDocumentField(u'StaffPreferences',
                                         default=StaffPreferences)

    def __unicode__(self):
        return u'Preferences #%s' % self.id
