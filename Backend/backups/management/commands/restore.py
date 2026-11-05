"""python manage.py restore <file> --yes  Replaces all data with a backup's contents."""
from django.core.management.base import BaseCommand, CommandError

from backups.core import BackupError, read_backup, restore_backup


class Command(BaseCommand):
    help = "Restore a backup. Deletes the current data first, all in one transaction."

    def add_arguments(self, parser):
        parser.add_argument("path", help="Backup file (.json.gz)")
        parser.add_argument("--yes", action="store_true", help="Confirm replacing the current data")

    def handle(self, *args, path, yes=False, **options):
        try:
            manifest = read_backup(path)["manifest"]
        except BackupError as exc:
            raise CommandError(str(exc))

        rows = sum(manifest["row_counts"].values())
        self.stdout.write(f"Backup from {manifest['created_at']} ({manifest['database_vendor']}), {rows} rows")
        if not yes:
            raise CommandError("This deletes all current data. Run again with --yes to confirm.")

        try:
            restore_backup(path)
        except BackupError as exc:
            raise CommandError(str(exc))
        self.stdout.write(self.style.SUCCESS("Restore complete"))
