from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django_dbq.models import Job
from optparse import make_option
import json
import logging


logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = "Create a job"
    args = '<job_name>'

    option_list = BaseCommand.option_list + (
        make_option('--workspace',
                    help='JSON-formatted initial command workspace'),)

    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError("Please supply a single job name")

        name = args[0]
        if name not in settings.JOBS:
            raise CommandError('"%s" is not a valid job name' % name)

        workspace = options['workspace']
        if workspace:
            workspace = json.loads(workspace)

        job = Job.objects.create(name=name, workspace=workspace)
        self.stdout.write('Created job: "%s", id=%s' % (job.name, job.pk))
