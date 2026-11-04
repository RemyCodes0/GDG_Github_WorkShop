from django.contrib import admin
from django.utils import timezone

from .models import Job


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ("id", "task", "queue", "status", "attempts", "max_attempts", "run_at", "finished_at")
    list_filter = ("status", "queue", "task")
    search_fields = ("task", "last_error")
    readonly_fields = ("created_at", "finished_at", "locked_by", "locked_at", "last_error", "result")
    actions = ["retry_now"]

    @admin.action(description="Retry selected jobs now")
    def retry_now(self, request, queryset):
        count = queryset.exclude(status=Job.Status.RUNNING).update(
            status=Job.Status.QUEUED, run_at=timezone.now(), attempts=0, last_error=""
        )
        self.message_user(request, f"{count} job(s) queued again.")
