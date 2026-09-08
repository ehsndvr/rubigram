# CLAUDE.md

rubigram is an async Python client for Rubika (phone sessions, bots, Rubino).
Read `docs/overview.md` and `docs/architecture.md` first; protocol facts live in
`docs/redesign/` (audit, coverage matrix with the real RPC names, samples).

## Commands

```bash
pip install -e .[dev]
python -m pytest -q                      # offline; tests/fake_rubika.py answers every call
ruff check . && ruff format --check .    # config in pyproject.toml, line length 140
pyright                                  # basic mode; library must be at 0 errors
python -m build                          # wheel must contain only rubigram/
python tools/gen_method_reference.py     # regenerate docs/method-reference.md after docstring changes
RUBIGRAM_INTEGRATION=1 python -m pytest tests/integration -q   # live, read-only, needs a session
python membership_worker/manage.py migrate                     # the worker service (Django + Celery, see docs/membership-worker.md)
```

## Layout

- `rubigram/client/client.py` is thin: construction, lifecycle, transports,
  handler decorators. Every method lives in a mixin under
  `rubigram/client/methods/` (one file per domain, ≤ ~450 lines).
- Mixins derive from `rubigram/client/base.py::BaseClient`, which declares the
  shared attributes and cross-mixin hooks as typed stubs. Add a stub there when
  a mixin needs a method of another mixin.
- `rubigram/raw/methods/` holds one dataclass per RPC (`method_name`, fields,
  `result`, optional `auth_mode` / `dc_type` / `api_version` / `retries`);
  `rubigram/raw/functions/` holds payload builders with logic.
- `rubigram/types/` are `@model` dataclasses parsed generically from type hints;
  unknown keys land in `.extra`. Bot payloads are in `rubigram/types/bot/`.
- `rubigram/network/` transports know nothing about methods; `rubigram/storage/`
  knows nothing about the network.
- `membership_worker/` is a Django + Celery service on top of the library.
  Everything that opens a Rubika connection goes through `worker/rubika.py`'s
  `build_client` — `accounts.py` (the panel-driven login) and `health.py` (the
  read-only account probe) are the only callers; `jobs.py`, `items.py`,
  `recovery.py` are pure bookkeeping; `exit.py` validates the per-call proxy and
  measures what address it comes out on; `views.py` is the signed API.
  `rubigram_internal/signing.py` is the HMAC scheme shared with the panel and
  must stay wire-compatible with balegram's. Its tests live in
  `tests/test_membership_worker.py` and use a temporary SQLite database with
  every Rubika action stubbed.
  The worker is excluded from pyright until `django-stubs` can be installed
  (without it every ORM access is a false positive); ruff still covers it.
- Shims kept for 0.1 imports: `rubigram/bot/*`, `rubigram/exceptions/`,
  `rubigram/types/results.py`, `rubigram/network/transport.py`,
  `rubigram/network/socket.py`, `rubigram/raw/methods/updates.py`.

## Adding a method

1. Check the RPC name and input in `docs/redesign/01-coverage-matrix.md`
   (names not in the web client, such as `getChat` or `getHistory`, do not
   exist server-side).
2. Add or extend the `RawMethod` dataclass in `rubigram/raw/methods/<domain>.py`
   and a result model in `rubigram/types/<domain>.py` (export both).
3. Add the typed wrapper to the matching mixin with a one-line docstring that
   ends in a tag: `[HTTP]`, `[WS]`, `[both]` or `[bot]` (bot-capable shared
   methods carry `[HTTP][bot]`).
4. Add a test in `tests/test_client.py` (or the domain file) using
   `FakeRubika.responses[...]` and, when a sanitized recording exists,
   `tests/fixtures/rubika/<method>.json`.
5. Regenerate the method reference.

## Rules

- Tests never touch the network; `httpx.MockTransport`, the stub websockets
  module and `FakeRubika` are the only servers.
- Never commit `*.session` files, session strings, phone numbers, codes,
  tokens or real guids; fixtures use `u0EXAMPLE…` guids and `FAKE_*`
  constants.
- No `print()` / `input()` in the library except the login prompt behind the
  `interactive` flag; use `logging`.
- Every network behaviour is configurable (`timeout`, `retry_policy`, `proxy`,
  `user_agent`, `socket_urls`); do not hard-code hosts outside
  `rubigram/network/discovery.py`.
- Keep the user API and the Bot API behind the same `Client`; mode is
  `client.is_bot`.
- Commit messages are bilingual: `<Persian summary> — <English summary>`.

## Known gaps

- Sending RPCs over the WebSocket is not implemented (the web client uses it
  for pushes only).
- `signUp` and a few rarely used payload shapes are unverified against the
  live server; they return permissive models (`RawObject` fields).
- Live behaviour was not observed with a logged-in account during the 0.2
  redesign; `tests/integration/` exists to do that when a session is available.
