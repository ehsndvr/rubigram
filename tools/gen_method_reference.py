"""Generate docs/method-reference.md from the Client mixins (signatures, docstrings, tags)."""

from __future__ import annotations

import inspect
import re
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from rubigram.client.client import Client  # noqa: E402
from rubigram.client.methods import (  # noqa: E402
    Advanced,
    Auth,
    BotApi,
    Channels,
    Chats,
    Groups,
    JoinLinksMixin,
    Media,
    Messages,
    Rubino,
    Services,
    Sessions,
    Settings,
    Stickers,
    UpdatesMixin,
    Users,
)

SECTIONS = [
    ("Lifecycle and handlers", Client, "`Client` itself: construction, start/stop, transport switching and handler registration."),
    ("Authentication", Auth, "Phone login, device registration, logout."),
    ("Sessions", Sessions, "Active devices and the portable session string."),
    ("Users and contacts", Users, ""),
    ("Chats", Chats, "Dialog list, read state, chat actions."),
    ("Messages", Messages, "Sending, editing, history, search, reactions, polls, drafts."),
    ("Media", Media, "Uploads, downloads, media messages, avatars, wallpapers."),
    ("Groups", Groups, ""),
    ("Channels", Channels, ""),
    ("Join links", JoinLinksMixin, ""),
    ("Stickers, GIFs and folders", Stickers, ""),
    ("Settings and security", Settings, ""),
    ("Bots (user side), services, wallet, live and voice chats", Services, ""),
    ("Rubino", Rubino, ""),
    (
        "Bot API",
        BotApi,
        "Only on `Client(token=...)`. Shared methods such as `send_message` or `get_me` switch to the Bot API automatically.",
    ),
    ("Updates", UpdatesMixin, "Receiving updates over the socket or by polling; the background listener."),
    ("Low level", Advanced, "The invoke seam for raw methods."),
]

TAG_RE = re.compile(r"\[(HTTP|WS|both|bot)\]")


def first_line(doc: str | None) -> str:
    if not doc:
        return ""
    text = inspect.cleandoc(doc)
    paragraph = text.split("\n\n")[0].replace("\n", " ")
    return TAG_RE.sub("", paragraph).strip()


def tags(doc: str | None, cls: type) -> str:
    found = TAG_RE.findall(doc or "")
    if found:
        return " ".join(f"[{t}]" for t in dict.fromkeys(found))
    if cls is BotApi:
        return "[bot]"
    if cls is Client:
        return "[both]"
    return "[HTTP]"


def signature(func) -> str:
    try:
        sig = inspect.signature(func)
    except (TypeError, ValueError):
        return "(...)"
    params = [p for name, p in sig.parameters.items() if name != "self"]
    parts = []
    for p in params:
        text = p.name
        if p.kind is p.VAR_POSITIONAL:
            text = "*" + text
        elif p.kind is p.VAR_KEYWORD:
            text = "**" + text
        if p.default is not p.empty:
            default = p.default
            if isinstance(default, str) or default is None or isinstance(default, (bool, int, float)):
                rep = repr(default)
            elif isinstance(default, tuple) and not default:
                rep = "()"
            else:
                rep = getattr(default, "__name__", None) or getattr(default, "value", None) or "…"
                rep = str(rep)
            text += f"={rep}"
        parts.append(text)
    # keyword-only marker
    kw_index = next((i for i, p in enumerate(params) if p.kind is p.KEYWORD_ONLY), None)
    if kw_index is not None and not any(p.kind is p.VAR_POSITIONAL for p in params):
        parts.insert(kw_index, "*")
    return "(" + ", ".join(parts) + ")"


def own_methods(cls: type):
    names = sorted(vars(cls))
    result = []
    for name in names:
        if name.startswith("_"):
            continue
        value = vars(cls)[name]
        if isinstance(value, property):
            continue
        func = value
        if isinstance(value, (staticmethod, classmethod)):
            func = value.__func__
        if not callable(func):
            continue
        result.append((name, func))
    return result


def main() -> None:
    out = [
        "# Method reference",
        "",
        "Generated from the docstrings of `rubigram.Client` (run `python tools/gen_method_reference.py`).",
        "",
        "Tags: `[HTTP]` encrypted RPC over HTTPS, `[WS]` needs the socket (Transport.WS), `[both]` works in either mode, `[bot]` Bot API (`Client(token=...)`).",
        "Every method is `async` unless it is marked *sync*. Any `object_guid` argument also accepts a `Peer`, a typed object with a guid, or `peer=`.",
        "",
    ]
    seen: set[str] = set()
    for title, cls, intro in SECTIONS:
        rows = []
        for name, func in own_methods(cls):
            if name in seen:
                continue
            seen.add(name)
            doc = inspect.getdoc(func) or ""
            is_alias = getattr(func, "__name__", name) != name
            summary = first_line(doc)
            if is_alias:
                summary = f"Alias of `{func.__name__}`. " + summary
            kind = "" if inspect.iscoroutinefunction(func) else " *(sync)*"
            rows.append(f"| `{name}{signature(func)}`{kind} | {tags(doc, cls)} | {summary} |")
        if not rows:
            continue
        out.append(f"## {title}")
        out.append("")
        if intro:
            out.append(intro)
            out.append("")
        out.append("| Method | Transport | Description |")
        out.append("|---|---|---|")
        out.extend(rows)
        out.append("")
    (ROOT / "docs" / "method-reference.md").write_text("\n".join(out), encoding="utf-8")
    print(f"wrote docs/method-reference.md with {len(seen)} methods")


if __name__ == "__main__":
    main()
