"""Automatic backup for the KPI PostgreSQL database and logic file.

The database runs in a Docker container on the same VPS, so backups are taken
by running ``pg_dump`` *inside* that container via ``docker exec``. This keeps
the pg_dump client version perfectly matched to the server and avoids needing a
PostgreSQL client installed on the host.

Scheduling is handled by systemd (``kpi-backup.timer``) every 24 hours. The
in-app background scheduler is disabled by default (enable it by setting the
env var ``ENABLE_INAPP_BACKUP=1``) to avoid producing duplicate dumps.
"""
import os
import shutil
import subprocess
import threading
import time
from datetime import datetime, timedelta

from config import Config

_lock = threading.Lock()
_last_backup_at = None


def _run_pg_dump(dst_path):
    """Dump the database into dst_path (custom format) using docker exec pg_dump.

    Returns True on success, raises CalledProcessError on failure.
    """
    cmd = [
        "docker", "exec",
        "-e", f"PGPASSWORD={Config.DB_PASSWORD}",
        Config.PG_CONTAINER,
        "pg_dump",
        "--format=custom",
        "--no-owner",
        "-U", Config.DB_USER,
        "-d", Config.DB_NAME,
    ]
    with open(dst_path, "wb") as out:
        subprocess.run(cmd, stdout=out, stderr=subprocess.PIPE, check=True)
    return True


def run_backup():
    """Backup PostgreSQL DB and kpi_logic.json. Returns path to DB dump or None."""
    global _last_backup_at
    os.makedirs(Config.BACKUP_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    db_dst = None

    with _lock:
        db_dst = os.path.join(Config.BACKUP_DIR, f"kpi_pg_{ts}.dump")
        try:
            _run_pg_dump(db_dst)
        except subprocess.CalledProcessError as exc:
            if os.path.exists(db_dst):
                os.remove(db_dst)
            stderr = exc.stderr.decode("utf-8", "replace") if exc.stderr else ""
            raise RuntimeError(f"pg_dump failed: {stderr.strip()}") from exc

        if os.path.exists(Config.LOGIC_FILE):
            shutil.copy2(
                Config.LOGIC_FILE,
                os.path.join(Config.BACKUP_DIR, f"kpi_logic_{ts}.json"),
            )

        _prune_old_backups()
        _last_backup_at = datetime.now()

    return db_dst


def _prune_old_backups():
    cutoff = datetime.now() - timedelta(days=Config.BACKUP_RETENTION_DAYS)
    if not os.path.isdir(Config.BACKUP_DIR):
        return
    for name in os.listdir(Config.BACKUP_DIR):
        path = os.path.join(Config.BACKUP_DIR, name)
        if not os.path.isfile(path):
            continue
        try:
            mtime = datetime.fromtimestamp(os.path.getmtime(path))
            if mtime < cutoff:
                os.remove(path)
        except OSError:
            pass


def list_backups():
    """Return backup files newest first: [{name, path, size_kb, mtime}, ...]"""
    if not os.path.isdir(Config.BACKUP_DIR):
        return []
    items = []
    for name in os.listdir(Config.BACKUP_DIR):
        path = os.path.join(Config.BACKUP_DIR, name)
        if os.path.isfile(path):
            items.append({
                "name": name,
                "path": path,
                "size_kb": round(os.path.getsize(path) / 1024, 1),
                "mtime": datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M"),
            })
    items.sort(key=lambda x: x["name"], reverse=True)
    return items


def get_last_backup_time():
    if _last_backup_at:
        return _last_backup_at.strftime("%Y-%m-%d %H:%M")
    backups = list_backups()
    if backups:
        return backups[0]["mtime"]
    return "Never"


def start_backup_scheduler(app=None):
    """Optional in-app backup loop (disabled unless ENABLE_INAPP_BACKUP=1).

    Scheduling is normally done by systemd (kpi-backup.timer). This exists as a
    fallback for environments without systemd.
    """
    if os.environ.get("ENABLE_INAPP_BACKUP", "0") != "1":
        return None

    def loop():
        time.sleep(10)
        while True:
            try:
                run_backup()
                if app:
                    app.logger.info("KPI database backup completed")
            except Exception as exc:
                if app:
                    app.logger.error("KPI backup failed: %s", exc)
            time.sleep(Config.BACKUP_INTERVAL_HOURS * 3600)

    t = threading.Thread(target=loop, daemon=True, name="kpi-backup")
    t.start()
    return t


if __name__ == "__main__":
    path = run_backup()
    print(f"Backup written to: {path}" if path else "Backup produced no file.")
