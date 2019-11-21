from django.core.management.base import BaseCommand
from django_dbq.models import Job


class Command(BaseCommand):

    help = "Delete old jobs"

    def handle(self, *args, **options):
        Job.objects.delete_old()
        self.stdout.write("Deleted old jobs")
