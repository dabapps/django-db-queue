# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Job'
        db.create_table(u'core_job', (
            ('id', self.gf('uuidfield.fields.UUIDField')(unique=True, max_length=32, primary_key=True, db_index=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, db_index=True, blank=True)),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('state', self.gf('django.db.models.fields.CharField')(default='READY', max_length=20, db_index=True)),
            ('next_task', self.gf('django.db.models.fields.CharField')(max_length=100, blank=True)),
            ('workspace', self.gf('jsonfield.fields.JSONField')(null=True)),
        ))
        db.send_create_signal(u'core', ['Job'])


    def backwards(self, orm):
        # Deleting model 'Job'
        db.delete_table(u'core_job')


    models = {
        u'core.job': {
            'Meta': {'ordering': "['-created']", 'object_name': 'Job'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'id': ('uuidfield.fields.UUIDField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True', 'db_index': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'next_task': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'state': ('django.db.models.fields.CharField', [], {'default': "'READY'", 'max_length': '20', 'db_index': 'True'}),
            'workspace': ('jsonfield.fields.JSONField', [], {'null': 'True'})
        }
    }

    complete_apps = ['core']