# Generated by Django 3.2rc1 on 2021-08-18 02:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("django_dbq", "0003_auto_20180713_1000"),
    ]

    operations = [
        migrations.AlterField(
            model_name="job",
            name="state",
            field=models.CharField(
                choices=[
                    ("NEW", "New"),
                    ("READY", "Ready"),
                    ("PROCESSING", "Processing"),
                    ("FAILED", "Failed"),
                    ("COMPLETE", "Complete"),
                ],
                db_index=True,
                default="NEW",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="job",
            name="workspace",
            field=models.JSONField(null=True),
        ),
    ]
