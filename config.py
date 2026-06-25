import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "lotus-kpi-change-me-on-production")
    ADMIN_USER = os.environ.get("KPI_ADMIN_USER", "admin")
    ADMIN_PASS = os.environ.get("KPI_ADMIN_PASS", "admin")
    DB_PATH = os.path.join(BASE_DIR, "kpi_history.db")
    LOGIC_FILE = os.path.join(BASE_DIR, "kpi_logic.json")
    DATA_CACHE = os.path.join(BASE_DIR, "data_cache")
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024
