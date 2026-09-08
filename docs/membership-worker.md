# Membership worker

`membership_worker/` is a service that owns a pool of Rubika accounts and
executes *orders* from a management panel: make N accounts join a channel or
group, leave it again, or view its latest posts. It is the Rubika twin of the
worker in the author's balegram project and speaks the same protocol, so the
existing panel can drive both: point `MEMBERSHIP_WORKER_BASE_URL` at this
service, share the secret, and set `MEMBERSHIP_WORKER_PROVIDER=rubigram-worker`.

```
panel ──signed HTTPS──▶ worker API (Daphne)          orders, login flow, health
                        │
                        ├── PostgreSQL / SQLite      accounts (session strings), jobs, items, memberships
                        ├── Redis ──▶ Celery worker  one item = one Rubika action with one account
                        └── Celery beat              auto-leave, lost-task recovery
worker ──signed HTTPS──▶ panel callback              order_accepted / completed / partial / failed / active
```

## What one order becomes

1. `POST /internal/orders/` with `action`, `target`, `count`, `service_id`,
   `retention_days`, `callback_url`, `idempotency_key`, `external_order_id`.
2. The worker parses the target (`joinc`/`joing` invite links, `@username`,
   `rubika.ir/name`, `c0…`/`g0…` guids, or `rubika.ir/name/<post id>` for a
   single post) and reserves accounts:
   - **join**: active, not throttled, not already a member of that target, not
     reserved by another running join for it; the count is inflated by
     `WORKER_BONUS_PERCENTAGE`. No free account → `422 insufficient_capacity`.
   - **leave**: accounts recorded as members of the target.
   - **view**: any active accounts, cycled to reach the count.
3. One `MembershipJobItem` per account is queued on Celery. Each item opens a
   short-lived rubigram client from the stored session string (HTTP only,
   no socket, DC list taken from the session), performs the action, and
   closes. Accounts are paced by `WORKER_ACTION_DELAY_SECONDS`.
4. Results update the counters; when no item is pending the job settles
   (`completed`, `partial`, `fail`, or `active` while a retention period runs)
   and a signed callback goes to the panel. Missing join slots are refilled
   with other accounts while some remain eligible.
5. With `retention_days`, an auto-leave is scheduled per joined account; beat
   runs them and the job moves from `active` to `completed`.

## Rubika specifics

| Order | rubigram calls |
|---|---|
| join `joinc` link | `get_channel_preview` (member count, `is_member`) → `join_channel_by_link` |
| join `joing` link | `get_group_preview` → `join_group` |
| join `@username` / `c0…` | `get_object_by_username` / `get_channel_info` → `join_channel` |
| leave | resolve as above → `leave_channel` / `leave_group` |
| view N posts | resolve → `get_messages(limit=N)` → `seen_chats` |
| view one post | `get_object_by_username` → `get_message` → `seen_chats` |

Member counts come from `count_members` of the preview/info before the first
join and from the join result (or a second info call) afterwards.

Failures are classified (`worker/rubika.py`):

| Kind | Cause | Effect |
|---|---|---|
| `invalid_target` | invalid/expired link, unknown username, a user or bot | first failure cancels the job (`fail`; `partial` if others already joined); later ones skip the item |
| `session_dead` | `INVALID_AUTH`, `NOT_REGISTERED`, missing session | item skipped, account **disabled**, another account takes the slot |
| `throttled` | `TOO_REQUESTS` | item skipped, account paused for the server's `retry_after` (default 1 h), retried later |
| `conn_error` | timeouts, network, undecodable answers | item skipped, account paused 60 s, slot refilled later |
| `already_done` | already a member / not a member | join: counted as success; leave: skipped |
| `failed` | anything else | item failed, message stored on the account |

## Adding accounts

The panel's "add number" flow maps onto Rubika's login:

| Endpoint | Rubika | Notes |
|---|---|---|
| `POST /internal/accounts/start-login/` `{username, phone, proxy?}` | `sendCode` | returns `transaction_hash` (= `phone_code_hash`), `session_name`, `device_hash`, the pending state in `grpc_cookies` / `login_state`, and where the code went (below) |
| `POST /internal/accounts/verify-code/` `{session_name, transaction_hash, code, grpc_cookies, proxy?}` | `signIn` | stores the session string; `requires_signup: true` when the phone has no account |
| `POST /internal/accounts/signup/` `{…, display_name, proxy?}` | `signUp` | unverified against the live server |
| `POST /internal/accounts/cancel-login/` | – | drops the pending login |

The pending state is a rubigram session string *without* `auth` (temporary
session, login key pair, DC list), so any worker process can finish a login
another one started. Accounts with two-step verification are refused with a
Persian message, as the panel has no password step. Responses carry
`auth_id = user guid` and `user_id = null` (Rubika has no numeric ids).

**Where the code goes.** `start-login` answers `sent_code_type` (`SMS` or
`Internal`), `code_digits_count` (five) and `code_via_telegram: false`. The last
one is stated rather than left out, because a missing field reads as *unknown*:
Bale and Soroush hand a foreign number's code to Telegram, which is what lets a
panel register from a `.session` file with nobody typing anything, and Rubika
never does. A caller waiting for a Rubika code in a Telegram chat waits until it
has expired.

**The exit.** `proxy` is the address *this* login leaves from, and it beats
`WORKER_PROXY` for the call. It exists because the panel picks an exit country
per registration and, until the worker read the field, that choice moved only
the panel's own hop — the connection Rubika sees is the one opened here. It is
validated (scheme, host, port) and refused with **422** when malformed, rather
than failing several layers down as a connection error that blames Rubika. It is
also returned inside `login_state`, so a verify finished by a *different* worker
process still answers from the address the code went out on. `egress_ip` on the
answer is what an echo service actually saw through it — evidence, not a
promise, and never a reason for a login to fail.

## Account status, health and removal

Four endpoints the panel uses once a number is registered. None of them is
required to register one; all four answer for accounts this worker owns.

| Endpoint | Reads | Notes |
|---|---|---|
| `POST /internal/accounts/stats/` `{session_names[], account_ids[], include_aggregate}` | the database | `per_account[<session>]` → `worker_status`, `last_error`, `joined`, … plus the worker-wide rollup when asked. Two queries whatever the batch; capped at 500 |
| `POST /internal/accounts/health/` `{session_names[]}` | the last probe | the `{total, available, at_capacity, dead, unknown, last_scan_at}` rollup always, `per_account` when names are given. Never connects to Rubika |
| `POST /internal/accounts/probe/` `{session_names[], timeout?}` | Rubika, now | connects as each session and answers `{alive, outcome, availability, detail}`; `missing` names the sessions this worker does not have. Read-only, capped at 50 |
| `POST /internal/accounts/delete/` `{account_id \| session_name \| phone}` | – | removes the account row and its session string. Idempotent: a row already gone is `deleted: 0` and **200**, so a panel retry is safe |

`worker_status` and `availability` answer different questions and the panel shows
both. The first is what the *job pipeline* last ran into, and it is noisy — a
dropped connection disables an account that is perfectly healthy. The second is
written only by a probe that connected on purpose:

* `available` — the session authenticated and nothing says it is full;
* `at_capacity` — it has hit Rubika's ceiling on joined channels. Rubika offers
  no read-only way to ask (a full account reads and identifies itself normally;
  only a *join* comes back refused), so this is recognised from the error a join
  already recorded, never from the probe;
* `dead` — refused authentication **twice running**. The hysteresis is the
  point: one refusal is as likely to be the route as the session;
* `unknown` — never probed, or only ever failed transiently. Said out loud,
  because "we have not looked" and "we looked and it is fine" are answers an
  operator must be able to tell apart.

A probe that finds a *disabled* account alive reactivates it, since a session
that authenticates now is one the pipeline was wrong about. The periodic sweep
(`membership_worker.scan_account_health`, every `HEALTH_SCAN_INTERVAL_SECONDS`)
works round the table oldest-verdict-first and uses the same verdict path.

## Configuration

See `membership_worker/.env.example`. Process environment variables override
the file. The important ones:

| Variable | Meaning |
|---|---|
| `WORKER_SHARED_SECRET` | HMAC secret shared with the panel |
| `WORKER_PROVIDER` | name reported to the panel (`rubigram-worker`) |
| `WORKER_SIGNATURE_HEADER_PREFIX` | header names on callbacks (`X-Balegram` for the balegram panel; `X-Rubigram` is accepted on incoming requests as well) |
| `WORKER_ACTION_DELAY_SECONDS`, `WORKER_ACTION_TIMEOUT_SECONDS` | pacing and per-request timeout |
| `WORKER_BONUS_PERCENTAGE`, `WORKER_JOB_MAX_WAIT_HOURS` | join buffer and how long missing slots are refilled |
| `WORKER_USER_AGENT`, `WORKER_DEVICE_HASH`, `WORKER_SYSTEM_VERSION`, `WORKER_DEVICE_MODEL`, `WORKER_PROXY` | the identity and network path of every Rubika client (a per-call `proxy` beats `WORKER_PROXY`) |
| `WORKER_EGRESS_ECHO_URL`, `WORKER_EGRESS_TIMEOUT_SECONDS` | where "which address did Rubika see?" is asked. Empty turns the check off — right for a deployment with no outbound to it |
| `HEALTH_SCAN_INTERVAL_SECONDS`, `HEALTH_SCAN_BATCH` | how often the read-only health sweep runs, and how many accounts each pass probes |
| `DATABASE_*`, `CELERY_BROKER_URL` | storage and broker |

## Running

```bash
pip install -e .[worker]
cp membership_worker/.env.example membership_worker/.env
python membership_worker/manage.py migrate
python membership_worker/manage.py runserver 127.0.0.1:9000
celery -A membership_worker.project.celery worker -l info -Q membership,callbacks,default   # add --pool=solo on Windows
celery -A membership_worker.project.celery beat -l info
```

Production recipes:

- **Dokploy** (recommended): `docker/server2/dokploy-compose.yml` with managed
  PostgreSQL and Redis; guide, environment template, nginx site, cutover script
  and a signed smoke test in [`deploy/dokploy/`](../deploy/dokploy/README.md).
- **Plain Docker Compose**: `docker/server2/docker-compose.yml` (PostgreSQL,
  Redis, API, worker, beat, nginx).
- **systemd**: the units and `deploy.sh` in `deploy/server2/`.

## Tests

`tests/test_membership_worker.py` runs the whole service against a temporary
SQLite database with the Rubika actions and Celery dispatch replaced by
recorders: signing and replay protection, target parsing, the signed API,
capacity reservation, join/leave/view processing, error classification,
recovery, and the login flow including the panel's field mapping. It is skipped
when Django or Celery are not installed (`pip install -e .[dev]` includes them).

## Not verified live

The join/leave/view calls follow rubigram's method reference; the view
mechanism (fetch + `seenChats`) is what the web client does when a channel is
opened and is assumed to count as a view. `signUp` and the reaction of Rubika
to many joins from one IP were not observed. Run a small order against a test
channel before trusting the counters.
