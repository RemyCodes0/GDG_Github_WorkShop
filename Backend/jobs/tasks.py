"""Background jobs for AUB Collab: register a task once, queue it from anywhere.

    # notifications/tasks.py
    from jobs.tasks import task

    @task(max_attempts=5)
    def send_application_email(application_id):
        ...

    # in a view, after saving an application:
    send_application_email.enqueue(application.pk)

The web request returns at once; `python manage.py runjobs` picks the job up. The job is a row
in the same database, written in the same transaction as the data it is about: if that
transaction rolls back, the job disappears with it, and workers cannot see it before it commits.
Arguments must be JSON serializable (pass IDs, not objects).
"""
import logging
from datetime import timedelta

from django.utils import timezone

from .models import Job

logger = logging.getLogger("aubcollab.jobs")

_REGISTRY = {}


class UnknownTask(LookupError):
    pass


class Task:
    def __init__(self, func, name, queue, max_attempts, priority):
        self.func = func
        self.name = name
        self.queue = queue
        self.max_attempts = max_attempts
        self.priority = priority

    def __call__(self, *args, **kwargs):
        """Calling the task directly runs it now, in this process (handy in tests and shells)."""
        return self.func(*args, **kwargs)

    def enqueue(self, *args, delay=None, run_at=None, priority=None, **kwargs):
        """Queue the task and return the Job."""
        when = run_at or (timezone.now() + delay if delay else timezone.now())
        fields = {
            "task": self.name,
            "args": list(args),
            "kwargs": kwargs,
            "queue": self.queue,
            "priority": self.priority if priority is None else priority,
            "max_attempts": self.max_attempts,
            "run_at": when,
        }
        return Job.objects.create(**fields)


def task(func=None, *, name=None, queue="default", max_attempts=3, priority=0):
    def register(f):
        task_name = name or f"{f.__module__}.{f.__qualname__}"
        wrapped = Task(f, task_name, queue, max_attempts, priority)
        _REGISTRY[task_name] = wrapped
        return wrapped

    return register(func) if func is not None else register


def get_task(name):
    try:
        return _REGISTRY[name]
    except KeyError:
        raise UnknownTask(f"No task registered as {name!r}. Is the module that defines it imported?")


def retry_delay(attempt):
    """Exponential backoff: 30 s, 2 min, 8 min, ... capped at one hour."""
    return timedelta(seconds=min(30 * 4 ** (attempt - 1), 3600))
