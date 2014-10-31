# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import jsonfield.fields
import uuidfield.fields


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Job',
            fields=[
                ('id', uuidfield.fields.UUIDField(primary_key=True, serialize=False, editable=False, max_length=32, blank=True, unique=True, db_index=True)),
                ('created', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=100)),
                ('state', models.CharField(default=b'NEW', max_length=20, db_index=True, choices=[(b'NEW', b'NEW'), (b'READY', b'READY'), (b'PROCESSING', b'PROCESSING'), (b'FAILED', b'FAILED'), (b'COMPLETE', b'COMPLETE')])),
                ('next_task', models.CharField(max_length=100, blank=True)),
                ('workspace', jsonfield.fields.JSONField(null=True)),
                ('queue_name', models.CharField(default=b'default', max_length=20, db_index=True)),
            ],
            options={
                'ordering': ['-created'],
            },
            bases=(models.Model,),
        ),
    ]
