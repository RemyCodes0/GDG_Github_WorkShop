from datetime import timedelta
from io import StringIO

from django.core.management import call_command
from django.db import transaction
from django.test import TestCase
from django.utils import timezone

from .models import Job
from .tasks import get_task, retry_delay, task
from .worker import claim_next, requeue_stale, work_once

CALLS = []


@task(name="tests.add")
def add(a, b):
    CALLS.append(("add", a, b))
    return a + b


@task(name="tests.flaky", max_attempts=2)
def flaky():
    raise RuntimeError("service unavailable")


@task(name="tests.email", queue="emails")
def send_email(to):
    CALLS.append(("email", to))


@task(name="tests.urgent", priority=10)
def urgent():
    CALLS.append(("urgent",))


class EnqueueTests(TestCase):
    def setUp(self):
        CALLS.clear()

    def test_enqueue_stores_a_queued_job(self):
        job = add.enqueue(2, b=3)

        job.refresh_from_db()
        self.assertEqual(job.task, "tests.add")
        self.assertEqual(job.args, [2])
        self.assertEqual(job.kwargs, {"b": 3})
        self.assertEqual(job.status, Job.Status.QUEUED)
        self.assertEqual(CALLS, [])

    def test_calling_a_task_directly_runs_it_now(self):
        self.assertEqual(add(1, 1), 2)
        self.assertEqual(Job.objects.count(), 0)

    def test_rolled_back_transaction_removes_its_jobs(self):
        class Rollback(Exception):
            pass

        try:
            with transaction.atomic():
                add.enqueue(1, 2)
                raise Rollback
        except Rollback:
            pass

        self.assertEqual(Job.objects.count(), 0)

    def test_unknown_task_name(self):
        with self.assertRaises(LookupError):
            get_task("nope.missing")


class WorkerTests(TestCase):
    def setUp(self):
        CALLS.clear()

    def test_runs_job_and_stores_result(self):
        job = add.enqueue(2, 3)

        done = work_once()

        self.assertEqual(done.pk, job.pk)
        done.refresh_from_db()
        self.assertEqual(done.status, Job.Status.SUCCEEDED)
        self.assertEqual(done.result, 5)
        self.assertEqual(done.attempts, 1)
        self.assertIsNotNone(done.finished_at)
        self.assertEqual(CALLS, [("add", 2, 3)])

    def test_nothing_due_returns_none(self):
        self.assertIsNone(work_once())

    def test_delayed_jobs_wait_until_due(self):
        job = add.enqueue(1, 1, delay=timedelta(minutes=10))

        self.assertIsNone(work_once())

        Job.objects.filter(pk=job.pk).update(run_at=timezone.now() - timedelta(seconds=1))
        self.assertEqual(work_once().status, Job.Status.SUCCEEDED)

    def test_failed_job_is_retried_with_backoff(self):
        job = flaky.enqueue()

        with self.assertLogs("aubcollab.jobs", level="WARNING"):
            work_once()

        job.refresh_from_db()
        self.assertEqual(job.status, Job.Status.QUEUED)
        self.assertEqual(job.attempts, 1)
        self.assertIn("service unavailable", job.last_error)
        self.assertGreater(job.run_at, timezone.now() + timedelta(seconds=20))

    def test_job_fails_for_good_after_max_attempts(self):
        job = flaky.enqueue()
        with self.assertLogs("aubcollab.jobs", level="WARNING"):
            work_once()
        Job.objects.filter(pk=job.pk).update(run_at=timezone.now())

        with self.assertLogs("aubcollab.jobs", level="ERROR"):
            work_once()

        job.refresh_from_db()
        self.assertEqual(job.status, Job.Status.FAILED)
        self.assertEqual(job.attempts, 2)
        self.assertIsNotNone(job.finished_at)

    def test_unregistered_task_fails_without_crashing_the_worker(self):
        Job.objects.create(task="removed.task", max_attempts=1)

        with self.assertLogs("aubcollab.jobs", level="ERROR"):
            job = work_once()

        self.assertEqual(job.status, Job.Status.FAILED)
        self.assertIn("No task registered", job.last_error)

    def test_higher_priority_runs_first(self):
        add.enqueue(1, 1)
        urgent.enqueue()

        self.assertEqual(work_once().task, "tests.urgent")

    def test_workers_only_take_their_queues(self):
        send_email.enqueue("student@mail.aub.edu")

        self.assertIsNone(work_once(queues=("default",)))
        self.assertEqual(work_once(queues=("emails",)).status, Job.Status.SUCCEEDED)

    def test_a_job_is_claimed_only_once(self):
        add.enqueue(1, 1)

        first = claim_next(worker="worker-a")
        second = claim_next(worker="worker-b")

        self.assertIsNotNone(first)
        self.assertEqual(first.locked_by, "worker-a")
        self.assertIsNone(second)

    def test_stale_running_jobs_are_requeued(self):
        job = add.enqueue(1, 1)
        claim_next(worker="crashed")
        Job.objects.filter(pk=job.pk).update(locked_at=timezone.now() - timedelta(hours=1))

        with self.assertLogs("aubcollab.jobs", level="WARNING"):
            self.assertEqual(requeue_stale(), 1)

        job.refresh_from_db()
        self.assertEqual(job.status, Job.Status.QUEUED)
        self.assertEqual(job.locked_by, "")

    def test_backoff_grows_and_is_capped(self):
        self.assertEqual(retry_delay(1), timedelta(seconds=30))
        self.assertEqual(retry_delay(2), timedelta(minutes=2))
        self.assertEqual(retry_delay(10), timedelta(hours=1))


class RunJobsCommandTests(TestCase):
    def test_burst_mode_runs_everything_due_then_exits(self):
        add.enqueue(1, 2)
        add.enqueue(3, 4)
        out = StringIO()

        call_command("runjobs", "--burst", stdout=out)

        self.assertEqual(Job.objects.filter(status=Job.Status.SUCCEEDED).count(), 2)
        self.assertIn("stopped after 2 job(s)", out.getvalue())
