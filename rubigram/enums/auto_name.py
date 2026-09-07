from enum import Enum
from typing import Any


class AutoName(Enum):
    """Enum whose ``auto()`` values are the lower-cased member names."""

    @staticmethod
    def _generate_next_value_(name: str, start: int, count: int, last_values: list[Any]) -> str:
        return name.lower()

    def __repr__(self) -> str:
        return f"rubigram.enums.{self}"
