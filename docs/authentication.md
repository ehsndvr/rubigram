# Authentication and sessions

## Phone-number sessions

```python
from rubigram import Client

async def ask_code(sent):
    return input(f"code ({sent.code_digits_count} digits): ")

app = Client("my_account", phone_number="98912…", code_callback=ask_code)

async with app:            # start(): getDCs → login if needed → registerDevice → socket
    me = await app.get_me()
```

The flow (`login()`):

1. `sendCode` with a fresh random `tmp_session`; the envelope is encrypted with
   it instead of an `auth`.
2. If the account has two-step verification the server answers
   `SendPassKey`; pass `password=` to `login()` (or answer the prompt).
3. `signIn` with the code and the client's RSA public key. The server returns
   the session `auth` encrypted with that key; rubigram unwraps it, stores it,
   and from now on every envelope carries `auth` (caesar-encoded) and an RSA
   signature of `data_enc`.
4. `registerDevice` with the web-client payload (`token_type "Web"`,
   `app_version "WB_4.4.34"`, a `device_hash` derived from the user agent).
5. In `Transport.WS` mode the socket is opened and `handShake` is sent.

Codes: `code=` for a one-shot script, `code_callback=` (sync or async, receives
the `SentCode`) for interactive apps, or the console prompt when neither is
given and stdin is a terminal. Wrong codes raise `CodeIsInvalid`; `login()`
retries up to `max_attempts` times. New accounts continue with `sign_up()`
(`first_name=`), which is kept from rubigram 0.1 and is unverified against the
current server.

Nothing prompts when `interactive=False`; a missing session then raises
`LoginRequired` instead.

## Where the session lives

| Storage | Constructor | Notes |
|---|---|---|
| `SqliteStorage` (default) | `Client("name", workdir=".")` | `name.session`, schema migrates automatically |
| `MemoryStorage` | `Client("name", in_memory=True)` | nothing on disk |
| session string | `Client.from_session_string("name", "rbg2.…")` | in-memory, see below |
| custom | `Client("name", storage=MyStorage("name"))` | subclass `rubigram.storage.Storage` |

The session holds the `auth`, the login key pair, the user guid, the device
hash and registration state, the DC configuration, update states and, for bots,
the token and the last update offset.

## Session strings

```python
string = await app.export_session_string()      # "rbg2." + CRC32 + zlib + base64url
other = Client.from_session_string("copy", string)
```

A session string is equivalent to the password of the account: whoever has it
can act as the user until the session is terminated. rubigram never logs it.
Strings from rubigram 0.1 (plain base64url JSON) are still accepted.

## Devices and logout

```python
sessions = await app.get_my_sessions()
await app.terminate_session(sessions.sessions[1].key)
await app.terminate_other_sessions()
await app.logout()                                # clears the stored auth
```

`get_unconfirmed_sessions()`, `confirm_session()` and `reject_session()`
handle logins started on another device. When the server answers
`ERROR_ACTION` / `INVALID_AUTH` the raised `InvalidAuth` has
`is_session_dead == True`; delete the session file and log in again.

## Bots

```python
bot = Client("my_bot", token="123456:abc…")
```

The token is stored in the session (and in the session string). Bot sessions
never use the phone flow; see [bot-api.md](bot-api.md).

## Security notes

- Never commit `*.session` files or session strings; `.gitignore` excludes
  them.
- `pem_private_key=` lets you supply your own RSA key; otherwise a 1024-bit
  key is generated once per session, like the web client.
- `enable_register_device=False` skips `registerDevice` (some accounts are
  limited in the number of registered devices).
