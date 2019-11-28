from time import sleep

from django_dbq.models import Job


def test_task(job):
    print("going to sleep")
    sleep(45)
    print("running job")
    Job.objects.filter(id=1)
