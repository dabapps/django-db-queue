from datetime import datetime, timedelta
import mock

import freezegun
from django.core.management import call_command, CommandError
from django.test import TestCase
from django.test.utils import override_settings
from django.utils import timezone

from django_dbq.management.commands.worker import process_job, Worker
from django_dbq.models import Job

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO


def test_task(job=None):
    pass  # pragma: no cover


def workspace_test_task(job):
    input = job.workspace["input"]
    job.workspace["output"] = input + "-output"


def failing_task(job):
    raise Exception("uh oh")


def failure_hook(job, exception):
    job.workspace["output"] = "failure hook ran"


def creation_hook(job):
    job.workspace["output"] = "creation hook ran"


@override_settings(JOBS={"testjob": {"tasks": ["a"]}})
class JobManagementCommandTestCase(TestCase):
    def test_create_job(self):
        call_command("create_job", "testjob", stdout=StringIO())
        job = Job.objects.get()
        self.assertEqual(job.name, "testjob")
        self.assertEqual(job.queue_name, "default")

    def test_create_job_with_workspace(self):
        workspace = '{"test": "test"}'
        call_command("create_job", "testjob", workspace=workspace, stdout=StringIO())
        job = Job.objects.get()
        self.assertEqual(job.workspace, {"test": "test"})

    def test_create_job_with_queue_name(self):
        call_command("create_job", "testjob", queue_name="lol", stdout=StringIO())
        job = Job.objects.get()
        self.assertEqual(job.name, "testjob")
        self.assertEqual(job.queue_name, "lol")

    def test_errors_raised_correctly(self):
        with self.assertRaises(CommandError):
            call_command("create_job", stdout=StringIO())

        with self.assertRaises(CommandError):
            call_command("create_job", "some_other_job", stdout=StringIO())


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


@freezegun.freeze_time()
@mock.patch("django_dbq.management.commands.worker.sleep")
@mock.patch("django_dbq.management.commands.worker.process_job")
class WorkerProcessDoWorkTestCase(TestCase):
    def setUp(self):
        super().setUp()
        self.MockWorker = mock.MagicMock()
        self.MockWorker.queue_name = "default"
        self.MockWorker.rate_limit_in_seconds = 5
        self.MockWorker.last_job_finished = None

    def test_do_work_no_previous_job_run(self, mock_process_job, mock_sleep):
        Worker.do_work(self.MockWorker)
        self.assertEqual(mock_sleep.call_count, 1)
        self.assertEqual(mock_process_job.call_count, 1)
        self.assertEqual(self.MockWorker.last_job_finished, timezone.now())

    def test_do_work_previous_job_too_soon(self, mock_process_job, mock_sleep):
        self.MockWorker.last_job_finished = timezone.now() - timezone.timedelta(
            seconds=2
        )
        Worker.do_work(self.MockWorker)
        self.assertEqual(mock_sleep.call_count, 1)
        self.assertEqual(mock_process_job.call_count, 0)
        self.assertEqual(
            self.MockWorker.last_job_finished,
            timezone.now() - timezone.timedelta(seconds=2),
        )

    def test_do_work_previous_job_long_time_ago(self, mock_process_job, mock_sleep):
        self.MockWorker.last_job_finished = timezone.now() - timezone.timedelta(
            seconds=7
        )
        Worker.do_work(self.MockWorker)
        self.assertEqual(mock_sleep.call_count, 1)
        self.assertEqual(mock_process_job.call_count, 1)
        self.assertEqual(self.MockWorker.last_job_finished, timezone.now())


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
        process_job("default")
        job = Job.objects.get()
        self.assertEqual(job.state, Job.STATES.COMPLETE)

    def test_process_job_wrong_queue(self):
        """
        Processing a different queue shouldn't touch our other job
        """
        job = Job.objects.create(name="testjob", queue_name="lol")
        process_job("default")
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
        process_job("default")
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

        j3 = Job.objects.create(name="testjob", state=Job.STATES.NEW)
        j3.created = two_days_ago
        j3.save()

        j4 = Job.objects.create(name="testjob", state=Job.STATES.COMPLETE)

        Job.objects.delete_old()

        self.assertEqual(Job.objects.count(), 2)
        self.assertTrue(j3 in Job.objects.all())
        self.assertTrue(j4 in Job.objects.all())


@override_settings(JOBS={'testjob': {'tasks': ['a']}})
class QueueDepthTestCase(TestCase):

    def test_queue_depth(self):

        Job.objects.create(name='testjob', state=Job.STATES.FAILED)
        Job.objects.create(name='testjob', state=Job.STATES.NEW)
        Job.objects.create(name='testjob', state=Job.STATES.FAILED)
        Job.objects.create(name='testjob', state=Job.STATES.COMPLETE)
        Job.objects.create(name='testjob', state=Job.STATES.READY)

        stdout = StringIO()
        call_command('queue_depth', stdout=stdout)
        output = stdout.getvalue()
        self.assertEqual(output.strip(), 'Queue depth for queue "default" is 2')
