"""Logical backups for AUB Collab: export, verify, restore and prune.

A backup is one gzip file holding a manifest and every row the app owns, in Django's fixture
format. Because it is logical (not a copy of SQLite or PostgreSQL files) a backup taken on
one database restores on the other, which also makes it the way to move servers.

Each backup gets a .sha256 file next to it. Restores refuse a backup whose checksum does not
match, so a corrupted or tampered file is never loaded.
"""
import gzip
import hashlib
import io
import json
import os
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import django
from django.core import management
from django.db import connection, transaction
from django.db.migrations.recorder import MigrationRecorder

FORMAT_VERSION = 1
PREFIX = "aubcollab-"
SUFFIX = ".json.gz"
STAMP = "%Y%m%dT%H%M%S.%fZ"

# Rebuilt automatically by migrate, or not worth keeping.
EXCLUDED = ["contenttypes", "auth.permission", "sessions", "admin.logentry"]


class BackupError(Exception):
    pass


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _applied_migrations():
    applied = {}
    for app, name in MigrationRecorder(connection).applied_migrations():
        applied.setdefault(app, []).append(name)
    return {app: sorted(names) for app, names in sorted(applied.items())}


def create_backup(directory, now=None):
    """Write a new backup into directory and return its path."""
    now = now or datetime.now(timezone.utc)
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)

    buffer = io.StringIO()
    management.call_command(
        "dumpdata",
        exclude=EXCLUDED,
        natural_foreign=True,
        natural_primary=True,
        stdout=buffer,
    )
    rows = json.loads(buffer.getvalue() or "[]")

    payload = {
        "manifest": {
            "format": FORMAT_VERSION,
            "created_at": now.isoformat(),
            "django": django.get_version(),
            "database_vendor": connection.vendor,
            "migrations": _applied_migrations(),
            "row_counts": dict(Counter(row["model"] for row in rows)),
        },
        "data": rows,
    }

    # Microseconds in the name, so two backups in the same second never overwrite each other.
    path = directory / f"{PREFIX}{now.strftime(STAMP)}{SUFFIX}"
    tmp = path.with_suffix(".partial")
    with gzip.open(tmp, "wt", encoding="utf-8") as fh:
        json.dump(payload, fh)
    os.replace(tmp, path)  # never leave a half written backup under the final name
    Path(f"{path}.sha256").write_text(f"{_sha256(path)}  {path.name}\n")
    return path


def read_backup(path):
    """Verify the checksum and structure, then return the payload. Raises BackupError."""
    path = Path(path)
    if not path.exists():
        raise BackupError(f"{path} does not exist")
    checksum_file = Path(f"{path}.sha256")
    if not checksum_file.exists():
        raise BackupError(f"Missing checksum file {checksum_file.name}")
    expected = checksum_file.read_text().split()[0]
    if _sha256(path) != expected:
        raise BackupError("Checksum mismatch: the backup is corrupted or was modified")
    try:
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            payload = json.load(fh)
    except (OSError, ValueError) as exc:
        raise BackupError(f"Unreadable backup: {exc}")
    if payload.get("manifest", {}).get("format") != FORMAT_VERSION or "data" not in payload:
        raise BackupError("Not an AUB Collab backup, or a format this version cannot read")
    return payload


def missing_migrations(manifest):
    """Migrations the backup was taken with that this database does not have yet."""
    current = _applied_migrations()
    missing = []
    for app, names in manifest["migrations"].items():
        for name in names:
            if name not in current.get(app, []):
                missing.append(f"{app}.{name}")
    return missing


def restore_backup(path):
    """Replace every row the app owns with the backup's contents, in one transaction."""
    payload = read_backup(path)
    missing = missing_migrations(payload["manifest"])
    if missing:
        raise BackupError(
            "This database is behind the backup. Run `python manage.py migrate` first. Missing: "
            + ", ".join(missing[:5])
        )

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as fh:
        json.dump(payload["data"], fh)
        fixture = fh.name
    try:
        with transaction.atomic():
            management.call_command("flush", interactive=False, verbosity=0)
            if payload["data"]:
                management.call_command("loaddata", fixture, verbosity=0)
    finally:
        os.unlink(fixture)
    return payload["manifest"]


def list_backups(directory):
    directory = Path(directory)
    if not directory.exists():
        return []
    return sorted(directory.glob(f"{PREFIX}*{SUFFIX}"))


def _timestamp(path):
    stamp = path.name[len(PREFIX) : -len(SUFFIX)]
    return datetime.strptime(stamp, STAMP).replace(tzinfo=timezone.utc)


def backups_to_keep(paths, daily=7, weekly=4, monthly=6):
    """Grandfather, father, son retention: newest backup of each recent day, week and month."""
    keep = set()
    seen = {"day": set(), "week": set(), "month": set()}
    limits = {"day": daily, "week": weekly, "month": monthly}
    for path in sorted(paths, key=_timestamp, reverse=True):
        when = _timestamp(path)
        buckets = {
            "day": when.date(),
            "week": tuple(when.isocalendar())[:2],
            "month": (when.year, when.month),
        }
        for kind, bucket in buckets.items():
            if bucket not in seen[kind] and len(seen[kind]) < limits[kind]:
                seen[kind].add(bucket)
                keep.add(path)
    return keep


def prune_backups(directory, daily=7, weekly=4, monthly=6):
    """Delete backups outside the retention policy. Returns the deleted paths."""
    paths = list_backups(directory)
    keep = backups_to_keep(paths, daily, weekly, monthly)
    deleted = []
    for path in paths:
        if path not in keep:
            path.unlink()
            Path(f"{path}.sha256").unlink(missing_ok=True)
            deleted.append(path)
    return deleted
