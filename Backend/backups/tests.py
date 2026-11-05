import gzip
import json
import tempfile
from datetime import datetime, timedelta, timezone
from io import StringIO
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, TransactionTestCase

from .core import STAMP, BackupError, backups_to_keep, create_backup, list_backups, prune_backups, read_backup, restore_backup

User = get_user_model()


class BackupRestoreTests(TransactionTestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())

    def test_backup_contains_data_and_manifest(self):
        User.objects.create_user("leen", email="leen@mail.aub.edu", password="unused-test-password")

        path = create_backup(self.dir)
        payload = read_backup(path)

        self.assertTrue(path.name.startswith("aubcollab-") and path.name.endswith(".json.gz"))
        self.assertTrue(Path(f"{path}.sha256").exists())
        self.assertEqual(payload["manifest"]["row_counts"]["auth.user"], 1)
        self.assertIn("auth", payload["manifest"]["migrations"])

    def test_restore_brings_back_deleted_data(self):
        User.objects.create_user("remy", password="unused-test-password")
        User.objects.create_user("zeina", password="unused-test-password")
        path = create_backup(self.dir)

        User.objects.filter(username="remy").delete()
        User.objects.create_user("intruder", password="unused-test-password")

        restore_backup(path)

        self.assertEqual(sorted(User.objects.values_list("username", flat=True)), ["remy", "zeina"])

    def test_restored_passwords_still_work(self):
        User.objects.create_user("acile", password="correct-horse-battery")
        path = create_backup(self.dir)
        User.objects.all().delete()

        restore_backup(path)

        self.assertTrue(User.objects.get(username="acile").check_password("correct-horse-battery"))

    def test_tampered_backup_is_refused(self):
        path = create_backup(self.dir)
        with gzip.open(path, "wt") as fh:
            json.dump({"manifest": {"format": 1}, "data": []}, fh)

        with self.assertRaisesMessage(BackupError, "Checksum mismatch"):
            read_backup(path)

    def test_backup_without_checksum_is_refused(self):
        path = create_backup(self.dir)
        Path(f"{path}.sha256").unlink()

        with self.assertRaises(BackupError):
            read_backup(path)

    def test_restore_refuses_backup_from_a_newer_schema(self):
        path = create_backup(self.dir)
        with gzip.open(path, "rt") as fh:
            payload = json.load(fh)
        payload["manifest"]["migrations"]["future_app"] = ["0001_initial"]
        with gzip.open(path, "wt") as fh:
            json.dump(payload, fh)
        from .core import _sha256

        Path(f"{path}.sha256").write_text(f"{_sha256(path)}  {path.name}\n")

        with self.assertRaisesMessage(BackupError, "migrate"):
            restore_backup(path)


class CommandTests(TransactionTestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())

    def test_backup_command_verifies(self):
        out = StringIO()
        call_command("backup", "--dir", str(self.dir), stdout=out)

        self.assertIn("verified", out.getvalue())
        self.assertEqual(len(list_backups(self.dir)), 1)

    def test_restore_requires_confirmation(self):
        path = create_backup(self.dir)

        with self.assertRaisesMessage(CommandError, "--yes"):
            call_command("restore", str(path), stdout=StringIO())

    def test_restore_with_confirmation(self):
        User.objects.create_user("leen", password="unused-test-password")
        path = create_backup(self.dir)
        User.objects.all().delete()

        call_command("restore", str(path), "--yes", stdout=StringIO())

        self.assertTrue(User.objects.filter(username="leen").exists())

    def test_listbackups_flags_broken_files(self):
        good = create_backup(self.dir, now=datetime(2026, 11, 1, tzinfo=timezone.utc))
        bad = create_backup(self.dir, now=datetime(2026, 11, 2, tzinfo=timezone.utc))
        Path(f"{bad}.sha256").write_text("0" * 64)
        out = StringIO()

        call_command("listbackups", "--dir", str(self.dir), stdout=out)

        self.assertIn(f"OK      {good.name}", out.getvalue())
        self.assertIn(f"BROKEN  {bad.name}", out.getvalue())


class RetentionTests(SimpleTestCase):
    def _paths(self, days):
        start = datetime(2026, 11, 5, 3, 0, tzinfo=timezone.utc)
        return [Path(f"aubcollab-{(start - timedelta(days=d)).strftime(STAMP)}.json.gz") for d in range(days)]

    def test_keeps_recent_days_weeks_and_months(self):
        paths = self._paths(120)

        keep = backups_to_keep(paths, daily=7, weekly=4, monthly=3)

        newest_seven = paths[:7]
        self.assertTrue(set(newest_seven) <= keep)
        self.assertLessEqual(len(keep), 7 + 4 + 3)
        self.assertNotIn(paths[-1], keep)

    def test_prune_deletes_files_and_checksums(self):
        directory = Path(tempfile.mkdtemp())
        for path in self._paths(10):
            (directory / path.name).write_text("x")
            (directory / f"{path.name}.sha256").write_text("x")

        deleted = prune_backups(directory, daily=3, weekly=0, monthly=0)

        self.assertEqual(len(deleted), 7)
        self.assertEqual(len(list_backups(directory)), 3)
        self.assertEqual(len(list(directory.glob("*.sha256"))), 3)
