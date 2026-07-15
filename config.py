import os
from urllib.parse import quote_plus

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "lotus-kpi-change-me-on-production")
    ADMIN_USER = os.environ.get("KPI_ADMIN_USER", "admin")
    ADMIN_PASS = os.environ.get("KPI_ADMIN_PASS", "admin")

    # PostgreSQL connection (Dockerized DB on the same VPS by default).
    DB_HOST = os.environ.get("DB_HOST", "127.0.0.1")
    DB_PORT = os.environ.get("DB_PORT", "5432")
    DB_NAME = os.environ.get("DB_NAME", "kpi")
    DB_USER = os.environ.get("DB_USER", "kpi")
    DB_PASSWORD = os.environ.get("DB_PASSWORD", "")

    # Full connection string (used by psycopg2 and pg_dump). Overridable via env.
    DATABASE_URL = os.environ.get(
        "DATABASE_URL",
        "postgresql://{user}:{pwd}@{host}:{port}/{db}".format(
            user=quote_plus(DB_USER),
            pwd=quote_plus(DB_PASSWORD),
            host=DB_HOST,
            port=DB_PORT,
            db=DB_NAME,
        ),
    )

    # Name of the Docker container running PostgreSQL (used by backups).
    PG_CONTAINER = os.environ.get("PG_CONTAINER", "kpi-postgres")

    LOGIC_FILE = os.path.join(BASE_DIR, "kpi_logic.json")
    DATA_CACHE = os.path.join(BASE_DIR, "data_cache")
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    BACKUP_DIR = os.path.join(BASE_DIR, "backups")
    BACKUP_INTERVAL_HOURS = int(os.environ.get("BACKUP_INTERVAL_HOURS", "24"))
    BACKUP_RETENTION_DAYS = int(os.environ.get("BACKUP_RETENTION_DAYS", "30"))
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024
