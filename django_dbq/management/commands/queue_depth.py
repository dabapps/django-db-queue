from django.core.management.base import BaseCommand
from django_dbq.models import Job


class Command(BaseCommand):

    help = "Print the current depth of the given queue"

    def add_arguments(self, parser):
        parser.add_argument("queue_name", nargs="*", default=["default"], type=str)

    def handle(self, *args, **options):
        queue_names = options["queue_name"]
        queue_depths = Job.get_queue_depths()

        self.stdout.write(
            " ".join(
                [
                    "{queue_name}={queue_depth}".format(
                        queue_name=queue_name,
                        queue_depth=queue_depths.get(queue_name, 0),
                    )
                    for queue_name in queue_names
                ]
            )
        )
