# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import uuid

from django.db.models import UUIDField


class Migration(migrations.Migration):

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Job",
            fields=[
                (
                    "id",
                    UUIDField(
                        serialize=False,
                        editable=False,
                        default=uuid.uuid4,
                        primary_key=True,
                    ),
                ),
                ("created", models.DateTimeField(db_index=True, auto_now_add=True)),
                ("modified", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=100)),
                (
                    "state",
                    models.CharField(
                        db_index=True,
                        max_length=20,
                        default="NEW",
                        choices=[
                            ("NEW", "NEW"),
                            ("READY", "READY"),
                            ("PROCESSING", "PROCESSING"),
                            ("FAILED", "FAILED"),
                            ("COMPLETE", "COMPLETE"),
                        ],
                    ),
                ),
                ("next_task", models.CharField(max_length=100, blank=True)),
                ("workspace", models.TextField(null=True)),
                (
                    "queue_name",
                    models.CharField(db_index=True, max_length=20, default="default"),
                ),
            ],
            options={
                "ordering": ["-created"],
            },
        ),
    ]
