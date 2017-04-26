from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django_dbq.models import Job
import json
import logging


logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = "Create a job"
    args = '<job_name>'

    def add_arguments(self, parser):
        parser.add_argument('args', nargs='+')
        parser.add_argument(
            '--workspace',
            action='store_true',
            dest='workspace',
            default=None,
            help="JSON-formatted initial commandworkspace."
        )
        parser.add_argument(
            '--queue_name',
            action='store_true',
            dest='queue_name',
            default=None,
            help="A specific queue to add this job to"
        )

    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError("Please supply a single job name")

        name = args[0]
        if name not in settings.JOBS:
            raise CommandError('"%s" is not a valid job name' % name)

        workspace = options['workspace']
        if workspace:
            workspace = json.loads(workspace)

        queue_name = options['queue_name']

        kwargs = {
            'name': name,
            'workspace': workspace,
        }

        if queue_name:
            kwargs['queue_name'] = queue_name

        job = Job.objects.create(**kwargs)
        self.stdout.write('Created job: "%s", id=%s for queue "%s"' % (job.name, job.pk, queue_name if queue_name else 'default'))
