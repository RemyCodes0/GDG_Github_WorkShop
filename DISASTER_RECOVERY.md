# Disaster Recovery

How AUB Collab protects its data, and exactly what to do when something goes wrong.

## Targets

| | Target | How |
| --- | --- | --- |
| **RPO** (data we can afford to lose) | at most 24 hours, 1 hour once scheduled hourly | scheduled `manage.py backup` |
| **RTO** (time to be back online) | under 1 hour | one command restore onto a fresh server |

## How backups work

`python manage.py backup` writes one file such as `aubcollab-20261105T030000.000000Z.json.gz` to `BACKUP_DIR`:

* **Logical, not a disk copy.** It holds every row the app owns (users, projects, applications, jobs, ...) in Django's fixture format, so a backup from SQLite restores into PostgreSQL and the other way around. This is also how to move to a new server or database.
* **Self describing.** A manifest records when it was taken, the Django version, the database type, the applied migrations and a row count per table.
* **Verified.** A `.sha256` checksum is written next to every backup and the backup is read back immediately. Restores refuse any file whose checksum does not match.
* **Atomic.** It is written under a temporary name first, so a crash never leaves a half written file that looks valid.
* **Retention.** After each backup, old ones are pruned: the newest backup of each of the last 7 days, 4 weeks and 6 months are kept (`BACKUP_KEEP_DAILY`, `BACKUP_KEEP_WEEKLY`, `BACKUP_KEEP_MONTHLY`).

## Setting it up

1. Point `BACKUP_DIR` at storage that is **not on the same disk as the database**: a mounted network volume, or a folder synced to object storage (S3, Google Cloud Storage, a university file share).
2. Schedule it. With cron on the server:

   ```cron
   15 3 * * *  cd /srv/aubcollab/Backend && python manage.py backup >> /var/log/aubcollab-backup.log 2>&1
   ```

   With Docker Compose: `docker compose exec -T backend python manage.py backup`.
3. Check backups weekly, or let monitoring do it:

   ```bash
   python manage.py listbackups
   # OK      aubcollab-20261105T031500.000000Z.json.gz  4812 rows
   ```

## Runbooks

### Data was deleted or corrupted by mistake

1. Put the site in maintenance (stop the web container or scale `backend` to 0) so no new writes arrive.
2. Take a backup of the current state anyway: `python manage.py backup --no-prune`. It may contain changes you want later.
3. Pick the newest good backup with `python manage.py listbackups`.
4. Restore it. This deletes current data and loads the backup in **one transaction**, so it either fully succeeds or changes nothing:

   ```bash
   python manage.py restore /path/to/aubcollab-YYYYMMDDTHHMMSS.ffffffZ.json.gz --yes
   ```

5. Bring the site back and tell affected students what period of changes was lost.

### The server or database is gone

1. Start a fresh server with the same code version (`git checkout <tag>`), or follow `DEPLOYMENT.md`.
2. Create the empty schema: `python manage.py migrate`.
3. Copy the newest backup and its `.sha256` file from off site storage.
4. `python manage.py restore <file> --yes`
5. Create or check the admin account and point DNS at the new server.

### Restore says "This database is behind the backup"

The backup was taken by a newer version of the code. Deploy that version (or newer), run `python manage.py migrate`, then restore again.

### Restore says "Checksum mismatch"

The file is damaged or was changed. Do not force it. Use the previous backup, and investigate the storage.

## Practise it

A backup that has never been restored is a hope, not a plan. Once a month, on a test machine or a fresh local checkout (never on production):

```bash
python manage.py migrate
python manage.py restore <newest backup> --yes
python manage.py runserver
```

Log in, click around, and note how long it took. That is the real RTO.
