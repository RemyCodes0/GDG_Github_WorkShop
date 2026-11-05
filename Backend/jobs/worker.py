"""The job worker: claims due jobs one at a time, runs them, records the outcome.

Claiming is safe with several workers at once. On PostgreSQL it uses SELECT ... FOR UPDATE
SKIP LOCKED, so workers never wait on each other. Elsewhere (SQLite in development) it uses a
conditional UPDATE, so only one worker can move a job from queued to running.
"""
import json
import logging
import os
import socket
import traceback
from datetime import timedelta

from django.db import connection, transaction
from django.utils import timezone

from .models import Job
from .tasks import get_task, retry_delay

logger = logging.getLogger("aubcollab.jobs")

# A job left "running" this long was on a worker that crashed; it is put back in the queue.
STALE_AFTER = timedelta(minutes=30)


def worker_id():
    return f"{socket.gethostname()}:{os.getpid()}"[:100]


def _due(queues):
    return Job.objects.filter(status=Job.Status.QUEUED, queue__in=queues, run_at__lte=timezone.now())


def claim_next(queues=("default",), worker=None):
    worker = worker or worker_id()
    now = timezone.now()

    if connection.features.has_select_for_update_skip_locked:
        with transaction.atomic():
            job = _due(queues).select_for_update(skip_locked=True).first()
            if job is None:
                return None
            job.status, job.locked_by, job.locked_at = Job.Status.RUNNING, worker, now
            job.attempts += 1
            job.save(update_fields=["status", "locked_by", "locked_at", "attempts"])
            return job

    for candidate in _due(queues).values_list("pk", "attempts")[:5]:
        pk, attempts = candidate
        claimed = Job.objects.filter(pk=pk, status=Job.Status.QUEUED).update(
            status=Job.Status.RUNNING, locked_by=worker, locked_at=now, attempts=attempts + 1
        )
        if claimed:
            return Job.objects.get(pk=pk)
    return None


def run_job(job):
    """Run one claimed job and store the result. Never raises."""
    log_extra = {"job_id": job.pk, "task": job.task, "attempt": job.attempts}
    try:
        result = get_task(job.task).func(*job.args, **job.kwargs)
    except Exception as exc:
        job.last_error = "".join(traceback.format_exception(exc))[-5000:]
        job.locked_by, job.locked_at = "", None
        if job.attempts < job.max_attempts:
            job.status = Job.Status.QUEUED
            job.run_at = timezone.now() + retry_delay(job.attempts)
            logger.warning("Job %s failed, will retry", job.pk, extra=log_extra, exc_info=True)
        else:
            job.status = Job.Status.FAILED
            job.finished_at = timezone.now()
            logger.error("Job %s failed permanently", job.pk, extra=log_extra, exc_info=True)
        job.save()
        return job

    job.status = Job.Status.SUCCEEDED
    job.result = result if _is_json(result) else repr(result)
    job.finished_at = timezone.now()
    job.locked_by, job.locked_at = "", None
    job.save()
    logger.info("Job %s succeeded", job.pk, extra=log_extra)
    return job


def requeue_stale(now=None):
    """Put jobs whose worker died back in the queue. Returns how many were requeued."""
    cutoff = (now or timezone.now()) - STALE_AFTER
    count = Job.objects.filter(status=Job.Status.RUNNING, locked_at__lt=cutoff).update(
        status=Job.Status.QUEUED, locked_by="", locked_at=None
    )
    if count:
        logger.warning("Requeued %s stale jobs", count)
    return count


def work_once(queues=("default",), worker=None):
    """Claim and run at most one job. Returns the job, or None if nothing was due."""
    job = claim_next(queues, worker)
    return run_job(job) if job else None


def _is_json(value):
    try:
        json.dumps(value)
        return True
    except (TypeError, ValueError):
        return False
