# rubigram membership worker

Owns Rubika account sessions and runs join / leave / view orders for the
management panel. It is the Rubika twin of balegram's `membership_worker`:
same signed API, same callbacks, same Celery task names, so the existing panel
drives it with `MEMBERSHIP_WORKER_PROVIDER=rubigram-worker` and no other change.

Signed internal endpoints (HMAC headers, nonce replay protection):

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/internal/health/` | provider name, rubigram version, available accounts |
| `POST` | `/internal/orders/` | create a join / leave / view job |
| `GET` | `/internal/orders/<id>/` | job status and counters |
| `POST` | `/internal/accounts/start-login/` | `sendCode` for a phone number |
| `POST` | `/internal/accounts/verify-code/` | `signIn`; stores the session |
| `POST` | `/internal/accounts/signup/` | `signUp` for a phone without an account |
| `POST` | `/internal/accounts/cancel-login/` | drop a pending login |
| `GET` | `/internal/accounts/available/` | number of active accounts |

Full description: [docs/membership-worker.md](../docs/membership-worker.md).

## Run locally

```bash
pip install -e .[worker]                      # from the repository root
cp membership_worker/.env.example membership_worker/.env   # set WORKER_SHARED_SECRET
python membership_worker/manage.py migrate
python membership_worker/manage.py runserver 127.0.0.1:9000
```

```bash
celery -A membership_worker.project.celery worker -l info -Q membership,callbacks,default
celery -A membership_worker.project.celery beat -l info
```

On Windows add `--pool=solo` to the worker command. Redis (or another Celery
broker) must be reachable at `CELERY_BROKER_URL`.

## Production

Dokploy (recommended): [`deploy/dokploy/README.md`](../deploy/dokploy/README.md)
with `docker/server2/dokploy-compose.yml`. Plain Docker Compose:
[`docker/server2/`](../docker/server2). systemd: [`deploy/server2/`](../deploy/server2). Keep the service on a private network or behind an IP
allow-list; every request is also HMAC-signed.
