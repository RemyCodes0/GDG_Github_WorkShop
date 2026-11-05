"""python manage.py backup  Takes a backup, verifies it, and applies the retention policy."""
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from backups.core import BackupError, create_backup, prune_backups, read_backup


class Command(BaseCommand):
    help = "Create a verified backup of all AUB Collab data."

    def add_arguments(self, parser):
        parser.add_argument("--dir", default=None, help="Backup folder (default: BACKUP_DIR)")
        parser.add_argument("--no-prune", action="store_true", help="Keep every old backup")

    def handle(self, *args, dir=None, no_prune=False, **options):
        directory = dir or settings.BACKUP_DIR
        path = create_backup(directory)
        try:
            manifest = read_backup(path)["manifest"]
        except BackupError as exc:
            raise CommandError(f"Backup written but failed verification: {exc}")

        rows = sum(manifest["row_counts"].values())
        self.stdout.write(self.style.SUCCESS(f"Backup {path.name}: {rows} rows, verified"))

        if not no_prune:
            retention = settings.BACKUP_RETENTION
            for old in prune_backups(directory, **retention):
                self.stdout.write(f"  removed old backup {old.name}")
