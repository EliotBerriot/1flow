# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting model 'UserProfile'
        db.delete_table(u'profiles_userprofile')


    def backwards(self, orm):
        # Adding model 'UserProfile'
        db.create_table(u'profiles_userprofile', (
            ('email_announcements', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('register_request_data', self.gf('jsonfield.fields.JSONField')(default={}, blank=True)),
            ('user', self.gf('django.db.models.fields.related.OneToOneField')(related_name='profile', unique=True, primary_key=True, to=orm['base.User'])),
            ('last_modified', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('data', self.gf('jsonfield.fields.JSONField')(default={}, blank=True)),
            ('hash_code', self.gf('django.db.models.fields.CharField')(default='083cfd9d1fcd40968a12bac7a13d9bf2', max_length=32)),
        ))
        db.send_create_signal(u'profiles', ['UserProfile'])


    models = {
        
    }

    complete_apps = ['profiles']