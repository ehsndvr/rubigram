#!/usr/bin/env bash
# Switch the worker box to the Dokploy stack — run ON the worker server as root.
#
# Works for both cases:
#   * fresh server: only wires nginx (or nothing, when a Dokploy Domain is used).
#   * migration from the systemd deploy (deploy/server2): stops the old units,
#     optionally moves the PostgreSQL database into the Dokploy-managed instance
#     and repoints nginx to the published port.
#
# PREREQS (Dokploy UI, no downtime):
#   1. This box is a Dokploy server ("Setup Server" done; docker registry mirror in
#      /etc/docker/daemon.json if pulls from Docker Hub are slow or blocked).
#   2. Managed PostgreSQL + Redis created in the project; their internal hosts and
#      passwords are in the Compose service's Environment (deploy/dokploy/worker.env.example).
#   3. The Compose service (Compose Path docker/server2/dokploy-compose.yml) is
#      deployed and HEALTHY.  worker-api is published on WORKER_PORT (default 8092):
#        curl -sI http://127.0.0.1:8092/internal/health/     # 401 = alive (signature required)
#
# RUN (survives SSH drops):
#   nohup bash deploy/dokploy/worker-cutover.sh &> /root/worker-cutover.log & tail -f /root/worker-cutover.log
#
# Environment knobs:
#   WORKER_PORT=8092          published port of worker-api
#   MIGRATE_DB=1              dump the host PostgreSQL database into the managed one (migration case)
#   OLD_DB=rubigram_worker    host database name;  PG_USER=rubigram  managed superuser
#   SKIP_NGINX=1              do not touch nginx (Dokploy Domain / Traefik handles TLS)
#
# ROLLBACK:
#   cp /root/rubigram-worker.PRECUTOVER.bak /etc/nginx/sites-enabled/rubigram-worker && nginx -t && systemctl reload nginx
#   systemctl enable --now rubigram-worker-api rubigram-worker-celery rubigram-worker-beat
set -uo pipefail

WORKER_PORT="${WORKER_PORT:-8092}"
MIGRATE_DB="${MIGRATE_DB:-0}"
OLD_DB="${OLD_DB:-rubigram_worker}"
PG_USER="${PG_USER:-rubigram}"
SKIP_NGINX="${SKIP_NGINX:-0}"
OLD_SERVICES="rubigram-worker-api rubigram-worker-celery rubigram-worker-beat"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

log() { echo "[$(date +%H:%M:%S)] $*"; }
die() { echo "[ABORT] $*" >&2; exit 1; }

# ---- discover the new containers ----
api=$(docker ps --format '{{.Names}}' | grep -m1 -E -- '-worker-api-1$' || true)
celery=$(docker ps --format '{{.Names}}' | grep -m1 -E -- '-worker-celery-1$' || true)
beat=$(docker ps --format '{{.Names}}' | grep -m1 -E -- '-worker-beat-1$' || true)
log "api=$api celery=$celery beat=$beat"
[ -n "$api" ] && [ -n "$celery" ] && [ -n "$beat" ] || die "Dokploy worker containers not all running — deploy the Compose service first"

# ---- 0) the new stack must answer before anything old is stopped ----
code=$(curl -m5 -so /dev/null -w '%{http_code}' "http://127.0.0.1:${WORKER_PORT}/internal/health/" || true)
[ "$code" != "000" ] || die "worker-api :${WORKER_PORT} not reachable (got $code)"
log "pre-check OK (worker-api answered HTTP $code; 401 is expected without a signature)"

# ---- 1) stop the systemd deploy, if any ----
for svc in $OLD_SERVICES; do
    if systemctl list-unit-files "$svc.service" >/dev/null 2>&1 && systemctl is-enabled "$svc" >/dev/null 2>&1; then
        log "stopping and disabling $svc"
        systemctl stop "$svc" || true
        systemctl disable "$svc" || true
    fi
done

# ---- 2) optional: move the database into the managed PostgreSQL ----
if [ "$MIGRATE_DB" = "1" ]; then
    pg=$(docker ps --format '{{.ID}} {{.Image}}' | awk '/postgres/{print $1; exit}')
    [ -n "$pg" ] || die "no managed postgres container found"
    ts=$(date +%Y%m%d_%H%M%S); mkdir -p /root/db-backups
    log "dumping host database $OLD_DB"
    sudo -u postgres pg_dump -Fc "$OLD_DB" > "/root/db-backups/worker_final_$ts.dump" || die "pg_dump failed"
    docker stop "$api" "$celery" "$beat" >/dev/null
    log "restoring into managed postgres $pg"
    docker exec "$pg" psql -U "$PG_USER" -d postgres -c "DROP DATABASE IF EXISTS $OLD_DB WITH (FORCE)" | tail -1
    docker exec "$pg" psql -U "$PG_USER" -d postgres -c "CREATE DATABASE $OLD_DB OWNER $PG_USER" | tail -1
    docker cp "/root/db-backups/worker_final_$ts.dump" "$pg":/tmp/worker.dump
    docker exec "$pg" pg_restore -U "$PG_USER" --no-owner --no-privileges -d "$OLD_DB" /tmp/worker.dump 2>&1 | tail -3
    rows=$(docker exec "$pg" psql -U "$PG_USER" -d "$OLD_DB" -Atc "select count(*) from worker_workeraccount" 2>&1)
    log "restored — worker_workeraccount rows: $rows"
    docker start "$api" "$celery" "$beat" >/dev/null
    sleep 5
fi

# ---- 3) nginx: point the site at the published port ----
if [ "$SKIP_NGINX" != "1" ]; then
    site=/etc/nginx/sites-enabled/rubigram-worker
    [ -e "$site" ] && cp "$(readlink -f "$site")" /root/rubigram-worker.PRECUTOVER.bak && log "nginx backup: /root/rubigram-worker.PRECUTOVER.bak"
    sed "s/127.0.0.1:8092/127.0.0.1:${WORKER_PORT}/" "$SCRIPT_DIR/nginx-worker.conf" > /etc/nginx/sites-available/rubigram-worker
    ln -sf /etc/nginx/sites-available/rubigram-worker "$site"
    if nginx -t; then
        systemctl reload nginx && log "nginx now proxies to :${WORKER_PORT}"
    else
        die "nginx config test failed — restore /root/rubigram-worker.PRECUTOVER.bak"
    fi
fi

# ---- 4) health ----
code=$(curl -m5 -so /dev/null -w '%{http_code}' "http://127.0.0.1:${WORKER_PORT}/internal/health/" || true)
log "worker-api :${WORKER_PORT} → HTTP $code"
log "done. Verify with: WORKER_SHARED_SECRET=... python deploy/dokploy/worker-call.py https://worker.example.com health"
