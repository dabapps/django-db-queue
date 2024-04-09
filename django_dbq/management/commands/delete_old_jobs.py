from django.core.management.base import BaseCommand
from django_dbq.models import Job


class Command(BaseCommand):

    help = "Delete old jobs"

    def add_arguments(self, parser):
        parser.add_argument(
            "--hours",
            help="Delete jobs older than this many hours",
            default=None,
            required=False,
            type=int,
        )

    def handle(self, *args, **options):
        Job.objects.delete_old(hours=options["hours"])
        self.stdout.write("Deleted old jobs")
