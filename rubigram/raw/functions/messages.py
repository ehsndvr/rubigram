"""Text formatting: parse modes and entities to Rubika ``metadata``."""

from __future__ import annotations

import html
import re
from typing import Any, Callable, Dict, Optional, Sequence

from rubigram.enums import MessageEntityType, ParseMode
from rubigram.types.formatting import MessageEntity

_MARKDOWN_PATTERNS: tuple[tuple[re.Pattern[str], MessageEntityType], ...] = (
    (re.compile(r"\*\*(.+?)\*\*", re.DOTALL), MessageEntityType.BOLD),
    (re.compile(r"__(.+?)__", re.DOTALL), MessageEntityType.ITALIC),
    (re.compile(r"`(.+?)`", re.DOTALL), MessageEntityType.MONO),
)
_HTML_TAGS: Dict[str, MessageEntityType] = {
    "b": MessageEntityType.BOLD,
    "strong": MessageEntityType.BOLD,
    "i": MessageEntityType.ITALIC,
    "em": MessageEntityType.ITALIC,
    "code": MessageEntityType.MONO,
    "pre": MessageEntityType.MONO,
}
_HTML_TAG_RE = re.compile(r"<(/?)(b|strong|i|em|code|pre)>", re.IGNORECASE)


def entities_to_metadata(entities: Sequence[MessageEntity]) -> Optional[Dict[str, Any]]:
    """``metadata`` block for explicit entities (``None`` when empty)."""
    if not entities:
        return None
    return {"meta_data_parts": [entity.to_metadata_part() for entity in entities]}


def _extract(text: str, patterns: Sequence[tuple[re.Pattern[str], MessageEntityType]]) -> tuple[str, list[MessageEntity]]:
    """Strip one layer of markers and record entities on the plain text."""
    entities: list[MessageEntity] = []
    plain = text
    for pattern, entity_type in patterns:
        parts: list[str] = []
        cursor = 0
        plain_length = 0
        new_entities: list[MessageEntity] = []
        for match in pattern.finditer(plain):
            start, end = match.span()
            parts.append(plain[cursor:start])
            plain_length += start - cursor
            inner = match.group(1)
            parts.append(inner)
            new_entities.append(MessageEntity(entity_type, plain_length, len(inner)))
            plain_length += len(inner)
            cursor = end
        parts.append(plain[cursor:])
        if new_entities:
            removed_before: Callable[[int], int] = lambda offset, _pattern=pattern, _plain=plain: sum(  # noqa: E731
                (m.end() - m.start()) - len(m.group(1)) for m in _pattern.finditer(_plain) if m.end() <= offset
            )
            entities = [MessageEntity(e.type, e.offset - removed_before(e.offset), e.length) for e in entities]
            entities.extend(new_entities)
            plain = "".join(parts)
    entities.sort(key=lambda e: e.offset)
    return plain, entities


def parse_markdown(text: str) -> tuple[str, list[MessageEntity]]:
    """``**bold**``, ``__italic__`` and ```` `mono` ```` markers to entities."""
    return _extract(text, _MARKDOWN_PATTERNS)


def parse_html(text: str) -> tuple[str, list[MessageEntity]]:
    """``<b>``, ``<i>``, ``<code>`` (and their aliases) to entities; other text is unescaped."""
    entities: list[MessageEntity] = []
    plain_parts: list[str] = []
    open_tags: list[tuple[MessageEntityType, int]] = []
    cursor = 0
    plain_length = 0
    for match in _HTML_TAG_RE.finditer(text):
        chunk = html.unescape(text[cursor : match.start()])
        plain_parts.append(chunk)
        plain_length += len(chunk)
        closing, tag = match.group(1), match.group(2).lower()
        entity_type = _HTML_TAGS[tag]
        if not closing:
            open_tags.append((entity_type, plain_length))
        else:
            for index in range(len(open_tags) - 1, -1, -1):
                if open_tags[index][0] is entity_type:
                    _, start = open_tags.pop(index)
                    if plain_length > start:
                        entities.append(MessageEntity(entity_type, start, plain_length - start))
                    break
        cursor = match.end()
    tail = html.unescape(text[cursor:])
    plain_parts.append(tail)
    entities.sort(key=lambda e: e.offset)
    return "".join(plain_parts), entities


def normalize_parse_mode(parse_mode: Any) -> Optional[ParseMode]:
    if parse_mode is None:
        return None
    if isinstance(parse_mode, ParseMode):
        return parse_mode
    value = str(parse_mode).strip().lower()
    if value in {"markdown", "md"}:
        return ParseMode.MARKDOWN
    if value == "html":
        return ParseMode.HTML
    if value in {"default", "none", ""}:
        return ParseMode.DEFAULT
    raise ValueError(f"Unsupported parse_mode: {parse_mode!r}")


def build_message_metadata(
    text: Optional[str], *, entities: Optional[Sequence[MessageEntity]] = None, parse_mode: Any = None
) -> tuple[Optional[str], Optional[Dict[str, Any]]]:
    """Return ``(plain_text, metadata)`` for ``sendMessage`` / ``editMessage``.

    Either explicit ``entities`` or a ``parse_mode`` may be given, not both.
    """
    if text is None:
        if entities:
            raise ValueError("entities require a text message")
        return None, None
    if entities and parse_mode is not None:
        raise ValueError("Use either entities or parse_mode, not both")
    if entities:
        return text, entities_to_metadata(entities)
    mode = normalize_parse_mode(parse_mode)
    if mode is None or mode is ParseMode.DEFAULT:
        return text, None
    plain, parsed = parse_markdown(text) if mode is ParseMode.MARKDOWN else parse_html(text)
    return plain, entities_to_metadata(parsed)


__all__ = ["build_message_metadata", "entities_to_metadata", "normalize_parse_mode", "parse_html", "parse_markdown"]
