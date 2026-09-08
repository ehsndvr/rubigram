#!/bin/bash
# First-time deploy of the rubigram membership worker on a fresh Ubuntu server.
#
#   rsync -av --exclude='.git' --exclude='**/__pycache__' --exclude='*.session' ./ root@worker.example.com:/opt/rubigram/
#   ssh root@worker.example.com bash /opt/rubigram/deploy/server2/deploy.sh
set -euo pipefail

DEPLOY_DIR="/opt/rubigram"
VENV="$DEPLOY_DIR/.venv"
WORKER_DIR="$DEPLOY_DIR/membership_worker"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "== rubigram membership worker deploy =="
[ -d "$WORKER_DIR" ] || { echo "ERROR: $WORKER_DIR not found; copy the repository first"; exit 1; }
[ -f "$WORKER_DIR/.env" ] || { echo "ERROR: $WORKER_DIR/.env not found; start from membership_worker/.env.example"; exit 1; }

echo "[1/5] system packages"
apt-get update -q
apt-get install -y --no-install-recommends python3 python3-venv gcc libpq-dev nginx redis-server
id -u rubigram >/dev/null 2>&1 || useradd --system --home "$DEPLOY_DIR" --shell /usr/sbin/nologin rubigram

echo "[2/5] virtualenv and dependencies"
python3 -m venv "$VENV"
"$VENV/bin/pip" install --upgrade pip --quiet
"$VENV/bin/pip" install --quiet -e "$DEPLOY_DIR[worker]"

echo "[3/5] migrations"
cd "$DEPLOY_DIR"
set -a; . "$WORKER_DIR/.env"; set +a
PYTHONPATH="$DEPLOY_DIR" DJANGO_SETTINGS_MODULE=membership_worker.project.settings "$VENV/bin/python" membership_worker/manage.py migrate --noinput
chown -R rubigram:rubigram "$DEPLOY_DIR"

echo "[4/5] systemd units"
for svc in worker-api worker-celery worker-beat; do
    cp "$SCRIPT_DIR/$svc.service" "/etc/systemd/system/rubigram-$svc.service"
done
systemctl daemon-reload
systemctl enable --now rubigram-worker-api rubigram-worker-celery rubigram-worker-beat

echo "[5/5] health check"
sleep 3
code=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8081/internal/health/ || true)
echo "  worker API answered HTTP $code on :8081 (401 = up, signature required)"
cat <<MSG

Next:
  cp $SCRIPT_DIR/nginx.conf /etc/nginx/sites-available/rubigram-worker
  ln -s /etc/nginx/sites-available/rubigram-worker /etc/nginx/sites-enabled/
  nginx -t && systemctl reload nginx && certbot --nginx -d worker.example.com
On the panel: MEMBERSHIP_WORKER_BASE_URL=https://worker.example.com, the same shared secret, MEMBERSHIP_WORKER_PROVIDER=rubigram-worker.
MSG
