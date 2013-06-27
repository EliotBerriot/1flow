# -*- coding: utf-8 -*-

import datetime

from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'LandingUser'
        db.create_table(u'landing_landinguser', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('email_announcements', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('last_modified', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('register_data', self.gf('jsonfield.fields.JSONField')(default={}, blank=True)),
            ('hash_codes', self.gf('jsonfield.fields.JSONField')(default={}, blank=True)),
            ('sent_emails', self.gf('jsonfield.fields.JSONField')(default={}, blank=True)),
            ('data', self.gf('jsonfield.fields.JSONField')(default={}, blank=True)),
            ('email', self.gf('django.db.models.fields.EmailField')(max_length=254)),
            ('date_joined', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
        ))
        db.send_create_signal(u'landing', ['LandingUser'])

    def backwards(self, orm):
        # Deleting model 'LandingUser'
        db.delete_table(u'landing_landinguser')


    models = {
        u'landing.landingcontent': {
            'Meta': {'object_name': 'LandingContent'},
            'content_en': ('django.db.models.fields.TextField', [], {}),
            'content_fr': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'content_nt': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '128'})
        },
        u'landing.landinguser': {
            'Meta': {'object_name': 'LandingUser'},
            'data': ('jsonfield.fields.JSONField', [], {'default': '{}', 'blank': 'True'}),
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '254'}),
            'email_announcements': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'hash_codes': ('jsonfield.fields.JSONField', [], {'default': '{}', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'register_data': ('jsonfield.fields.JSONField', [], {'default': '{}', 'blank': 'True'}),
            'sent_emails': ('jsonfield.fields.JSONField', [], {'default': '{}', 'blank': 'True'})
        }
    }

    complete_apps = ['landing']
