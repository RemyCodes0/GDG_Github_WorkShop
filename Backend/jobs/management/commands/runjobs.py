"""python manage.py runjobs  Starts a background job worker.

    python manage.py runjobs                    run forever, polling every 2 seconds
    python manage.py runjobs --queue emails     only work on one queue (repeatable)
    python manage.py runjobs --burst            run every due job, then exit (cron friendly)

Run as many workers as you like; each job is only ever claimed by one of them.
Stop with Ctrl+C or SIGTERM; the current job finishes first.
"""
import signal
import time

from django.core.management.base import BaseCommand

from jobs.worker import requeue_stale, work_once, worker_id


class Command(BaseCommand):
    help = "Run background jobs."

    def add_arguments(self, parser):
        parser.add_argument("--queue", action="append", dest="queues", help="Queue to work on (default: default)")
        parser.add_argument("--burst", action="store_true", help="Exit when no job is due")
        parser.add_argument("--sleep", type=float, default=2.0, help="Seconds to wait when idle")

    def handle(self, *args, queues=None, burst=False, sleep=2.0, **options):
        queues = tuple(queues or ["default"])
        self.stopping = False
        signal.signal(signal.SIGTERM, self._stop)
        signal.signal(signal.SIGINT, self._stop)

        me = worker_id()
        self.stdout.write(f"Worker {me} on queues: {', '.join(queues)}")
        processed = 0
        last_sweep = 0.0

        while not self.stopping:
            if time.monotonic() - last_sweep > 60:
                requeue_stale()
                last_sweep = time.monotonic()

            job = work_once(queues, me)
            if job is not None:
                processed += 1
                self.stdout.write(f"  {job.task} #{job.pk}: {job.status}")
                continue
            if burst:
                break
            time.sleep(sleep)

        self.stdout.write(self.style.SUCCESS(f"Worker stopped after {processed} job(s)"))

    def _stop(self, *_):
        self.stopping = True
