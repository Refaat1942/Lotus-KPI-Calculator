# KPI Web — VPS Deployment (PostgreSQL + 24h Backups)

The app stores KPI history in **PostgreSQL running in Docker** on the same VPS.
A **systemd timer** runs a `pg_dump` backup **every 24 hours**, storing dumps
locally on the VPS with automatic retention pruning.

```
KPI Flask app (gunicorn)  --psycopg2 127.0.0.1:5432-->  PostgreSQL (Docker: kpi-postgres)
kpi-backup.timer (24h) --> kpi-backup.service --> pg_dump (inside container) --> backups/*.dump
```

## Quick start: one-command deploy

If Docker is already installed on the VPS, you can deploy (or update) everything
with a single command from the app folder:

```bash
cd /opt/kpi-web        # your app folder
sudo ./deploy.sh
```

`deploy.sh` is safe to re-run any time. It:

1. Pulls the latest code (`main`)
2. Creates `.env` with strong random secrets on first run (prints the generated
   admin password once — save it), and keeps your existing `.env` on re-runs
3. Starts PostgreSQL in Docker and waits for it to be healthy
4. Creates/updates the Python virtualenv and installs dependencies
5. Installs/updates the systemd services (web app + 24h backup timer)
6. Restarts the web app and enables the 24-hour backup timer
7. Runs one backup immediately and prints status

You can override defaults with env vars, e.g.
`sudo APP_DIR=/srv/kpi APP_USER=kpi ./deploy.sh`.

If Docker is **not** installed yet, install it first:

```bash
curl -fsSL https://get.docker.com | sh
sudo systemctl enable --now docker
```

---

The manual steps below do the same thing, one piece at a time.

## 1. Prerequisites

Install Docker Engine + the Compose plugin (if not already present):

```bash
curl -fsSL https://get.docker.com | sh
sudo systemctl enable --now docker
```

## 2. App directory & environment

The app is expected at `/opt/kpi-web`. Copy the repo there, then create the
environment file from the template and fill in real values:

```bash
cd /opt/kpi-web
cp .env.example .env
# Edit .env: set a strong DB_PASSWORD, SECRET_KEY, KPI_ADMIN_PASS, etc.
nano .env
```

`.env` is used by both `docker-compose.yml` and the systemd services
(`EnvironmentFile=/opt/kpi-web/.env`). It is git-ignored — never commit it.

## 3. Start PostgreSQL (Docker)

```bash
cd /opt/kpi-web
docker compose up -d
docker compose ps          # kpi-postgres should be "healthy"
```

PostgreSQL is bound to `127.0.0.1:5432` only (not reachable from the public
internet). Data persists in the named volume `kpi_pgdata`.

## 4. Python environment

```bash
cd /opt/kpi-web
python3 -m venv venv
./venv/bin/pip install -r requirements-web.txt   # includes psycopg2-binary
```

## 5. Install & start systemd services

```bash
sudo cp kpi-web.service kpi-backup.service kpi-backup.timer /etc/systemd/system/
sudo systemctl daemon-reload

# Web app (auto-creates the kpi_records table on first start)
sudo systemctl enable --now kpi-web.service
sudo systemctl status kpi-web.service

# 24-hour backups
sudo systemctl enable --now kpi-backup.timer
```

> Note: `kpi-backup.service` runs `pg_dump` *inside* the `kpi-postgres`
> container via `docker exec`, so no PostgreSQL client is required on the host
> and the dump version always matches the server. The service user must be able
> to run `docker` (root, or a user in the `docker` group).

## 6. Verify backups

```bash
# Trigger one backup immediately
sudo systemctl start kpi-backup.service

# A new dump should appear
ls -lh /opt/kpi-web/backups/          # kpi_pg_YYYYmmdd_HHMMSS.dump + kpi_logic_*.json

# Confirm the next scheduled run is ~24h out
systemctl list-timers | grep kpi-backup
```

## 7. Restoring from a backup

Dumps use PostgreSQL custom format (`pg_restore`):

```bash
# Copy a dump into the container, then restore
docker cp backups/kpi_pg_YYYYmmdd_HHMMSS.dump kpi-postgres:/tmp/restore.dump
docker exec -e PGPASSWORD="$DB_PASSWORD" kpi-postgres \
  pg_restore --no-owner --clean --if-exists -U kpi -d kpi /tmp/restore.dump
```

## Notes

- **Backups are local to the VPS** with retention controlled by
  `BACKUP_RETENTION_DAYS` (default 30). Files older than that are pruned on each run.
- **Backup interval** is fixed at 24h by `kpi-backup.timer`
  (`OnUnitActiveSec=24h`, `Persistent=true` so a missed run catches up on boot).
- Scheduling is done by systemd. The in-app backup thread is disabled unless you
  set `ENABLE_INAPP_BACKUP=1` (avoids duplicate dumps).
- Migration is a **fresh start** — no data is copied from the old SQLite
  `kpi_history.db`, which remains untouched on disk as a safety copy.
