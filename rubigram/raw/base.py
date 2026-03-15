from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar, Dict, Generic, Literal, TypeVar, cast

if TYPE_CHECKING:
    import rubigram

ResultT = TypeVar("ResultT", covariant=True)


@dataclass
class RawMethod(ABC, Generic[ResultT]):
    """
    Base class for all raw API methods.

    Concrete implementations define:
    - ``method_name``: Rubika RPC method name
    - ``auth_mode``: which session key should encrypt the request
    - ``unwrap_auth_on_success``: whether the response contains a new auth
    """
    method_name: ClassVar[str]
    auth_mode: ClassVar[Literal["auth", "tmp"]] = "auth"
    unwrap_auth_on_success: ClassVar[bool] = False

    @abstractmethod
    def to_input(self) -> Dict[str, Any]:
        """Convert the raw method fields into the RPC input payload."""

    @property
    def name(self) -> str:
        return type(self).method_name

    def parse_response(self, client: "rubigram.Client", data: Any) -> ResultT:
        from rubigram.types import RawObject

        return cast(ResultT, RawObject._parse(client, data))

    def __post_init__(self):
        """Validate that the method is not instantiated directly."""
        if type(self) is RawMethod:
            raise TypeError("RawMethod cannot be instantiated directly")
