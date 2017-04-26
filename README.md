django-db-queue
==========
[![Build Status](https://travis-ci.org/dabapps/django-db-queue.svg)](https://travis-ci.org/dabapps/django-db-queue)
[![pypi release](https://img.shields.io/pypi/v/django-db-queue.svg)](https://pypi.python.org/pypi/django-db-queue)

Simple databased-backed job queue. Jobs are defined in your settings, and are processed by management commands.

Asynchronous tasks are run via a *job queue*. This system is designed to support multi-step job workflows.

Tested against Django 1.8, 1.9, 1.10, 1.11

## Getting Started

### Describe your job

In e.g. project.common.jobs:

```python
import time

def my_task(job):
    logger.info("Working hard...")
    time.sleep(10)
    logger.info("Job's done!")
```

### Set up your job

In project.settings:

```python
JOBS = {
    'my_job': ['project.common.jobs.my_task'],
}
```

### Start the worker

In another terminal:

`python manage.py worker`

### Create a job

Using the name you configured for your job in your settings, create an instance of Job.

```python
Job.objects.create(name='my_job')
```

## Terminology

### Job

The top-level abstraction of a standalone piece of work. Jobs are stored in the database (ie they are represented as Django model instances).

### Task

Jobs are processed to completion by *tasks*. These are simply Python functions, which must take a single argument - the `Job` instance being processed. A single job will often require processing by more than one task to be completed fully. Creating the task functions is the responsibility of the developer. For example:

    def my_task(job):
        logger.info("Doing some hard work")
        do_some_hard_work()

### Workspace

The *workspace* is an area that tasks within a single job can use to communicate with each other. It is implemented as a Python dictionary, available on the `job` instance passed to tasks as `job.workspace`. The initial workspace of a job can be empty, or can contain some parameters that the tasks require (for example, API access tokens, account IDs etc). A single task can edit the workspace, and the modified workspace will be passed on to the next task in the sequence. For example:

    def my_first_task(job):
        job.workspace['message'] = 'Hello, task 2!'

    def my_second_task(job):
        logger.info("Task 1 says: %s" % job.workspace['message'])

When creating a Job, the workspace is passed as a keyword argument:

```python
Job.objects.create(name='my_job', workspace={'key': value})
```

### Worker process

A *worker process* is a long-running process, implemented as a Django management command, which is responsible for executing the tasks associated with a job. There may be many worker processes running concurrently in the final system. Worker processes wait for a new job to be created in the database, and call the each associated task in the correct sequeunce.. A worker can be started using `python manage.py worker`, and a single worker instance is included in the development `procfile`.

### Configuration

Jobs are configured in the Django `settings.py` file. The `JOBS` setting is a dictionary mapping a *job name* (eg `import_cats`) to a *list* of one or more task function paths. For example:

    JOBS = {
        'import_cats': ['apps.cat_importer.import_cats.step_one', 'apps.cat_importer.import_cats.step_two'],
    }

### Job states

Jobs have a `state` field which can have one of the following values:

* `NEW` (has been created, waiting for a worker process to run the next task)
* `READY` (has run a task before, awaiting a worker process to run the next task)
* `PROCESSING` (a task is currently being processed by a worker)
* `COMPLETED` (all job tasks have completed successfully)
* `FAILED` (a job task failed)

### API

#### Management commands

There is a management command, `manage.py delete_old_jobs`, which deletes any
jobs from the database which are in state `COMPLETE` or `FAILED` and were
created more than 24 hours ago. This could be run, for example, as a cron task,
to ensure the jobs table remains at a reasonable size.

For debugging/development purposes, a simple management command is supplied to create jobs:

    manage.py create_job <job_name> --queue_name 'my_queue_name' --workspace '{"key": "value"}'

The `workspace` flag is optional. If supplied, it must be a valid JSON string.

`queue_name` is optional and defaults to `default`

To start a worker:

    manage.py worker [queue_name]

`queue_name` is optional, and will default to `default`

## Testing

It may be necessary to supply a DATABASE_PORT environment variable.
