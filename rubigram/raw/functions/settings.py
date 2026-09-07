"""``updated_parameters`` / ``update_parameters`` helpers."""

from __future__ import annotations

import enum
from typing import Any, Dict, Optional, Sequence


def _plain(value: Any) -> Any:
    if isinstance(value, enum.Enum):
        return value.value
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    if hasattr(value, "to_dict"):
        return value.to_dict()
    return value


def build_updated_parameters(fields: Dict[str, Any], *, allowed: Optional[Sequence[str]] = None) -> tuple[Dict[str, Any], list[str]]:
    """Split ``fields`` into the non-``None`` values and the list of their names.

    Used by ``editGroupInfo``, ``editChannelInfo``, ``updateProfile``,
    ``editFolder``, ``setGroupVoiceChatSetting`` and ``setLiveSetting``.
    """
    values: Dict[str, Any] = {}
    names: list[str] = []
    for key, value in fields.items():
        if value is None:
            continue
        if allowed is not None and key not in allowed:
            raise ValueError(f"{key!r} is not an updatable parameter (allowed: {', '.join(allowed)})")
        values[key] = _plain(value)
        names.append(key)
    return values, names


def build_settings_input(settings: Dict[str, Any]) -> Dict[str, Any]:
    """``setSetting`` input: ``{"settings": {...}, "update_parameters": [...]}``."""
    values, names = build_updated_parameters(settings)
    if not names:
        raise ValueError("At least one setting must be provided")
    return {"settings": values, "update_parameters": names}


__all__ = ["build_updated_parameters", "build_settings_input"]
