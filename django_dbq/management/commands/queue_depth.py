from django.core.management.base import BaseCommand
from django_dbq.models import Job


class Command(BaseCommand):

    help = "Print the current depth of the given queue"

    def add_arguments(self, parser):
        parser.add_argument('queue_name', nargs='?', default='default', type=str)

    def handle(self, *args, **options):
        queue_name = options['queue_name']
        queue_depth = Job.objects.filter(queue_name=queue_name, state__in=(Job.STATES.READY, Job.STATES.NEW)).count()
        self.stdout.write("Queue depth for queue \"%s\" is %s" % (queue_name, queue_depth))
