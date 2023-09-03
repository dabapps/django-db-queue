from datetime import datetime, timedelta
import mock

import freezegun
from django.core.management import call_command, CommandError
from django.test import TestCase
from django.test.utils import override_settings
from django.utils import timezone

from django_dbq.management.commands.worker import Worker
from django_dbq.models import Job

from io import StringIO


def test_task(job=None):
    pass  # pragma: no cover


def workspace_test_task(job):
    input = job.workspace["input"]
    job.workspace["output"] = input + "-output"


def failing_task(job):
    raise Exception("uh oh")


def shift_task(job):
    job.workspace["message"] = f"{job.id} ran"


def failure_hook(job, exception):
    job.workspace["output"] = "failure hook ran"


def creation_hook(job):
    job.workspace["output"] = "creation hook ran"


@override_settings(JOBS={"testjob": {"tasks": ["a"]}})
class WorkerManagementCommandTestCase(TestCase):
    def test_worker_no_args(self):
        stdout = StringIO()
        call_command("worker", dry_run=True, stdout=stdout)
        output = stdout.getvalue()
        self.assertTrue("Starting job worker" in output)
        self.assertTrue("default" in output)

    def test_worker_with_queue_name(self):
        stdout = StringIO()
        call_command("worker", queue_name="test_queue", dry_run=True, stdout=stdout)
        output = stdout.getvalue()
        self.assertTrue("test_queue" in output)


@override_settings(JOBS={"testjob": {"tasks": ["a"]}})
class JobModelMethodTestCase(TestCase):
    def test_get_queue_depths(self):
        Job.objects.create(name="testjob", queue_name="default")
        Job.objects.create(name="testjob", queue_name="testworker")
        Job.objects.create(name="testjob", queue_name="testworker")
        Job.objects.create(
            name="testjob", queue_name="testworker", state=Job.STATES.FAILED
        )
        Job.objects.create(
            name="testjob", queue_name="testworker", state=Job.STATES.COMPLETE
        )

        queue_depths = Job.get_queue_depths()
        self.assertDictEqual(queue_depths, {"default": 1, "testworker": 2})


@override_settings(JOBS={"testjob": {"tasks": ["a"]}})
class QueueDepthTestCase(TestCase):
    def test_queue_depth(self):

        Job.objects.create(name="testjob", state=Job.STATES.FAILED)
        Job.objects.create(name="testjob", state=Job.STATES.NEW)
        Job.objects.create(name="testjob", state=Job.STATES.FAILED)
        Job.objects.create(name="testjob", state=Job.STATES.COMPLETE)
        Job.objects.create(name="testjob", state=Job.STATES.READY)
        Job.objects.create(
            name="testjob", queue_name="testqueue", state=Job.STATES.READY
        )
        Job.objects.create(
            name="testjob", queue_name="testqueue", state=Job.STATES.READY
        )

        stdout = StringIO()
        call_command("queue_depth", stdout=stdout)
        output = stdout.getvalue()
        self.assertEqual(output.strip(), "event=queue_depths default=2")

    def test_queue_depth_multiple_queues(self):

        Job.objects.create(name="testjob", state=Job.STATES.FAILED)
        Job.objects.create(name="testjob", state=Job.STATES.NEW)
        Job.objects.create(name="testjob", state=Job.STATES.FAILED)
        Job.objects.create(name="testjob", state=Job.STATES.COMPLETE)
        Job.objects.create(name="testjob", state=Job.STATES.READY)
        Job.objects.create(
            name="testjob", queue_name="testqueue", state=Job.STATES.READY
        )
        Job.objects.create(
            name="testjob", queue_name="testqueue", state=Job.STATES.READY
        )

        stdout = StringIO()
        call_command(
            "queue_depth",
            queue_name=(
                "default",
                "testqueue",
            ),
            stdout=stdout,
        )
        output = stdout.getvalue()
        self.assertEqual(output.strip(), "event=queue_depths default=2 testqueue=2")

    def test_queue_depth_for_queue_with_zero_jobs(self):
        stdout = StringIO()
        call_command("queue_depth", queue_name=("otherqueue",), stdout=stdout)
        output = stdout.getvalue()
        self.assertEqual(output.strip(), "event=queue_depths otherqueue=0")


@freezegun.freeze_time()
@mock.patch("django_dbq.management.commands.worker.sleep")
class WorkerProcessProcessJobTestCase(TestCase):
    def setUp(self):
        super().setUp()
        self.mock_worker = mock.MagicMock()
        self.mock_worker.queue_name = "default"
        self.mock_worker.rate_limit_in_seconds = 5
        self.mock_worker.last_job_finished = None

    def test_process_job_no_previous_job_run(self, mock_sleep):
        Worker.process_job(self.mock_worker)
        self.assertEqual(mock_sleep.call_count, 1)
        self.assertEqual(self.mock_worker._process_job.call_count, 1)
        self.assertEqual(self.mock_worker.last_job_finished, timezone.now())

    def test_process_job_previous_job_too_soon(self, mock_sleep):
        self.mock_worker.last_job_finished = timezone.now() - timezone.timedelta(
            seconds=2
        )
        Worker.process_job(self.mock_worker)
        self.assertEqual(mock_sleep.call_count, 1)
        self.assertEqual(self.mock_worker._process_job.call_count, 0)
        self.assertEqual(
            self.mock_worker.last_job_finished,
            timezone.now() - timezone.timedelta(seconds=2),
        )

    def test_process_job_previous_job_long_time_ago(self, mock_sleep):
        self.mock_worker.last_job_finished = timezone.now() - timezone.timedelta(
            seconds=7
        )
        Worker.process_job(self.mock_worker)
        self.assertEqual(mock_sleep.call_count, 1)
        self.assertEqual(self.mock_worker._process_job.call_count, 1)
        self.assertEqual(self.mock_worker.last_job_finished, timezone.now())


@override_settings(JOBS={"testjob": {"tasks": ["a"]}})
class ShutdownTestCase(TestCase):
    def test_shutdown_sets_state_to_stopping(self):
        job = Job.objects.create(name="testjob")
        worker = Worker("default", 1, 0)
        worker.current_job = job

        worker.shutdown(None, None)

        job.refresh_from_db()
        self.assertEqual(job.state, Job.STATES.STOPPING)


@override_settings(JOBS={"testjob": {"tasks": ["a"]}})
class JobTestCase(TestCase):
    def test_create_job(self):
        job = Job(name="testjob")
        self.assertEqual(job.state, Job.STATES.NEW)

    def test_create_job_with_queue(self):
        job = Job(name="testjob", queue_name="lol")
        self.assertEqual(job.state, Job.STATES.NEW)
        self.assertEqual(job.queue_name, "lol")

    def test_get_next_ready_job(self):
        self.assertTrue(Job.objects.get_ready_or_none("default") is None)

        Job.objects.create(name="testjob", state=Job.STATES.READY)
        Job.objects.create(name="testjob", state=Job.STATES.PROCESSING)
        expected = Job.objects.create(name="testjob", state=Job.STATES.READY)
        expected.created = datetime.now() - timedelta(minutes=1)
        expected.save()

        self.assertEqual(Job.objects.get_ready_or_none("default"), expected)

    def test_gets_jobs_in_priority_order(self):
        job_1 = Job.objects.create(name="testjob")
        job_2 = Job.objects.create(name="testjob", state=Job.STATES.PROCESSING)
        job_3 = Job.objects.create(name="testjob", priority=3)
        job_4 = Job.objects.create(name="testjob", priority=2)
        self.assertEqual(
            {job for job in Job.objects.to_process("default")}, {job_3, job_4, job_1}
        )
        self.assertEqual(Job.objects.get_ready_or_none("default"), job_3)
        self.assertFalse(Job.objects.to_process("default").filter(id=job_2.id).exists())

    def test_gets_jobs_in_negative_priority_order(self):
        job_1 = Job.objects.create(name="testjob")
        job_2 = Job.objects.create(name="testjob", state=Job.STATES.PROCESSING)
        job_3 = Job.objects.create(name="testjob", priority=-2)
        job_4 = Job.objects.create(name="testjob", priority=1)
        self.assertEqual(
            {job for job in Job.objects.to_process("default")}, {job_4, job_3, job_1}
        )
        self.assertEqual(Job.objects.get_ready_or_none("default"), job_4)
        self.assertFalse(Job.objects.to_process("default").filter(id=job_2.id).exists())

    def test_gets_jobs_in_priority_and_date_order(self):
        job_1 = Job.objects.create(name="testjob", priority=3)
        job_2 = Job.objects.create(
            name="testjob", state=Job.STATES.PROCESSING, priority=3
        )
        job_3 = Job.objects.create(name="testjob", priority=3)
        job_4 = Job.objects.create(name="testjob", priority=3)
        self.assertEqual(
            {job for job in Job.objects.to_process("default")}, {job_1, job_3, job_4}
        )
        self.assertEqual(Job.objects.get_ready_or_none("default"), job_1)
        self.assertFalse(Job.objects.to_process("default").filter(id=job_2.id).exists())

    def test_ignores_jobs_until_run_after_is_in_the_past(self):
        job_1 = Job.objects.create(name="testjob")
        job_2 = Job.objects.create(name="testjob", run_after=datetime(2021, 11, 4, 8))

        with freezegun.freeze_time(datetime(2021, 11, 4, 7)):
            self.assertEqual(
                {job for job in Job.objects.to_process("default")}, {job_1}
            )

        with freezegun.freeze_time(datetime(2021, 11, 4, 9)):
            self.assertEqual(
                {job for job in Job.objects.to_process("default")}, {job_1, job_2}
            )

    def test_get_next_ready_job_created(self):
        """
        Created jobs should be picked too.

        We create three jobs, and expect the oldest in NEW or READY to be
        selected by get_ready_or_none (the model is ordered by 'created' and the
        query picks the .first())
        """
        self.assertTrue(Job.objects.get_ready_or_none("default") is None)

        Job.objects.create(name="testjob", state=Job.STATES.NEW)
        Job.objects.create(name="testjob", state=Job.STATES.PROCESSING)
        expected = Job.objects.create(name="testjob", state=Job.STATES.NEW)
        expected.created = datetime.now() - timedelta(minutes=1)
        expected.save()

        self.assertEqual(Job.objects.get_ready_or_none("default"), expected)


@override_settings(JOBS={"testjob": {"tasks": ["a", "b", "c"]}})
class JobTaskTestCase(TestCase):
    def test_task_sequence(self):
        job = Job.objects.create(name="testjob")
        self.assertEqual(job.next_task, "a")
        job.update_next_task()
        self.assertEqual(job.next_task, "b")
        job.update_next_task()
        self.assertEqual(job.next_task, "c")
        job.update_next_task()
        self.assertEqual(job.next_task, "")


@override_settings(JOBS={"testjob": {"tasks": ["django_dbq.tests.test_task"]}})
class ProcessJobTestCase(TestCase):
    def test_process_job(self):
        job = Job.objects.create(name="testjob")
        Worker("default", 1, 0)._process_job()
        job = Job.objects.get()
        self.assertEqual(job.state, Job.STATES.COMPLETE)

    def test_process_job_wrong_queue(self):
        """
        Processing a different queue shouldn't touch our other job
        """
        job = Job.objects.create(name="testjob", queue_name="lol")
        Worker("default", 1, 0)._process_job()
        job = Job.objects.get()
        self.assertEqual(job.state, Job.STATES.NEW)


@override_settings(
    JOBS={
        "testjob": {
            "tasks": ["django_dbq.tests.test_task"],
            "creation_hook": "django_dbq.tests.creation_hook",
        }
    }
)
class JobCreationHookTestCase(TestCase):
    def test_creation_hook(self):
        job = Job.objects.create(name="testjob")
        job = Job.objects.get()
        self.assertEqual(job.workspace["output"], "creation hook ran")

    def test_creation_hook_only_runs_on_create(self):
        job = Job.objects.create(name="testjob")
        job = Job.objects.get()
        job.workspace["output"] = "creation hook output removed"
        job.save()
        job = Job.objects.get()
        self.assertEqual(job.workspace["output"], "creation hook output removed")


@override_settings(
    JOBS={
        "testjob": {
            "tasks": ["django_dbq.tests.failing_task"],
            "failure_hook": "django_dbq.tests.failure_hook",
        }
    }
)
class JobFailureHookTestCase(TestCase):
    def test_failure_hook(self):
        job = Job.objects.create(name="testjob")
        Worker("default", 1, 0)._process_job()
        job = Job.objects.get()
        self.assertEqual(job.state, Job.STATES.FAILED)
        self.assertEqual(job.workspace["output"], "failure hook ran")


@override_settings(JOBS={"testjob": {"tasks": ["a"]}})
class DeleteOldJobsTestCase(TestCase):
    def test_delete_old_jobs(self):
        two_days_ago = datetime.utcnow() - timedelta(days=2)

        j1 = Job.objects.create(name="testjob", state=Job.STATES.COMPLETE)
        j1.created = two_days_ago
        j1.save()

        j2 = Job.objects.create(name="testjob", state=Job.STATES.FAILED)
        j2.created = two_days_ago
        j2.save()

        j3 = Job.objects.create(name="testjob", state=Job.STATES.STOPPING)
        j3.created = two_days_ago
        j3.save()

        j4 = Job.objects.create(name="testjob", state=Job.STATES.NEW)
        j4.created = two_days_ago
        j4.save()

        j5 = Job.objects.create(name="testjob", state=Job.STATES.COMPLETE)

        Job.objects.delete_old()

        self.assertEqual(Job.objects.count(), 2)
        self.assertTrue(j4 in Job.objects.all())
        self.assertTrue(j5 in Job.objects.all())


@override_settings(JOBS={"testshift": {"tasks": ["django_dbq.tests.shift_task"]}})
class ShiftTestCase(TestCase):
    """ Tests various combinations of rate_limit and shift_limit in terms of their impact on processing jobs"""
    def test_rate_with_shorter_shift_limit(self):
        Job.objects.create(name="testshift")
        Job.objects.create(name="testshift")
        stdout = StringIO()
        call_command("worker", rate_limit=2, shift_limit=1, stdout=stdout)
        output = stdout.getvalue()
        self.assertTrue("rate limit of one job per 2 second(s) and a shift constraint of 1 seconds" in output)
        self.assertEqual(Job.objects.filter(state=Job.STATES.NEW).count(), 1)
        self.assertEqual(Job.objects.filter(state=Job.STATES.COMPLETE).count(), 1)

    def test_rate_with_equal_shift_limit(self):
        Job.objects.create(name="testshift")
        Job.objects.create(name="testshift")
        stdout = StringIO()
        call_command("worker", rate_limit=1, shift_limit=1, stdout=stdout)
        output = stdout.getvalue()
        self.assertTrue("rate limit of one job per 1 second(s) and a shift constraint of 1 seconds" in output)
        self.assertEqual(Job.objects.filter(state=Job.STATES.NEW).count(), 1)
        self.assertEqual(Job.objects.filter(state=Job.STATES.COMPLETE).count(), 1)

    def test_rate_with_longer_shift_limit(self):
        Job.objects.create(name="testshift")
        Job.objects.create(name="testshift")
        stdout = StringIO()
        call_command("worker", rate_limit=1, shift_limit=2, stdout=stdout)
        output = stdout.getvalue()
        self.assertTrue("rate limit of one job per 1 second(s) and a shift constraint of 2 seconds" in output)
        self.assertEqual(Job.objects.filter(state=Job.STATES.NEW).count(), 0)
        self.assertEqual(Job.objects.filter(state=Job.STATES.COMPLETE).count(), 2)

    def test_rate_with_two_workers(self):
        Job.objects.create(name="testshift")
        Job.objects.create(name="testshift")
        Job.objects.create(name="testshift")
        Job.objects.create(name="testshift")
        stdout = StringIO()
        call_command("worker", rate_limit=1, shift_limit=2, stdout=stdout)
        output = stdout.getvalue()
        self.assertTrue("rate limit of one job per 1 second(s) and a shift constraint of 2 seconds" in output)
        call_command("worker", rate_limit=1, shift_limit=1, stdout=stdout)
        output = stdout.getvalue()
        self.assertTrue("rate limit of one job per 1 second(s) and a shift constraint of 1 seconds" in output)
        self.assertEqual(Job.objects.filter(state=Job.STATES.NEW).count(), 1)
        self.assertEqual(Job.objects.filter(state=Job.STATES.COMPLETE).count(), 3)


