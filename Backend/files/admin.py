from django.contrib import admin

from .models import StoredFile


@admin.register(StoredFile)
class StoredFileAdmin(admin.ModelAdmin):
    list_display = ("original_name", "owner", "content_type", "size", "created_at")
    list_filter = ("content_type",)
    search_fields = ("original_name", "owner__username", "sha256")
    readonly_fields = ("id", "owner", "file", "original_name", "extension", "content_type", "size", "sha256", "created_at")
