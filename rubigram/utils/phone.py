"""Phone number normalization for the login flow."""

from __future__ import annotations

_PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def normalize_phone_number(value: str, *, default_country_code: str = "98") -> str:
    """Return the international number without ``+`` (``09121234567`` → ``989121234567``).

    Rules: Persian/Arabic digits are converted, non-digits removed, a leading
    ``+`` or ``00`` dropped, and a single leading ``0`` replaced by the default
    country code.
    """
    digits = "".join(ch for ch in str(value).translate(_PERSIAN_DIGITS) if ch.isdigit())
    if digits.startswith("00"):
        digits = digits[2:]
    elif digits.startswith("0"):
        digits = default_country_code + digits[1:]
    return digits


def looks_like_phone_number(value: str) -> bool:
    stripped = str(value).strip()
    if not stripped:
        return False
    return all(ch.isdigit() or ch.isspace() or ch in "+-()" for ch in stripped.translate(_PERSIAN_DIGITS))


def looks_like_bot_token(value: str) -> bool:
    stripped = str(value).strip()
    return bool(stripped) and not looks_like_phone_number(stripped)


__all__ = ["normalize_phone_number", "looks_like_phone_number", "looks_like_bot_token"]
