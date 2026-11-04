"""python manage.py listbackups  Shows every backup and whether it passes verification."""
from django.conf import settings
from django.core.management.base import BaseCommand

from backups.core import BackupError, list_backups, read_backup


class Command(BaseCommand):
    help = "List backups and verify each one."

    def add_arguments(self, parser):
        parser.add_argument("--dir", default=None, help="Backup folder (default: BACKUP_DIR)")

    def handle(self, *args, dir=None, **options):
        paths = list_backups(dir or settings.BACKUP_DIR)
        if not paths:
            self.stdout.write("No backups found")
            return
        for path in paths:
            try:
                manifest = read_backup(path)["manifest"]
                rows = sum(manifest["row_counts"].values())
                self.stdout.write(self.style.SUCCESS(f"OK      {path.name}  {rows} rows"))
            except BackupError as exc:
                self.stdout.write(self.style.ERROR(f"BROKEN  {path.name}  {exc}"))
