# Final report — rubigram 0.2 redesign

Date: 2026-09-07. Branch: `claude/rubigram-balegram-redesign-80eb77` (13 commits on
top of `master` at `ed9f5bb`; `master` untouched; no remote exists, nothing was
pushed). Everything below was produced and verified inside the worktree
`C:\Codes\rubigram\.claude\worktrees\rubigram-balegram-redesign-80eb77`.

## 1. Outcome

| Gate | Result |
|---|---|
| `python -m pytest -q` | 111 passed, 2 skipped (live tests), 1.5 s, no network |
| `ruff check .` | All checks passed (E, W, F, I, UP, B, C4, SIM, RUF, ASYNC; line length 140) |
| `ruff format --check .` | 136 files already formatted |
| `pyright` (basic) | 0 errors, 0 warnings |
| `python -m build` | `rubigram-0.2.0-py3-none-any.whl` (172 KB, 119 files, only `rubigram/`, ships `py.typed`) and the sdist (156 KB) |
| Library size | 113 modules, 15,820 lines; largest module 437 lines (`client/methods/messages.py`) |
| Branch diff vs `master` | 239 files changed, +27,319 / −19,427 |

The library now has the balegram shape: a thin `Client` composed of domain
mixins on a typed `BaseClient`, a dispatcher with handler groups and
propagation control, composable sync/async filters, one `errors` package with
exact `status_det` classes, a generic `RawMethod` layer with every web-client
RPC, a generic dataclass `Object` parser for typed results, a network layer that
mirrors the web client (retry ladder, DC rotation, socket keep-alive and
reconnect, chunked uploads, ranged downloads, proxy and user agent everywhere),
storage with automatic migration and a portable session string, and the Bot API
merged into `Client(token=...)`.

## 2. Rescued work (Phase 0)

The main checkout had 14 modified files that were never committed. They were
committed first as `7df5a62` (17 files, +1,805 / −339): Rubino post support
(`get_rubino_post`, `RubinoPost`/`UrlFile` types with download), the `DcType`
enum, `JsonTransport`, `download_url`, storage tweaks, docs and tests. The main
checkout still shows those edits as modified files; they are identical to what
`7df5a62` contains and can be discarded there after the branch is merged (that
is the owner's call; nothing was reset).

## 3. Protocol discovery (Phase 1)

Source: the public web client bundle 4.4.34 at `web.rubika.ir` and the public
`getDCs` endpoint, read without logging in. Recorded facts (all in
`docs/redesign/01-coverage-matrix.md` and `01-samples.md`): the encrypted
envelope `{api_version: "6", auth: caesar(auth), data_enc, sign}` (AES-256-CBC,
zero IV, key derived from the auth; RSA PKCS#1 v1.5 / SHA-256 signature), the
`tmp_session` login envelope, plain-JSON service calls with the PWA client
block, `getDCs` (api_version 4) and `getBaseInfo` (api_version 0), the socket
handshake (api_version 5) with a `{}` ping 30 s after the last frame and a
reconnect after 20 s of silence, the 0/2/3/5/10 s retry ladder with DC rotation
and a 20 s request timeout, 131072-byte upload parts with their headers,
downloads posted to `storages[dc_id]` with `start-index`/`last-index`, the
`registerDevice` payload (`token_type "Web"`, `app_version "WB_4.4.34"`,
`device_hash`), the error enums and the five update kinds. 204 methods were
listed; 41 sanitized request/response pairs were mined from the owner's
recordings into `tests/fixtures/rubika/`.

**Not done:** observing traffic of a logged-in account. The owner was not
available to log in and the instruction was to continue without asking, so no
credential was ever typed and nothing was sent to the servers. Consequences are
listed in section 8.

## 4. New tree

```
rubigram/
├── __init__.py, version.py (0.2.0), peer.py, py.typed
├── client/            client.py (Client), base.py (BaseClient), methods/{advanced, auth, sessions, users,
│                      chats, messages, media, groups, channels, join_links, stickers, settings,
│                      services, rubino, bot_api, updates}.py
├── handlers/          handler.py, kinds.py, dispatcher.py
├── filters/           filters.py
├── types/             object.py, raw_object.py, files, user, message, chat, group, channel, update,
│                      settings, stickers, rubino, formatting; bot/{keypad, message}.py
├── raw/               base.py; methods/{auth, users, chats, messages, groups, channels, files,
│                      stickers, settings, services}.py (203 classes); functions/{envelope, messages,
│                      files, settings}.py
├── network/           transport_mode, retry, pool, headers, discovery, http, ws, upload, download, bot_api
├── storage/           base (Storage + FIELDS), sqlite, memory, session_codec
├── crypto/            cipher, auth, codec
├── errors/            exceptions, mapping
├── enums/, utils/
└── shims: bot/{enums,types,transport}, exceptions/, types/results.py, network/{transport,socket}.py,
          raw/methods/updates.py, storage/{file_storage,sqlite_storage}.py
tests/                 fake_rubika.py (in-process Rubika), test_{client,dispatcher,bot_api,types,raw,
                       network,storage,errors,crypto}.py, fixtures/rubika/ (41 + socket frame),
                       integration/ (opt-in live checks)
examples/              user_session, echo_bot, get_rubino_post, rubino_downloader_bot, ai_assistant
tools/                 gen_method_reference.py, payload-decoder/ (offline traffic decoder page)
docs/                  overview, architecture, authentication, transports, updates-and-handlers,
                       method-reference (generated, 318 methods), bot-api, rubino, examples, migration,
                       redesign/00–03
CLAUDE.md, README.md, LICENSE (LGPL-2.1-or-later), pyproject.toml, pyrightconfig.json, .gitignore
```

## 5. Methods

Coverage of the 204 web-client methods:

| | Phase 1 (0.1) | Now (0.2) |
|---|---|---|
| typed wrapper (typed result model) | 31 | 137 |
| wrapper returning `RawObject` (shape not observed) | 5 + 8 partial | 63 |
| raw class only | – | 2 (`loginTwoStepForgetPassword`, `loginDisableTwoStep`) |
| wrong server name | 6 | 0 |
| missing entirely | 154 | 0 |
| transport level (`handShake`, `getDCs`) | 2 | 2 |

`rubigram.raw.methods` has 203 classes (every RPC in the bundle plus `signUp`),
`Client` exposes 318 public methods (docs/method-reference.md, each tagged
`[HTTP]`, `[WS]`, `[both]` or `[bot]`), and `invoke_raw()` calls anything by
name.

Corrected behaviour:

| 0.1 | Problem | 0.2 |
|---|---|---|
| `getChat`, `getHistory`, `deleteMessage`, `blockUser`, `unblockUser`, `uploadNewGroupAvatar` | not server methods | `getChatsByID`, `getMessages`, `deleteMessages`, `setBlockUser(action)`, `uploadAvatar`; old Python names kept as aliases |
| `getMessages(offset, limit)`, `getContacts(offset, limit)` | wrong inputs | `max_id/min_id/sort/limit/filter_type`, `start_id` |
| download host `messenger{dc}.iranlms.ir` | wrong host pattern | `storages[dc_id]` from `getDCs` (`messanger…/GetFile.ashx`) with ranges and `total_length` |
| `app_version 4.4.27` | outdated | `4.4.34`; `WB_` prefix in `registerDevice` |
| single attempt, no DC rotation | | `RetryPolicy(0, 2, 3, 5, 10)` with rotation, `getDCs` refresh, `retries=0` for fire-and-forget |
| socket without keep-alive | | `{}` ping 30 s after the last frame, reconnect after 20 s silence / close, URL rotation, re-handshake |
| `OldState` answers moved the state | | state never moves backwards; per-chat states for `getMessagesUpdates` |
| `NOT_REGISTERED` surfaced as an error | | `registerDevice` once, then retry |
| errors matched by substrings | | one class per `status_det`, `client_show_message` kept, `TooRequests.retry_after` (Persian/English) |
| `MemoryStorage.open()` lost state, `Avatar.download` misplaced, `Sticker._parse` parsed twice, `RpcError.raw` was the outer envelope | bugs | fixed by construction (tests cover each) |
| two clients (`Client`, `BotClient`) with drifting polling/dispatch | | one `Client`; shared methods switch on `is_bot` |

Added (typed wrappers, all offline-tested): users and contacts (block, contacts
updates with stored state, last online, profile, username, report, spam),
chats (dialog pages and `iter_chats`, seen, mute/pin/archive, delete variants,
share URLs, link resolution), messages (edit/delete/forward, history pages and
`iter_messages`, by-id, interval, search, pin, activities, read participants,
transcription, reactions, polls, drafts), media (`send_photo/video/voice/music/gif/document`,
progress callbacks, in-memory downloads, avatars, wallpapers), groups (info,
members pages, bans, admins with access lists, default access, links, online
count, mentions, ownership transfer, settings incl. reactions and slow mode),
channels (same plus username), join links and join requests, stickers, GIF set
and folders (with stored state), settings, privacy, two-step verification,
phone change, sessions and unconfirmed sessions, services, web apps, wallet,
live streams, group voice chats, Rubino (posts, stories, share), Bot API
(keypads, files, polls, locations, contacts, commands, endpoints, bans,
webhooks), updates (`receive_update`, `get_updates` in both modes, per-chat
updates, `idle`, HTTP polling fallback).

## 6. Deleted files

Every deletion was checked for references first (grep across the tree, the old
test suite and the examples); replacements are named.

| File | Size | Reason |
|---|---|---|
| `.DS_Store` (tracked) | 6,148 B | macOS Finder metadata committed by mistake |
| `examples.json` | 79,404 B | raw traffic dump with real guids; the sanitized pairs now live in `tests/fixtures/rubika/` |
| `TODO` | 356 B | both items were done (`getDCs` discovery, login `Client`); the AI-assistant idea became `examples/ai_assistant.py` |
| `TODO.md` | 0 B | empty |
| `tests/local_bot_test.py` | 734 B | real-account script with a hard-coded bot token; replaced by `examples/echo_bot.py` and `tests/integration/test_live_bot.py` |
| `tests/local_client_test.py` | 9,273 B | real-account experiments with real guids; replaced by `examples/user_session.py` and `tests/integration/test_live_user.py` |
| `tests/local_test.py` | 8,087 B | AI assistant on a real account; ported to `examples/ai_assistant.py` (env-based configuration) |
| `tests/rubino_downloader_bot.py` | 2,801 B | real-account script; ported to `examples/rubino_downloader_bot.py` |
| `tests/test_client.py` (0.1) | 5,159 lines, 214,963 B | monolith bound to the old god class; replaced by per-domain suites (`test_client`, `test_dispatcher`, `test_bot_api`) on the fake server |
| `tests/test_bot_api.py` (0.1) | 286 lines, 9,487 B | rewritten for `Client(token=...)` |
| `tests/test_transport.py` (0.1) | 326 lines, 10,598 B | replaced by `tests/test_network.py` |
| `rubigram/client.py` (0.1 module) | 1,509 lines, 58,846 B | god class; replaced by the `rubigram/client/` package |
| `rubigram/methods/` (0.1 package, 26 files) | 1,645 lines | old mixins; replaced by `rubigram/client/methods/` |
| `rubigram/types/results.py` (0.1 content) | 2,322 lines | split into domain modules; the path stays as an import shim |
| `rubigram/types/user_and_chats/` | 181 lines | merged into `types/user.py` and `types/chat.py` |
| `rubigram/filters.py` | 140 lines, 6,794 B | became the `rubigram/filters/` package (same names, async-capable) |
| `rubigram/bot/client.py` | 429 lines, 16,625 B | `BotClient` merged into `Client(token=...)` |
| `rubigram/crypto/encryption.py` | 41 lines, 800 B | duplicate of `crypto/cipher.py` |
| `rubigram/session/__init__.py` | 10 lines, 291 B | unused re-export |
| `docs/client-methods.md` | 41,757 B | hand-written 0.1 reference with wrong signatures; replaced by the generated `docs/method-reference.md` |
| `docs/update-message-types.md` | 7,503 B | 0.1 samples; superseded by `docs/updates-and-handlers.md` and the socket fixture |

Removed from the **main checkout** (untracked junk; sizes measured before deletion):

| Path | Count / size | Reason |
|---|---|---|
| `._*` AppleDouble files | 272 files, 1,114,112 B | macOS resource forks copied from a Mac |
| `.DS_Store` files | 2 files, 12,296 B | Finder metadata |
| `rubigram.egg-info/` | 24,828 B | build artefact of `pip install -e` |
| `.pytest_tmp/`, `rubigram/api/`, `rubigram/models/` | empty | empty directories |
| `rubigram-ui/` | 27,453 B (3 real files) | moved to `tools/payload-decoder/` (verified byte-identical, now tracked) |
| `*.session` (6 files) | 483 KB | deleted at the very end as instructed; contents never read, printed or copied; never in git history (checked with `git log --all -- '*.session'`) |

`.vscode/` (150 B, owner's editor settings, ignored by git) was left alone.

## 7. Commits

| Hash | Message |
|---|---|
| `7df5a62` | نجات کار ذخیره‌نشدهٔ مالک — Rescue owner's uncommitted work |
| `7214085` | ممیزی فاز صفر — Phase 0 audit |
| `5a277e6` | فاز یک: کشف پروتکل — Phase 1: protocol discovery, coverage matrix, samples |
| `af62d19` | فاز دو: طرح معماری — Phase 2: architecture plan |
| `435a8b4` | پکیج خطاهای یکپارچه — Unified errors package |
| `ea166db` | لایهٔ شبکه — Network layer |
| `bd78c7b` | ذخیره‌سازی — Storage and session string |
| `354555e` | لایهٔ انواع — Types layer |
| `a32bc0d` | لایهٔ raw — Raw layer |
| `327173d` | کلاینت نازک با mixinها — Thin Client, dispatcher, filters, Bot API merge |
| `81bbe12` | پاک‌سازی — Cleanup, examples, integration tests, license |
| `44b50a8` | دروازهٔ کیفیت — Quality gate and 0.2.0 packaging |
| `fdbe49c` | مستندات ۰.۲ — 0.2 documentation and CLAUDE.md |

> History note (2026-09-08): before the first push to GitHub the four files that carried secrets or real identifiers (`ai.md`, `examples.json`, `tests/local_bot_test.py`, `tests/local_client_test.py`) were removed from every commit, so the hashes above are the rewritten ones. The old local `master` in the main checkout still has the original history and must be replaced by `origin/main`.

## 8. What could not be verified

1. **Live server behaviour.** No logged-in traffic was observed. Envelope
   format, DC discovery, retry ladder, socket rules and upload/download formats
   come from the bundle; 41 request/response pairs come from the owner's earlier
   recordings. The 63 wrappers that return `RawObject` and the field lists of
   several typed models were derived from how the web client reads them, not
   from observed answers.
2. **`signUp`** (kept from 0.1), **`loginTwoStepForgetPassword`** and
   **`loginDisableTwoStep`** (raw classes only) were never exercised.
3. **Socket keep-alive and reconnect** are implemented exactly as the bundle
   describes and tested with a stub websockets module, not against the server.
4. **Bot API** shapes follow the 0.1 implementation and the public Bot API
   documentation; they were tested offline only.
5. **Rubino** `getProfilePosts` input comes from the owner's rescued code, which
   worked for them; it was not re-verified.
6. **`graphify`** is not installed, so no dependency graph was produced; the
   audit's dependency map was made by hand.

`tests/integration/` (skipped by default) runs read-only checks against the
real servers once a session exists: `RUBIGRAM_INTEGRATION=1 python -m pytest tests/integration -q`.

## 9. Security notes for the owner

- The bot token that was hard-coded in `tests/local_bot_test.py` is gone from
  the tree but is still readable in git history (3 commits touch that file,
  including `master`). **Revoke that token** in the bot panel.
- The six `.session` files at the repo root contained unencrypted session
  keys; they are deleted and `.gitignore` excludes `*.session`, `._*` and
  `.DS_Store` from now on.
- Fixtures contain only `u0EXAMPLE…` guids, a synthetic phone number and no
  access hashes; tests use `"a" * 32`-style fake auth keys.

## 10. Remaining work

1. Merge the branch (`git merge --no-ff claude/rubigram-balegram-redesign-80eb77`
   on `master`), then discard the duplicate working-tree edits in the main
   checkout.
2. Point the editable install at this repo (`pip install -e C:\Codes\rubigram`);
   today `pip` still points at `E:\Codes\rubigram`.
3. Log in once with `examples/user_session.py` and run the live tests; promote
   `RawObject` results to typed models as real answers are recorded (drop the
   sanitized pair into `tests/fixtures/rubika/<method>.json`).
4. Decide on socket RPC sending (not implemented; the web client does not use
   it) and on typed wrappers for voice/video call signalling.
5. Add a `CHANGELOG.md` and publish 0.2.0 when the live checks pass.
