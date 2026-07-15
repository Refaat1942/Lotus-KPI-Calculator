#!/usr/bin/env bash
#
# One-command deploy for the Lotus KPI app (PostgreSQL + 24h backups).
#
# Usage (run on the VPS, from the app folder):
#     sudo ./deploy.sh
#
# What it does (safe to re-run any time):
#   1. Pulls the latest code from git (branch: main)
#   2. Creates .env with strong random secrets on first run (kept on re-runs)
#   3. Starts PostgreSQL in Docker
#   4. Creates/updates the Python virtualenv and installs dependencies
#   5. Installs/updates the systemd services (web app + 24h backup timer)
#   6. Restarts the web app and enables the 24h backup timer
#   7. Runs one backup immediately and prints status
#
set -euo pipefail

# ---------------------------------------------------------------------------
# Settings (override by exporting before running, e.g. APP_DIR=/srv/kpi ./deploy.sh)
# ---------------------------------------------------------------------------
APP_DIR="${APP_DIR:-/opt/kpi-web}"
GIT_BRANCH="${GIT_BRANCH:-main}"
APP_USER="${APP_USER:-www-data}"

log()  { printf "\n\033[1;32m==>\033[0m %s\n" "$*"; }
warn() { printf "\n\033[1;33m[!]\033[0m %s\n" "$*"; }
die()  { printf "\n\033[1;31m[x]\033[0m %s\n" "$*" >&2; exit 1; }

# ---------------------------------------------------------------------------
# 0. Sanity checks
# ---------------------------------------------------------------------------
if [ ! -f "app.py" ] || [ ! -f "docker-compose.yml" ]; then
    die "Run this from the app folder (where app.py and docker-compose.yml live)."
fi

if [ "$(id -u)" -ne 0 ]; then
    die "Please run with sudo:   sudo ./deploy.sh"
fi

command -v git >/dev/null    || die "git is not installed. Install it first: apt-get install -y git"
command -v docker >/dev/null || die "Docker is not installed. Install it: curl -fsSL https://get.docker.com | sh"

# docker compose (v2 plugin) or docker-compose (v1)
if docker compose version >/dev/null 2>&1; then
    DC="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
    DC="docker-compose"
else
    die "Docker Compose is not installed. Install the compose plugin."
fi

command -v python3 >/dev/null || die "python3 is not installed."

# ---------------------------------------------------------------------------
# 1. Pull latest code
# ---------------------------------------------------------------------------
log "Pulling latest code (branch: $GIT_BRANCH)"
git fetch origin "$GIT_BRANCH"
git checkout "$GIT_BRANCH"
git pull origin "$GIT_BRANCH"

# ---------------------------------------------------------------------------
# 2. Ensure .env exists and has all required keys
# ---------------------------------------------------------------------------
_ensure_env() {
    local key="$1" default="$2" generate="${3:-0}"
    local val
    if grep -q "^${key}=" .env 2>/dev/null; then
        val="$(grep "^${key}=" .env | head -1 | cut -d= -f2-)"
    else
        val=""
    fi
    # Treat empty or placeholder values as missing.
    case "$val" in
        ""|change-this*|change-me)
            if [ "$generate" = "1" ]; then
                case "$key" in
                    SECRET_KEY)     val="$(openssl rand -hex 32)" ;;
                    KPI_ADMIN_PASS) val="$(openssl rand -hex 8)" ;;
                    *)              val="$(openssl rand -hex 24)" ;;
                esac
            else
                val="$default"
            fi
            if grep -q "^${key}=" .env 2>/dev/null; then
                sed -i "s|^${key}=.*|${key}=${val}|" .env
            else
                echo "${key}=${val}" >> .env
            fi
            warn "Set missing ${key} in .env"
            ;;
    esac
}

if [ ! -f ".env" ]; then
    log "First run: creating .env with strong random secrets"
    cp .env.example .env
    DB_PASSWORD="$(openssl rand -hex 24)"
    SECRET_KEY="$(openssl rand -hex 32)"
    KPI_ADMIN_PASS="$(openssl rand -hex 8)"
    sed -i "s|^DB_PASSWORD=.*|DB_PASSWORD=${DB_PASSWORD}|"       .env
    sed -i "s|^SECRET_KEY=.*|SECRET_KEY=${SECRET_KEY}|"          .env
    sed -i "s|^KPI_ADMIN_PASS=.*|KPI_ADMIN_PASS=${KPI_ADMIN_PASS}|" .env
    warn "A new admin password was generated. SAVE IT NOW:"
    printf "\n    Admin user:     admin\n    Admin password: %s\n\n" "$KPI_ADMIN_PASS"
else
    log ".env already exists — checking for missing database settings"
    _ensure_env DB_NAME kpi 0
    _ensure_env DB_USER kpi 0
    _ensure_env DB_HOST 127.0.0.1 0
    _ensure_env DB_PORT 5432 0
    _ensure_env PG_CONTAINER kpi-postgres 0
    _ensure_env DB_PASSWORD "" 1
    _ensure_env SECRET_KEY "" 1
    _ensure_env KPI_ADMIN_PASS "" 1
    _ensure_env BACKUP_INTERVAL_HOURS 24 0
    _ensure_env BACKUP_RETENTION_DAYS 30 0
    _ensure_env ENABLE_INAPP_BACKUP 0 0
fi

# Lock down .env so only root and the app user can read it
chown "root:${APP_USER}" .env 2>/dev/null || chown root:root .env
chmod 640 .env

# ---------------------------------------------------------------------------
# 3. Start PostgreSQL (Docker)
# ---------------------------------------------------------------------------
log "Starting PostgreSQL container"
$DC --env-file .env up -d

log "Waiting for PostgreSQL to become healthy..."
for i in $(seq 1 30); do
    if $DC ps 2>/dev/null | grep -q "healthy"; then
        echo "   PostgreSQL is healthy."
        break
    fi
    sleep 2
    [ "$i" -eq 30 ] && warn "PostgreSQL not reporting healthy yet; continuing anyway."
done

# ---------------------------------------------------------------------------
# 4. Python virtualenv + dependencies
# ---------------------------------------------------------------------------
if [ ! -d "venv" ]; then
    log "Creating Python virtualenv"
    python3 -m venv venv
fi
log "Installing/updating Python dependencies"
./venv/bin/pip install --upgrade pip >/dev/null
./venv/bin/pip install -r requirements-web.txt

# ---------------------------------------------------------------------------
# 5. Install/update systemd units
# ---------------------------------------------------------------------------
log "Installing systemd services"
cp kpi-web.service kpi-backup.service kpi-backup.timer /etc/systemd/system/
systemctl daemon-reload

# ---------------------------------------------------------------------------
# 6. Restart app + enable 24h backups
# ---------------------------------------------------------------------------
log "Restarting web app (creates DB table on first start)"
systemctl enable kpi-web.service >/dev/null 2>&1 || true
systemctl restart kpi-web.service

log "Enabling 24-hour backup timer"
systemctl enable --now kpi-backup.timer

# ---------------------------------------------------------------------------
# 7. Run one backup now + show status
# ---------------------------------------------------------------------------
log "Running one backup now to verify it works"
if systemctl start kpi-backup.service; then
    echo "   Backup service ran. Latest files:"
    # shellcheck disable=SC2012
    ls -lht backups/ 2>/dev/null | head -5 || true
else
    warn "Backup run failed — check: journalctl -u kpi-backup.service -n 30"
fi

echo
log "Deploy complete."
echo "   Web app status:  systemctl status kpi-web.service"
echo "   Next backup:     $(systemctl list-timers 2>/dev/null | grep kpi-backup || echo 'run: systemctl list-timers | grep kpi-backup')"
echo "   App should be reachable on port 20000."
