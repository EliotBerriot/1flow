# -*- coding: utf-8 -*-

from django import forms

from ..base.models import User


class LandingPageForm(forms.ModelForm):

    class Meta:
        model  = User
        fields = ('email', )
