# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'LandingContent'
        db.create_table(u'landing_landingcontent', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=128)),
            ('content_en', self.gf('django.db.models.fields.TextField')()),
            ('content_fr', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('content_nt', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'landing', ['LandingContent'])


    def backwards(self, orm):
        # Deleting model 'LandingContent'
        db.delete_table(u'landing_landingcontent')


    models = {
        u'landing.landingcontent': {
            'Meta': {'object_name': 'LandingContent'},
            'content_en': ('django.db.models.fields.TextField', [], {}),
            'content_fr': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'content_nt': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '128'})
        }
    }

    complete_apps = ['landing']