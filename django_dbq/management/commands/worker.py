from django.db import transaction
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.utils.module_loading import import_string
from django_dbq.models import Job
from time import sleep
import logging
import signal


logger = logging.getLogger(__name__)


DEFAULT_QUEUE_NAME = "default"


class Worker:
    def __init__(self, name, rate_limit_in_seconds, drain=False):
        self.queue_name = name
        self.rate_limit_in_seconds = rate_limit_in_seconds
        self.drain = drain
        self.alive = True
        self.last_job_finished = None
        self.current_job = None
        self.init_signals()

    def init_signals(self):
        signal.signal(signal.SIGINT, self.shutdown)

        # for Windows, which doesn't support the SIGQUIT signal
        if hasattr(signal, "SIGQUIT"):
            signal.signal(signal.SIGQUIT, self.shutdown)

        signal.signal(signal.SIGTERM, self.shutdown)

    def shutdown(self, signum, frame):
        self.alive = False
        if self.current_job:
            self.current_job.state = Job.STATES.STOPPING
            self.current_job.save(update_fields=["state"])

    def run(self):
        while self.alive:
            self.process_job()

    def process_job(self):
        sleep(1)
        if (
            self.last_job_finished
            and (timezone.now() - self.last_job_finished).total_seconds()
            < self.rate_limit_in_seconds
        ):
            return

        self._process_job()

        self.last_job_finished = timezone.now()

    def _process_job(self):
        with transaction.atomic():
            job = Job.objects.get_ready_or_none(self.queue_name)
            if not job:
                if self.drain:
                    self.alive = False
                return

            logger.info(
                'Processing job: name="%s" queue="%s" id=%s state=%s next_task=%s',
                job.name,
                self.queue_name,
                job.pk,
                job.state,
                job.next_task,
            )
            job.state = Job.STATES.PROCESSING
            job.save()
            self.current_job = job

        try:
            task_function = import_string(job.next_task)
            task_function(job)
            job.update_next_task()
            if not job.next_task:
                job.state = Job.STATES.COMPLETE
            else:
                job.state = Job.STATES.READY
        except Exception as exception:
            logger.exception("Job id=%s failed", job.pk)
            job.state = Job.STATES.FAILED

            failure_hook_name = job.get_failure_hook_name()
            if failure_hook_name:
                logger.info(
                    "Running failure hook %s for job id=%s", failure_hook_name, job.pk
                )
                failure_hook_function = import_string(failure_hook_name)
                failure_hook_function(job, exception)
            else:
                logger.info("No failure hook for job id=%s", job.pk)

        logger.info(
            'Updating job: name="%s" id=%s state=%s next_task=%s',
            job.name,
            job.pk,
            job.state,
            job.next_task or "none",
        )

        try:
            job.save()
        except:
            logger.exception("Failed to save job: id=%s", job.pk)
            raise

        self.current_job = None


class Command(BaseCommand):

    help = "Run a queue worker process"

    def add_arguments(self, parser):
        parser.add_argument("queue_name", nargs="?", default="default", type=str)
        parser.add_argument(
            "--rate_limit",
            help="The rate limit in seconds. The default rate limit is 1 job per second.",
            nargs="?",
            default=1,
            type=int,
        )
        parser.add_argument(
            "--drain",
            help="Process all jobs in the queue and then exit",
            action="store_true",
            dest="drain",
            default=False,
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            dest="dry_run",
            default=False,
            help="Don't actually start the worker. Used for testing.",
        )

    def handle(self, *args, **options):
        if not args:
            args = (DEFAULT_QUEUE_NAME,)

        if len(args) != 1:
            raise CommandError("Please supply a single queue job name")

        queue_name = options["queue_name"]
        rate_limit_in_seconds = options["rate_limit"]
        drain = options["drain"]

        self.stdout.write(
            'Starting job worker for queue "%s" with rate limit of one job per %s second(s)'
            % (queue_name, rate_limit_in_seconds)
        )

        worker = Worker(queue_name, rate_limit_in_seconds, drain=drain)

        if options["dry_run"]:
            return

        worker.run()
