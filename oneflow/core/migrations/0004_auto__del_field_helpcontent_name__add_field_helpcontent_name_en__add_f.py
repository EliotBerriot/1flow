# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'HelpContent.name_en'
        db.rename_column(u'core_helpcontent', 'name', 'name_en')

        # Adding field 'HelpContent.name_fr'
        db.add_column(u'core_helpcontent', 'name_fr',
                      self.gf('django.db.models.fields.CharField')(max_length=128, unique=True, null=True, blank=True),
                      keep_default=False)

        # Adding field 'HelpContent.name_nt'
        db.add_column(u'core_helpcontent', 'name_nt',
                      self.gf('django.db.models.fields.CharField')(max_length=128, unique=True, null=True, blank=True),
                      keep_default=False)

    def backwards(self, orm):

        db.rename_column(u'core_helpcontent', 'name_en', 'name')

        # Deleting field 'HelpContent.name_fr'
        db.delete_column(u'core_helpcontent', 'name_fr')

        # Deleting field 'HelpContent.name_nt'
        db.delete_column(u'core_helpcontent', 'name_nt')

    models = {
        'core.helpcontent': {
            'Meta': {'ordering': "['ordering', 'id']", 'object_name': 'HelpContent'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'content_en': ('django.db.models.fields.TextField', [], {}),
            'content_fr': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'content_nt': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name_en': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '128'}),
            'name_fr': ('django.db.models.fields.CharField', [], {'max_length': '128', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'name_nt': ('django.db.models.fields.CharField', [], {'max_length': '128', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'ordering': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        }
    }

    complete_apps = ['core']
