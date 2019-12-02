from django.core.management.base import BaseCommand
from django_dbq.models import Job


class Command(BaseCommand):

    help = "Print the current depth of the given queue"

    def add_arguments(self, parser):
        parser.add_argument("queue_name", nargs="?", default="default", type=str)

    def handle(self, *args, **options):
        queue_name = options["queue_name"]
        queue_depths = Job.get_queue_depths()
        all_queues_depth = sum([queue_depth for _, queue_depth in queue_depths.items()])

        self.stdout.write(
            "all_queues_depth= queue_name={queue_name} queue_depth={depth}".format(
                all_queues_depth=all_queues_depth,
                queue_name=queue_name,
                depth=queue_depths.get(queue_name, 0),
            )
        )
