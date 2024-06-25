from django.conf import settings


TASK_LIST_KEY = "tasks"
PRE_TASK_HOOK_KEY = "pre_task_hook"
POST_TASK_HOOK_KEY = "post_task_hook"
FAILURE_HOOK_KEY = "failure_hook"
CREATION_HOOK_KEY = "creation_hook"


def get_next_task_name(job_name, current_task=None):
    """Given a job name and (optionally) a task name, return the
    next task in the list. If the current_task is None, return the
    first task. If current_task is the last task in the list, return None"""

    task_list = settings.JOBS[job_name][TASK_LIST_KEY]

    if current_task is None:
        return task_list[0]

    next_task_index = task_list.index(current_task) + 1

    try:
        return task_list[next_task_index]
    except IndexError:
        return None


def get_pre_task_hook_name(job_name):
    """Return the name of the pre task hook for the given job (as a string) or None"""
    return settings.JOBS[job_name].get(PRE_TASK_HOOK_KEY)


def get_post_task_hook_name(job_name):
    """Return the name of the post_task hook for the given job (as a string) or None"""
    return settings.JOBS[job_name].get(POST_TASK_HOOK_KEY)


def get_failure_hook_name(job_name):
    """Return the name of the failure hook for the given job (as a string) or None"""
    return settings.JOBS[job_name].get(FAILURE_HOOK_KEY)


def get_creation_hook_name(job_name):
    """Return the name of the creation hook for the given job (as a string) or None"""
    return settings.JOBS[job_name].get(CREATION_HOOK_KEY)
