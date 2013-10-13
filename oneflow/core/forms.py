# -*- coding: utf-8 -*-

import logging

from django import forms
from django.forms import TextInput
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth import get_user_model

from mongodbforms import DocumentForm

from django_select2.widgets import Select2Widget, Select2MultipleWidget

from .models import (HomePreferences, ReadPreferences,
                     SelectorPreferences, StaffPreferences,
                     Folder, Subscription)

LOGGER = logging.getLogger(__name__)
User = get_user_model()


class FullUserCreationForm(forms.ModelForm):
    """ Like the django UserCreationForm,
        with optional first_name and last_name,
        and email too.

        .. note:: the ``username`` field from Django's ``UserCreationForm``
            is overriden by our Model's one. Thus the 30 chars limit
            doesn't apply.
    """

    error_messages = {
        'password_mismatch': _("The two password fields didn't match."),
    }

    email = forms.EmailField()
    password1 = forms.CharField(label=_("Password"),
                                widget=forms.PasswordInput)
    password2 = forms.CharField(label=_("Password confirmation"),
                                widget=forms.PasswordInput,
                                help_text=_("Enter the same password as "
                                            "above, for verification."))

    class Meta:
        model  = User
        fields = ['first_name', 'last_name',
                  'username', 'email',
                  'password1', 'password2', ]

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError(
                self.error_messages['password_mismatch'])
        return password2

    def save(self, commit=True):
        user = super(FullUserCreationForm, self).save(commit=False)

        user.set_password(self.cleaned_data["password1"])
        user.email      = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"]
        user.last_name  = self.cleaned_data["last_name"]

        if commit:
            user.save()

        return user


class UserProfileEditForm(forms.ModelForm):

    class Meta:
        model  = User
        fields = ['first_name', 'last_name', ]


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


class OnlyNameChoiceField(forms.ModelChoiceField):
    """ In forms, we need something much simpler
        than the `__unicode__()` output. """

    def label_from_instance(self, obj):

        root = obj.owner.root_folder

        # OMG. Please don't do this anywhere else. How ugly it is.
        if obj.parent == root:
            prefix = u''
        elif obj.parent.parent == root:
            prefix = u' ' * 8
        elif obj.parent.parent.parent == root:
            prefix = u' ' * 16
        elif obj.parent.parent.parent.parent == root:
            prefix = u' ' * 24
        elif obj.parent.parent.parent.parent.parent == root:
            prefix = u' ' * 32
        elif obj.parent.parent.parent.parent.parent.parent == root:
            prefix = u' ' * 40
        elif obj.parent.parent.parent.parent.parent.parent.parent == root:
            prefix = u' ' * 48
        else:
            prefix = u' ' * 56

        return prefix + obj.name


class OnlyNameMultipleChoiceField(forms.ModelMultipleChoiceField):
    """ In forms, we need something much simpler
        than the `__unicode__()` output. """

    def label_from_instance(self, obj):

        try:
            root = obj.owner.root_folder

        except AttributeError:
            return obj.name

        # OMG. Please don't do this anywhere else. How ugly it is.
        if obj.parent == root:
            prefix = u''
        elif obj.parent.parent == root:
            prefix = u' ' * 8
        elif obj.parent.parent.parent == root:
            prefix = u' ' * 16
        elif obj.parent.parent.parent.parent == root:
            prefix = u' ' * 24
        elif obj.parent.parent.parent.parent.parent == root:
            prefix = u' ' * 32
        elif obj.parent.parent.parent.parent.parent.parent == root:
            prefix = u' ' * 40
        elif obj.parent.parent.parent.parent.parent.parent.parent == root:
            prefix = u' ' * 48
        else:
            prefix = u' ' * 56

        return prefix + obj.name


class ManageFolderForm(DocumentForm):
    parent = OnlyNameChoiceField(queryset=Folder.objects.all(),
                                 empty_label=_(u'(None)'),
                                 required=False, widget=Select2Widget())

    subscriptions = OnlyNameMultipleChoiceField(
        queryset=Subscription.objects.none(), required=False,
        widget=Select2MultipleWidget())

    class Meta:
        model = Folder
        fields = ('name', 'parent', )
        widgets = {
            'name': TextInput(),
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
            'name': TextInput(),
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

        # Handle `folders` manually, because it's not in form.fields.
        if subscription.user.preferences.selector.subscriptions_in_multiple_folders: # NOQA
            subscription.folders = self.cleaned_data['folders']

        else:
            # Avoid the 'folders : Saisissez une liste de valeurs.' error.
            # in "one folder only", we used a "select" widget which didn't
            # built a list. We need to reconstruct it for the save() to work.
            subscription.folders = [self.cleaned_data['folders']]

        if commit:
            subscription.save()

        return subscription
