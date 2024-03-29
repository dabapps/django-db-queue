# Generated by Django 3.2rc1 on 2021-11-29 04:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("django_dbq", "0005_job_run_after"),
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
                    ("STOPPING", "Stopping"),
                    ("FAILED", "Failed"),
                    ("COMPLETE", "Complete"),
                ],
                db_index=True,
                default="NEW",
                max_length=20,
            ),
        ),
    ]
