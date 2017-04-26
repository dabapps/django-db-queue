from datetime import datetime, timedelta
from django.core.management import call_command, CommandError
from django.test import TestCase
from django.test.utils import override_settings
from django_dbq.management.commands.worker import process_job
from django_dbq.models import Job
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO


def test_task(job=None):
    pass  # pragma: no cover


def workspace_test_task(job):
    input = job.workspace['input']
    job.workspace['output'] = input + '-output'


def failing_task(job):
    raise Exception("uh oh")


def failure_hook(job, exception):
    job.workspace['output'] = 'failure hook ran'


def creation_hook(job):
    job.workspace['output'] = 'creation hook ran'


@override_settings(JOBS={'testjob': {'tasks': ['a']}})
class JobManagementCommandTestCase(TestCase):

    def test_create_job(self):
        call_command('create_job', 'testjob', stdout=StringIO())
        job = Job.objects.get()
        self.assertEqual(job.name, 'testjob')
        self.assertEqual(job.queue_name, 'default')

    def test_create_job_with_workspace(self):
        workspace = '{"test": "test"}'
        call_command('create_job', 'testjob', workspace=workspace, stdout=StringIO())
        job = Job.objects.get()
        self.assertEqual(job.workspace, {'test': 'test'})

    def test_create_job_with_queue_name(self):
        call_command('create_job', 'testjob', queue_name='lol', stdout=StringIO())
        job = Job.objects.get()
        self.assertEqual(job.name, 'testjob')
        self.assertEqual(job.queue_name, 'lol')

    def test_errors_raised_correctly(self):
        with self.assertRaises(CommandError):
            call_command('create_job', stdout=StringIO())

        with self.assertRaises(CommandError):
            call_command('create_job', 'some_other_job', stdout=StringIO())


@override_settings(JOBS={'testjob': {'tasks': ['a']}})
class WorkerManagementCommandTestCase(TestCase):

    def test_worker_no_args(self):
        stdout = StringIO()
        call_command('worker', dry_run=True, stdout=stdout)
        output = stdout.getvalue()
        self.assertTrue('Starting job worker' in output)
        self.assertTrue('default' in output)

    def test_worker_with_queue_name(self):
        stdout = StringIO()
        call_command('worker', queue_name='test_queue', dry_run=True, stdout=stdout)
        output = stdout.getvalue()
        self.assertTrue('test_queue' in output)


@override_settings(JOBS={'testjob': {'tasks': ['a']}})
class JobTestCase(TestCase):

    def test_create_job(self):
        job = Job(name='testjob')
        self.assertEqual(job.state, Job.STATES.NEW)

    def test_create_job_with_queue(self):
        job = Job(name='testjob', queue_name='lol')
        self.assertEqual(job.state, Job.STATES.NEW)
        self.assertEqual(job.queue_name, 'lol')

    def test_get_next_ready_job(self):
        self.assertTrue(Job.objects.get_ready_or_none('default') is None)

        Job.objects.create(name='testjob', state=Job.STATES.READY)
        Job.objects.create(name='testjob', state=Job.STATES.PROCESSING)
        expected = Job.objects.create(name='testjob', state=Job.STATES.READY)
        expected.created = datetime.now() - timedelta(minutes=1)
        expected.save()

        self.assertEqual(Job.objects.get_ready_or_none('default'), expected)

    def test_get_next_ready_job_created(self):
        """
        Created jobs should be picked too.

        We create three jobs, and expect the oldest in NEW or READY to be
        selected by get_ready_or_none (the model is ordered by 'created' and the
        query picks the .first())
        """
        self.assertTrue(Job.objects.get_ready_or_none('default') is None)

        Job.objects.create(name='testjob', state=Job.STATES.NEW)
        Job.objects.create(name='testjob', state=Job.STATES.PROCESSING)
        expected = Job.objects.create(name='testjob', state=Job.STATES.NEW)
        expected.created = datetime.now() - timedelta(minutes=1)
        expected.save()

        self.assertEqual(Job.objects.get_ready_or_none('default'), expected)


@override_settings(JOBS={'testjob': {'tasks': ['a', 'b', 'c']}})
class JobTaskTestCase(TestCase):

    def test_task_sequence(self):
        job = Job.objects.create(name='testjob')
        self.assertEqual(job.next_task, 'a')
        job.update_next_task()
        self.assertEqual(job.next_task, 'b')
        job.update_next_task()
        self.assertEqual(job.next_task, 'c')
        job.update_next_task()
        self.assertEqual(job.next_task, '')


@override_settings(JOBS={'testjob': {'tasks': ['django_dbq.tests.test_task']}})
class ProcessJobTestCase(TestCase):

    def test_process_job(self):
        job = Job.objects.create(name='testjob')
        process_job('default')
        job = Job.objects.get()
        self.assertEqual(job.state, Job.STATES.COMPLETE)

    def test_process_job_wrong_queue(self):
        """
        Processing a different queue shouldn't touch our other job
        """
        job = Job.objects.create(name='testjob', queue_name='lol')
        process_job('default')
        job = Job.objects.get()
        self.assertEqual(job.state, Job.STATES.NEW)


@override_settings(JOBS={'testjob': {'tasks': ['django_dbq.tests.test_task'], 'creation_hook': 'django_dbq.tests.creation_hook'}})
class JobCreationHookTestCase(TestCase):

    def test_creation_hook(self):
        job = Job.objects.create(name='testjob')
        job = Job.objects.get()
        self.assertEqual(job.workspace['output'], 'creation hook ran')

    def test_creation_hook_only_runs_on_create(self):
        job = Job.objects.create(name='testjob')
        job = Job.objects.get()
        job.workspace['output'] = 'creation hook output removed'
        job.save()
        job = Job.objects.get()
        self.assertEqual(job.workspace['output'], 'creation hook output removed')


@override_settings(JOBS={'testjob': {'tasks': ['django_dbq.tests.failing_task'], 'failure_hook': 'django_dbq.tests.failure_hook'}})
class JobFailureHookTestCase(TestCase):

    def test_failure_hook(self):
        job = Job.objects.create(name='testjob')
        process_job('default')
        job = Job.objects.get()
        self.assertEqual(job.state, Job.STATES.FAILED)
        self.assertEqual(job.workspace['output'], 'failure hook ran')


@override_settings(JOBS={'testjob': {'tasks': ['a']}})
class DeleteOldJobsTestCase(TestCase):

    def test_delete_old_jobs(self):
        two_days_ago = datetime.utcnow() - timedelta(days=2)

        j1 = Job.objects.create(name='testjob', state=Job.STATES.COMPLETE)
        j1.created = two_days_ago
        j1.save()

        j2 = Job.objects.create(name='testjob', state=Job.STATES.FAILED)
        j2.created = two_days_ago
        j2.save()

        j3 = Job.objects.create(name='testjob', state=Job.STATES.NEW)
        j3.created = two_days_ago
        j3.save()

        j4 = Job.objects.create(name='testjob', state=Job.STATES.COMPLETE)

        Job.objects.delete_old()

        self.assertEqual(Job.objects.count(), 2)
        self.assertTrue(j3 in Job.objects.all())
        self.assertTrue(j4 in Job.objects.all())
