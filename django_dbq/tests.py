from datetime import datetime, timedelta
from django.core.management import call_command, CommandError
from django.core.urlresolvers import reverse
from django.test import TestCase, LiveServerTestCase
from django.test.utils import override_settings
from importer.apps.core.management.commands.worker import process_job
from importer.apps.core.models import Job
from importer.apps.core.utils.requests_storage import SessionStorage
from requests import Session
from rest_framework import status
from rest_framework.test import APITestCase
from StringIO import StringIO


class ImporterTestCase(APITestCase):
    def test_index_endpoint(self):
        """
        The endpoint should currently return "Hello, World!"
        """
        url = reverse('index')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.keys(), ['create_job'])
        self.assertEqual(response.data['create_job'], 'http://testserver/jobs/')

    def test_exception_view(self):
        """
        Exercise a view which always raises an exception.
        We use this to ensure logging config etc is setup correctly.
        """
        url = reverse('exception')
        with self.assertRaises(Exception) as context_manager:
            self.client.get(url)
        exc = context_manager.exception
        self.assertEqual(str(exc), 'You asked for it, kid.')


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
class JobAPITestCase(APITestCase):

    def test_create_job(self):
        url = reverse('create_job')
        response = self.client.post(url, {'name': 'testjob'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue('url' in response.data)
        self.assertEqual(Job.objects.count(), 1)
        job = Job.objects.get()
        self.assertEqual(job.name, 'testjob')
        self.assertEqual(job.state, job.STATES.READY)

    def test_create_job_with_invalid_name(self):
        url = reverse('create_job')
        response = self.client.post(url, {'name': 'some-other-job-name'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_job_detail(self):
        job = Job.objects.create(name='testjob')
        url = reverse('job_detail', kwargs={'pk': job.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['name'], 'testjob')


@override_settings(JOBS={'testjob': {'tasks': ['a']}})
class JobManagementCommandTestCase(TestCase):

    def test_create_job(self):
        call_command('create_job', 'testjob', stdout=StringIO())
        job = Job.objects.get()
        self.assertEqual(job.name, 'testjob')

    def test_create_job_with_workspace(self):
        workspace = '{"test": "test"}'
        call_command('create_job', 'testjob', workspace=workspace, stdout=StringIO())
        job = Job.objects.get()
        self.assertEqual(job.workspace, {'test': 'test'})

    def test_errors_raised_correctly(self):
        with self.assertRaises(CommandError):
            call_command('create_job', stdout=StringIO())

        with self.assertRaises(CommandError):
            call_command('create_job', 'some_other_job', stdout=StringIO())


@override_settings(JOBS={'testjob': {'tasks': ['a']}})
class JobTestCase(TestCase):

    def test_create_job(self):
        job = Job(name='testjob')
        self.assertEqual(job.state, Job.STATES.READY)

    def test_get_next_ready_job(self):
        self.assertTrue(Job.objects.get_ready_or_none() is None)

        Job.objects.create(name='testjob', state=Job.STATES.READY, created=datetime.now())
        Job.objects.create(name='testjob', state=Job.STATES.PROCESSING, created=datetime.now())
        expected = Job.objects.create(name='testjob', state=Job.STATES.READY, created=datetime.now() - timedelta(minutes=1))

        self.assertEqual(Job.objects.get_ready_or_none(), expected)


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


@override_settings(JOBS={'testjob': {'tasks': ['importer.apps.core.tests.test_task']}})
class ProcessJobTestCase(TestCase):

    def test_process_job(self):
        job = Job.objects.create(name='testjob')
        process_job()
        job = Job.objects.get()
        self.assertEqual(job.state, Job.STATES.COMPLETE)


@override_settings(JOBS={'testjob': {'tasks': ['importer.apps.core.tests.test_task'], 'creation_hook': 'importer.apps.core.tests.creation_hook'}})
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


@override_settings(JOBS={'testjob': {'tasks': ['importer.apps.core.tests.failing_task'], 'failure_hook': 'importer.apps.core.tests.failure_hook'}})
class JobFailureHookTestCase(TestCase):

    def test_failure_hook(self):
        job = Job.objects.create(name='testjob')
        process_job()
        job = Job.objects.get()
        self.assertEqual(job.state, Job.STATES.FAILED)
        self.assertEqual(job.workspace['output'], 'failure hook ran')


@override_settings(JOBS={'testjob': {'tasks': ['importer.apps.core.tests.workspace_test_task']}})
class WorkspaceTestCase(APITestCase):

    def test_basic_args(self):
        url = reverse('create_job')
        self.client.post(url, {'name': 'testjob', 'workspace': '{"input": "input"}'})
        process_job()
        job = Job.objects.get()
        self.assertEqual(job.workspace['output'], 'input-output')

    def test_json_post(self):
        """Ensures that we can also create a workspace by sending JSON"""
        url = reverse('create_job')
        self.client.post(url, {'name': 'testjob', 'workspace': {'input': 'input'}}, format='json')
        process_job()
        job = Job.objects.get()
        self.assertEqual(job.workspace['output'], 'input-output')


class RequestsStorageTestCase(LiveServerTestCase):

    def test_requests_storage(self):
        session = Session()
        storage = SessionStorage(session)
        url = "%s/" % self.live_server_url
        session.get(url)
        request_list = storage.get_requests()
        self.assertEqual(len(request_list), 1)
        self.assertEqual(request_list[0]['request']['url'], url)
        self.assertEqual(request_list[0]['response']['status_code'], 200)

        for _ in range(5):
            session.get(url)

        request_list = storage.get_requests()
        self.assertEqual(len(request_list), 6)
