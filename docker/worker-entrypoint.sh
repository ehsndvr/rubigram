#!/bin/sh
set -e
cd /app

if [ "${1:-}" = "daphne" ]; then
    echo "[entrypoint] applying database migrations"
    python membership_worker/manage.py migrate --noinput
fi

exec "$@"
