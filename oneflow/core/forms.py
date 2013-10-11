# -*- coding: utf-8 -*-

import logging

from django import forms
from django.forms import TextInput
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth import get_user_model

from mongodbforms import DocumentForm

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


class ManageFolderForm(DocumentForm):
    parent = OnlyNameChoiceField(queryset=Folder.objects.all(),
                                 empty_label=_(u'(None)'),
                                 required=False)

    class Meta:
        model = Folder
        fields = ('name', 'parent', )
        widgets = {
            'name': TextInput(),
        }

    def __init__(self, *args, **kwargs):

        self.folder_owner = kwargs.pop('owner')

        super(ManageFolderForm, self).__init__(*args, **kwargs)

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

        return folder


class ManageSubscriptionForm(DocumentForm):
    folders = OnlyNameMultipleChoiceField(queryset=Folder.objects.all(),
                                          required=False)

    class Meta:
        model = Subscription
        fields = ('name', 'folders', )
        widgets = {
            'name': TextInput(),
        }
