from django.db import models
from django.utils import timezone


class Job(models.Model):
    """One unit of background work, stored in the database until a worker runs it."""

    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"

    task = models.CharField(max_length=200, help_text="Registered task name, e.g. notifications.send_email")
    args = models.JSONField(default=list, blank=True)
    kwargs = models.JSONField(default=dict, blank=True)
    queue = models.CharField(max_length=50, default="default", db_index=True)
    priority = models.SmallIntegerField(default=0, help_text="Higher runs first")

    status = models.CharField(max_length=10, choices=Status.choices, default=Status.QUEUED)
    run_at = models.DateTimeField(default=timezone.now, help_text="Do not run before this time")
    attempts = models.PositiveSmallIntegerField(default=0)
    max_attempts = models.PositiveSmallIntegerField(default=3)

    locked_by = models.CharField(max_length=100, blank=True)
    locked_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)
    result = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-priority", "run_at", "id"]
        indexes = [
            # The worker's main query: queued jobs in a queue that are due, best first.
            models.Index(fields=["status", "queue", "run_at"], name="jobs_due_idx"),
        ]

    def __str__(self):
        return f"{self.task} #{self.pk} ({self.status})"
