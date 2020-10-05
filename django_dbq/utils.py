import asyncio


def run_job(job_function, *args, **kwargs):
    if asyncio.iscoroutinefunction(job_function):
        asyncio.run(job_function(*args, **kwargs))
    else:
        job_function(*args, **kwargs)
