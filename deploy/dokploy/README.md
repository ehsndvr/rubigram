# Deploying the worker with Dokploy

The worker runs as one Dokploy **Compose** service (`worker-api`, `worker-celery`,
`worker-beat`) next to a Dokploy-managed **PostgreSQL** and **Redis**. TLS is
handled either by a Dokploy Domain (Traefik) or by the host's nginx in front of a
published port, exactly like the balegram worker.

```
panel ── HTTPS ──▶ Traefik (Dokploy domain)  or  host nginx → :8092
                          │
                   worker-api (Daphne :8001) ──┐
                   worker-celery                ├── dokploy-network ── postgres, redis
                   worker-beat  ───────────────┘
```

Files:

| File | Role |
|---|---|
| `docker/server2/dokploy-compose.yml` | the Compose Path to give Dokploy |
| `docker/worker.Dockerfile` | image (build arg `PIP_INDEX_URL` for a PyPI mirror) |
| `deploy/dokploy/worker.env.example` | environment to paste into Dokploy |
| `deploy/dokploy/nginx-worker.conf` | host nginx site when Traefik is not used |
| `deploy/dokploy/worker-cutover.sh` | fresh wiring or migration from the systemd deploy |
| `deploy/dokploy/worker-call.py` | signed smoke test (`health`, `available`, `order <id>`) |

## 1. Prerequisites

1. Push this repository to a Git host Dokploy can read (GitHub, GitLab, Gitea or
   any SSH remote). Dokploy builds the image from the repository, so a remote is
   required; the repository currently has none.
2. A server with Dokploy installed, or an existing Dokploy adding this box as a
   **remote server** ("Setup Server"). If Docker Hub is slow or blocked from the
   server, put a registry mirror in `/etc/docker/daemon.json` and restart Docker;
   if PyPI is blocked, set `PIP_INDEX_URL` to a mirror in the environment.

## 2. Databases

In the Dokploy project create:

- **PostgreSQL**: database `rubigram_worker`, user `rubigram`, a strong password.
- **Redis**: with a password.

Both must run on the same server as the worker (they are reached over
`dokploy-network`). Copy each database's **Internal Host** from its page; those
go into `DATABASE_HOST` and the Redis URL.

## 3. The Compose service

1. Project → Create Service → **Compose**.
2. Source: your Git provider, branch `main` (or the branch you deploy),
   **Compose Path** `docker/server2/dokploy-compose.yml`.
3. **Environment**: paste `deploy/dokploy/worker.env.example` and fill in
   `SECRET_KEY`, `ALLOWED_HOSTS`, the database and Redis values,
   `WORKER_SHARED_SECRET` (same as the panel) and `WORKER_PORT`.
4. Deploy. The entrypoint runs `migrate` before Daphne starts; wait until the
   service is healthy (the health check probes port 8001 inside the container).

Two ways to expose it:

- **Dokploy Domain (recommended on a fresh server)**: Domains tab → add
  `worker.example.com`, service `worker-api`, container port `8001`, HTTPS with
  Let's Encrypt. Set `SKIP_NGINX=1` if you run the cutover script.
- **Host nginx**: keep `WORKER_PORT` published and install
  `deploy/dokploy/nginx-worker.conf` (the cutover script does it), then
  `certbot --nginx -d worker.example.com`.

## 4. Cutover / wiring

On the server, from a checkout of the repository:

```bash
nohup bash deploy/dokploy/worker-cutover.sh &> /root/worker-cutover.log & tail -f /root/worker-cutover.log
```

The script refuses to touch anything until the new stack answers on
`WORKER_PORT`, stops the systemd units if they exist, optionally moves the old
PostgreSQL database into the managed one (`MIGRATE_DB=1`), and repoints nginx.
Rollback instructions are in its header.

## 5. Verify and connect the panel

```bash
export WORKER_SHARED_SECRET=...
python deploy/dokploy/worker-call.py https://worker.example.com health       # provider, rubigram version, accounts
python deploy/dokploy/worker-call.py https://worker.example.com available
```

On the panel set `MEMBERSHIP_WORKER_BASE_URL=https://worker.example.com`,
`MEMBERSHIP_WORKER_SHARED_SECRET` to the same secret and
`MEMBERSHIP_WORKER_PROVIDER=rubigram-worker`. The panel's own health page then
shows the worker as `ok`.

## 6. A test stack on the same server

Deploy a second Compose service from another branch with `WORKER_PORT=8093`,
its own databases and its own secret; the host nginx site (or a second Dokploy
domain) points at the second port. Nothing else is shared.

## Operations

| Task | How |
|---|---|
| logs | Dokploy → service → Logs, or `docker logs -f <project>-worker-celery-1` |
| Django shell | `docker exec -it <project>-worker-api-1 python membership_worker/manage.py shell` |
| migrations | run automatically on every deploy of `worker-api` |
| scale actions | `CELERY_WORKER_CONCURRENCY` in the environment, then redeploy |
| backups | Dokploy's database backup feature on the PostgreSQL service (the accounts' session strings live there) |

---

## خلاصهٔ فارسی

1. مخزن را روی GitHub/GitLab/Gitea (یا هر ریموت SSH) بگذارید؛ Dokploy از روی مخزن ایمیج را می‌سازد.
2. در پروژهٔ Dokploy یک PostgreSQL و یک Redis مدیریت‌شده بسازید و «Internal Host» آن‌ها را بردارید.
3. یک سرویس Compose بسازید با مسیر `docker/server2/dokploy-compose.yml`؛ متغیرهای `deploy/dokploy/worker.env.example` را در تب Environment پر کنید (`WORKER_SHARED_SECRET` باید با پنل یکی باشد).
4. برای دامنه یا از تب Domains (سرویس `worker-api`، پورت `8001`) استفاده کنید یا nginx میزبان را با `deploy/dokploy/nginx-worker.conf` به پورت `WORKER_PORT` وصل کنید (اسکریپت `worker-cutover.sh` این کار را انجام می‌دهد).
5. با `deploy/dokploy/worker-call.py health` سلامت را بررسی کنید و در پنل `MEMBERSHIP_WORKER_PROVIDER=rubigram-worker` را تنظیم کنید.
