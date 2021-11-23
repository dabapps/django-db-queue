from django.db import models
from django.utils import timezone
from django.utils.module_loading import import_string
from django_dbq.tasks import (
    get_next_task_name,
    get_failure_hook_name,
    get_creation_hook_name,
)
from django.db.models import JSONField, UUIDField, Count, TextChoices
import datetime
import logging
import uuid


logger = logging.getLogger(__name__)


DELETE_JOBS_AFTER_HOURS = 24


class JobManager(models.Manager):
    def get_ready_or_none(self, queue_name, max_retries=3):
        """
        Get a job in state READY or NEW for a given queue. Supports retrying in case of database deadlock

        See https://dev.mysql.com/doc/refman/5.0/en/innodb-deadlocks.html

        "Always be prepared to re-issue a transaction if it fails due to
        deadlock. Deadlocks are not dangerous. Just try again."

        In the `except` clause, it's difficult to be more specific on the
        exception type, because it's different on different backends. MySQL,
        for example, raises a django.db.utils.InternalError for all manner of
        database-related problems. This code is more-or-less cribbed from
        django-celery, which uses a very similar approach.

        """
        retries_left = max_retries
        while True:
            try:
                return self.to_process(queue_name).first()
            except Exception as e:
                if retries_left == 0:
                    raise
                retries_left -= 1
                logger.warn(
                    "Caught %s when looking for a READY job, retrying %s more times",
                    str(e),
                    retries_left,
                )

    def delete_old(self):
        """
        Delete all jobs older than DELETE_JOBS_AFTER_HOURS
        """
        delete_jobs_in_states = [Job.STATES.FAILED, Job.STATES.COMPLETE]
        delete_jobs_created_before = timezone.now() - datetime.timedelta(
            hours=DELETE_JOBS_AFTER_HOURS
        )
        logger.info(
            "Deleting all job in states %s created before %s",
            ", ".join(delete_jobs_in_states),
            delete_jobs_created_before.isoformat(),
        )
        Job.objects.filter(
            state__in=delete_jobs_in_states, created__lte=delete_jobs_created_before
        ).delete()

    def to_process(self, queue_name):
        return self.select_for_update().filter(
            models.Q(queue_name=queue_name)
            & models.Q(state__in=(Job.STATES.READY, Job.STATES.NEW))
            & models.Q(
                models.Q(run_after__isnull=True)
                | models.Q(run_after__lte=timezone.now())
            )
        )


class Job(models.Model):
    class STATES(TextChoices):
        NEW = "NEW"
        READY = "READY"
        PROCESSING = "PROCESSING"
        FAILED = "FAILED"
        COMPLETE = "COMPLETE"

    id = UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created = models.DateTimeField(auto_now_add=True, db_index=True)
    modified = models.DateTimeField(auto_now=True)
    name = models.CharField(max_length=100)
    state = models.CharField(
        max_length=20, choices=STATES.choices, default=STATES.NEW, db_index=True
    )
    next_task = models.CharField(max_length=100, blank=True)
    workspace = JSONField(null=True)
    queue_name = models.CharField(max_length=20, default="default", db_index=True)
    priority = models.SmallIntegerField(default=0, db_index=True)
    run_after = models.DateTimeField(null=True, db_index=True)

    class Meta:
        ordering = ["-priority", "created"]

    objects = JobManager()

    def save(self, *args, **kwargs):
        if self._state.adding:
            self.next_task = get_next_task_name(self.name)
            self.workspace = self.workspace or {}

            try:
                self.run_creation_hook()
            except Exception as exception:  # noqa
                logger.exception(
                    "Failed to create new job, creation hook raised an exception"
                )
                return  # cancel the save

        return super().save(*args, **kwargs)

    def update_next_task(self):
        self.next_task = get_next_task_name(self.name, self.next_task) or ""

    def get_failure_hook_name(self):
        return get_failure_hook_name(self.name)

    def get_creation_hook_name(self):
        return get_creation_hook_name(self.name)

    def run_creation_hook(self):
        creation_hook_name = self.get_creation_hook_name()
        if creation_hook_name:
            logger.info("Running creation hook %s for new job", creation_hook_name)
            creation_hook_function = import_string(creation_hook_name)
            creation_hook_function(self)

    @staticmethod
    def get_queue_depths():
        annotation_dicts = (
            Job.objects.filter(state__in=(Job.STATES.READY, Job.STATES.NEW))
            .values("queue_name")
            .order_by("queue_name")
            .annotate(Count("queue_name"))
        )

        return {
            annotation_dict["queue_name"]: annotation_dict["queue_name__count"]
            for annotation_dict in annotation_dicts
        }
