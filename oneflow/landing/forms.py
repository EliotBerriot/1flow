# -*- coding: utf-8 -*-

from django import forms

from .models import LandingUser


class LandingPageForm(forms.ModelForm):

    class Meta:
        model  = LandingUser
        fields = ('email', )
