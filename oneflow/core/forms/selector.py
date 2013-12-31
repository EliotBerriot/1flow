# -*- coding: utf-8 -*-

import logging
import simplejson as json

from dateutil import parser as date_parser

from django import forms
from django.core.urlresolvers import reverse, reverse_lazy

from django.utils.translation import ugettext_lazy as _
from django.core.validators import URLValidator
from django.contrib import messages

from mongodbforms import DocumentForm

from django_select2.widgets import (Select2Widget, Select2MultipleWidget,
                                    HeavySelect2MultipleWidget)

from ..models import (Folder, Subscription, Feed, Article, Read)
from .fields import OnlyNameChoiceField, OnlyNameMultipleChoiceField


LOGGER = logging.getLogger(__name__)


class ManageFolderForm(DocumentForm):
    parent = OnlyNameChoiceField(queryset=Folder.objects.all(),
                                 empty_label=_(u'(None)'),
                                 label=_(u'Parent folder'),
                                 required=False, widget=Select2Widget())

    subscriptions = OnlyNameMultipleChoiceField(
        label=_(u'Subscriptions'), queryset=Subscription.objects.none(),
        required=False, widget=Select2MultipleWidget(),
        help_text=_(u'These are the ones held directly by the folder; they '
                    u'are displayed above subfolders. There can be none, if '
                    u'you prefer dispatching your subscriptions in subfolders '
                    u'only.'))

    class Meta:
        model = Folder
        fields = ('name', 'parent', )
        widgets = {
            'name': forms.TextInput(),
        }

    def __init__(self, *args, **kwargs):

        self.folder_owner = kwargs.pop('owner')

        super(ManageFolderForm, self).__init__(*args, **kwargs)

        folders_tree = self.folder_owner.get_folders_tree(for_parent=True)

        if self.instance.id:
            try:
                folders_tree.remove(self.instance)
            except ValueError:
                pass

            else:
                for f in self.instance.children_tree:
                    try:
                        folders_tree.remove(f)

                    except ValueError:
                        # ValueError: list.remove(x): x not in list
                        # Happens when try to remove a level-N+ folder
                        # from a list limited to level N-1 folder. No
                        # need to continue, folders_tree return a
                        # depth-aware list.
                        break

            try:
                self.fields['subscriptions'].initial = \
                    self.folder_owner.subscriptions_by_folder[self.instance]

            except KeyError:
                # No subscriptions in this folder yet.
                pass

        self.fields['parent'].queryset = folders_tree
        self.fields['subscriptions'].queryset = \
            self.folder_owner.subscriptions.order_by('name')

    def clean_parent(self):

        try:
            parent = self.cleaned_data['parent']

        except:
            return self.folder_owner.root_folder

        if parent is None:
            return self.folder_owner.root_folder

        return parent

    def is_valid(self):

        res = super(ManageFolderForm, self).is_valid()

        if not res:
            return False

        if self.instance.id is None:

            parent_folder = self.cleaned_data['parent']

            try:
                Folder.objects.get(
                    owner=self.folder_owner, name=self.cleaned_data['name'],
                    parent=parent_folder)
            except Folder.DoesNotExist:
                return True

            else:
                if parent_folder == self.folder_owner.root_folder:
                    self._errors['already_exists'] = \
                        _(u'A top folder by that name already exists.')
                else:
                    self._errors['already_exists'] = \
                        _(u'A folder by that name already exists '
                          u'at the same place.')

                return False

        return True

    def save(self, commit=True):

        parent_folder  = self.cleaned_data.get('parent')
        parent_changed = False

        # id == None means creation, else we are editing.
        if self.instance.id:

            # We need to get the previous values; Django doesn't cache
            # them and self.instance is already updated with new values.
            old_folder = Folder.objects.get(id=self.instance.id)

            if old_folder.parent != parent_folder:
                # The form.save() will set the new parent, but
                # will not unset instance from parent.children.
                # We need to take care of this.
                try:
                    old_folder.parent.remove_child(self.instance,
                                                   full_reload=False,
                                                   update_reverse_link=False)
                except AttributeError:
                    # A top folder is becoming a sub-folder. It had no parent.
                    pass
                parent_changed = True

        else:
            # In "add folder" mode, parent has always changed, it's new!
            parent_changed = True

        folder = super(ManageFolderForm, self).save(commit=False)

        if self.instance.id is None:
            folder.owner = self.folder_owner

        if commit:
            folder.save()

        if parent_changed:
            # In edit or create mode, we need to take care of the other
            # direction of the double-linked relation. This will imply
            # a superfluous write in case of an unchanged parent
            parent_folder.add_child(folder, full_reload=False,
                                    update_reverse_link=False)

        self.synchronize_subscriptions_folders(folder)

        return folder

    def synchronize_subscriptions_folders(self, folder):
        """ NOTE: `folder` is just self.instance passed
            through to avoid to look it up again. """

        try:
            initial_subscriptions = \
                self.folder_owner.subscriptions_by_folder[self.instance]

        except KeyError:
            initial_subscriptions = []

        updated_subscriptions = self.cleaned_data['subscriptions']

        for subscription in initial_subscriptions:
            if subscription not in updated_subscriptions:
                subscription.update(pull__folders=folder)

        if self.folder_owner.preferences.selector.subscriptions_in_multiple_folders: # NOQA
            subscr_kwargs = {'add_to_set__folders': folder}

        else:
            subscr_kwargs = {'set__folders': [folder]}

        for subscription in updated_subscriptions:
            # This will update more things than needed, but in the case of
            # a changed preference, this will make the subscription appear
            # in one folder only again.
            # TODO: when the preference has a trigger on save() that do
            # this automatically, uncomment the following line to simply
            # move new subscriptions to this folder, and not touch others.
            #
            # if subscription not in initial_subscriptions:
            subscription.update(**subscr_kwargs)


class ManageSubscriptionForm(DocumentForm):

    class Meta:
        model = Subscription

        # NOTE: as we manage `folders` differently and very specially, given
        # the value of a user preference, we MUST NOT put `folders` here in
        # `fields`, because in one of 2 cases, setting the initial value will
        # not work because of attribute being a list and field being not.
        fields = ('name', )
        widgets = {
            'name': forms.TextInput(),
        }

    def __init__(self, *args, **kwargs):

        super(ManageSubscriptionForm, self).__init__(*args, **kwargs)

        folders_queryset = self.instance.user.folders_tree

        if self.instance.user.preferences.selector.subscriptions_in_multiple_folders: # NOQA
            self.fields['folders'] = OnlyNameMultipleChoiceField(
                queryset=folders_queryset, required=False, label=_(u'Folders'),
                widget=Select2MultipleWidget(), initial=self.instance.folders)
                # no empty_label here.

        else:
            self.fields['folders'] = OnlyNameChoiceField(
                queryset=folders_queryset, required=False,
                widget=Select2Widget(), label=_(u'Folder'),
                empty_label=_(u'(None)'))

            try:
                self.fields['folders'].initial = self.instance.folders[0]

            except IndexError:
                # Subscription is not in any folder yet.
                pass

    def save(self, commit=True):

        subscription = super(ManageSubscriptionForm, self).save(commit=False)
        preferences  = subscription.user.preferences.selector

        # Handle `folders` manually, because it's not in form.fields.
        if preferences.subscriptions_in_multiple_folders:
            if self.cleaned_data['folders']:
                subscription.folders = self.cleaned_data['folders']

        elif self.cleaned_data['folders'] is not None:
            # Avoid the:
            #   - 'folders : Saisissez une liste de valeurs.' error.
            #   - A ReferenceField only accepts DBRef or documents: ['folders']
            #       when nothing is selected, this makes value=[None].
            #
            # In "one folder only", we used a "select" widget which didn't
            # built a list. We need to reconstruct it for the save() to work.
            subscription.folders = [self.cleaned_data['folders']]

        if commit:
            subscription.save()

        return subscription


class AddSubscriptionForm(forms.Form):

    feeds = OnlyNameMultipleChoiceField(queryset=Feed.objects.none(),
                                        required=False,
                                        label=_(u'Search 1flow\'s streams'))

    search_for = forms.CharField(label=_(u'Enter an URL'), required=False)

    def __init__(self, *args, **kwargs):

        self.owner = kwargs.pop('owner')

        super(AddSubscriptionForm, self).__init__(*args, **kwargs)

        # not_shown = [s.feed.id for s in self.owner.subscriptions]
        # LOGGER.warning(len(not_shown))

        # NOTE: this query is replicated in the completer view.
        self.fields['feeds'].queryset = Feed.good_feeds(
            id__nin=[s.feed.id for s in self.owner.subscriptions])

        count = self.fields['feeds'].queryset.count()

        self.fields['feeds'].widget = HeavySelect2MultipleWidget(
                                    data_url=reverse_lazy('feeds_completer'))

        self.fields['feeds'].widget.set_placeholder(
            _(u'Select feed(s) from the {0} referenced').format(count))

        self.fields['search_for'].help_text = _(
            u'<span class="muted">NOTE: this can be long. '
            u'You will be notified when search is done.</span> '
            u'<a href="{0}" target="_blank">How does it work?</a>').format(
                reverse('help') + unicode(_(u'#adding-subscriptions')))

    def is_valid(self):

        res = super(AddSubscriptionForm, self).is_valid()

        if not res:
            return False

        if not self.cleaned_data['feeds'] \
                and not self.cleaned_data['search_for']:
            self._errors['nothing_choosen'] = \
                _(u'You have to fill at least one of the two fields.')
            return False

        return True

    def save(self, commit=True):

        created_subscriptions = []

        selector_prefs = self.owner.preferences.selector

        for feed in self.cleaned_data['feeds']:

            folders = []

            for tag in feed.tags:
                folders.append(Folder.add_folder_from_tag(tag, self.owner))

                if not selector_prefs.subscriptions_in_multiple_folders:
                    # One is enough.
                    break

            subscription = Subscription.subscribe_user_to_feed(self.owner, feed,
                                                               background=True)

            subscription.folders = folders

            if commit:
                subscription.save()

            created_subscriptions.append(subscription)

        return created_subscriptions


class WebPagesImportForm(forms.Form):

    urls = forms.CharField(label=_(u'Web addresses'), required=True,
                           widget=forms.Textarea())

    def __init__(self, *args, **kwargs):

        self.request = kwargs.pop('request', None)
        self.user    = None \
            if self.request is None else self.request.user.mongo

        super(WebPagesImportForm, self).__init__(*args, **kwargs)

    def import_readability(self):

        try:
            readability_json = json.loads(self.cleaned_data['urls'])

        except:
            return False

        try:
            first_object = readability_json[0]

        except:
            return False

        for attr_name in ("article__title", "article__excerpt",
                          "article__url", "date_added",
                          "favorite", "date_favorited",
                          "archive", "date_archived"):
            if attr_name not in first_object:
                return False

        # OK, now we've got a readability import file.
        messages.info(self.request,
                      _(u'Readability JSON export format detected.'))

        for readability_object in readability_json:

            url = readability_object['article__url']

            if self.validate_url(url):
                article = self.import_one_article_from_url(url)

                if article is None:
                    # article was not created, we
                    # already have it in the database.
                    article = Article.objects.get(url=url)

                #
                # Now comes the readability-specific part of the import,
                # eg. get back user meta-data as much as possible in 1flow.
                #

                article_needs_save = False

                if readability_object['article__title']:
                    article.title      = readability_object['article__title']
                    article_needs_save = True

                if readability_object['article__excerpt']:
                    article.excerpt    = readability_object['article__excerpt']
                    article_needs_save = True

                if article_needs_save:
                    article.save()

                read = article.reads.get(
                    subscriptions=self.user.web_import_subscription)

                # About parsing dates:
                # http://stackoverflow.com/q/127803/654755
                # http://stackoverflow.com/a/18150817/654755

                read_needs_save = False

                date_added = readability_object['date_added']

                if date_added:
                    # We try to keep the history of date when the
                    # user added this article to readability.
                    try:
                        read.date_created = date_parser.parse(date_added)

                    except:
                        LOGGER.exception(u'Parsing creation date "%s" for '
                                         u'read #%s failed.', date_added,
                                         read.id)

                    else:
                        read_needs_save = True

                if readability_object['favorite']:
                    read.is_starred = True
                    read_needs_save = True

                    date_favorited = readability_object['date_favorited']

                    if date_favorited:
                        try:
                            read.date_starred = date_parser.parse(
                                                        date_favorited)
                        except:
                            LOGGER.exception(u'Parsing favorited date "%s" '
                                             u'for read #%s failed.',
                                             date_favorited, read.id)

                if read_needs_save:
                    read.save()

    def import_articles_from_urls(self, urls=None):

        if urls is None:
            urls = self.cleaned_data['urls'].splitlines()

        for url in urls:
            self.validate_url(url)

        for url in self.import_to_create:
            self.import_one_article_from_url(url)

    def validate_url(self, url):

        url = url.strip()

        if not url:
            return False

        try:
            self.import_validator(url)

        except Exception, e:
            self.import_failed.append((url, u', '.join(e.messages)))
            return False

        else:
            if url in self.import_to_create:
                return False

            # Avoid stupidity.
            if u'1flow.io/' in url or u'1flow.net/' in url:
                try:
                    #
                    # HACK: if we try to import an article from another
                    # user's page. This is quick and dirty, but sufficient
                    # until we have an auto-clone feature.
                    #

                    # extract a potential read_id from
                    # http://1flow.io/fr/lire/52c2beba84cc1762a69c4c2e/
                    # get it from the end, because matching any reverse_lazy()
                    # is too complicated, given the lang of the 2 users.
                    read_id = url[-26:].split('/', 1)[1].replace('/', '')

                except:
                    return False

                try:
                    Read.objects.get(id=read_id)

                except:
                    return False

                else:
                    return True

            self.import_to_create.add(url)

            return True

    def import_one_article_from_url(self, url):

        try:
            article, created = \
                self.user.web_import_feed.create_article_from_url(url)

        except Exception, e:
            LOGGER.exception(u'Could not create article from '
                             u'imported URL %s', url)
            self.import_failed.append((url, unicode(e)))
            return None

        else:
            # Keep the read accessible over time.
            LOGGER.warning(u'TODO: make sure import_one_article_from_url() has '
                           u'no race condition when marking new read archived.')
            read = Read.objects.get(article=article, user=self.user)
            read.mark_archived()

            # We append "None" if the article was not created but
            # already exists. This is intended, for the view to
            # count them as "correctly imported" to the end-user.
            # If we only append *really* created articles (in our
            # internal DB point-of-view), this will result in:
            #
            #         created + failed != total_imported
            #
            # Which can be very confusing to the end-user, even
            # though everything is really OK in the database and
            # in the reading lists.
            self.import_created.append(article)

            return article

    def save(self):

        self.import_validator = URLValidator()
        self.import_to_create = set()
        self.import_created   = []
        self.import_failed    = []

        if self.import_readability():
            return self.import_created, self.import_failed

        #
        # TODO: insert other importers here.
        #

        self.import_articles_from_urls()

        return self.import_created, self.import_failed
