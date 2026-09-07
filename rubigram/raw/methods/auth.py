"""Login, device registration and session RPCs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from rubigram.raw.base import RawMethod
from rubigram.types import Authorization, Empty, MySessions, SentCode, TimeResult, UnconfirmedSessions


@dataclass
class SendCode(RawMethod[SentCode]):
    """Send a login code; needs a temporary session (``tmp_session``)."""

    phone_number: str
    send_type: str = "SMS"
    pass_key: Optional[str] = None

    method_name = "sendCode"
    auth_mode = "tmp"
    api_version = "6"
    result = SentCode


@dataclass
class SignIn(RawMethod[Authorization]):
    """Confirm the code; the response carries the new ``auth`` (RSA-encrypted)."""

    phone_number: str
    phone_code_hash: str
    phone_code: str
    public_key: Optional[str] = None

    method_name = "signIn"
    auth_mode = "tmp"
    api_version = "6"
    unwrap_auth_on_success = True
    result = Authorization


@dataclass
class SignUp(RawMethod[Authorization]):
    """Register a new account after ``signIn`` reported it does not exist.

    Not used by the web client (kept from rubigram 0.1; unverified against the
    current server).
    """

    first_name: str
    last_name: Optional[str] = ""
    public_key: Optional[str] = None

    method_name = "signUp"
    auth_mode = "tmp"
    api_version = "6"
    unwrap_auth_on_success = True
    result = Authorization


@dataclass
class LoginTwoStepForgetPassword(RawMethod[Any]):
    phone_number: str

    method_name = "loginTwoStepForgetPassword"
    auth_mode = "tmp"


@dataclass
class LoginDisableTwoStep(RawMethod[Any]):
    phone_number: str
    phone_code_hash: Optional[str] = None
    phone_code: Optional[str] = None
    email_code: Optional[str] = None

    method_name = "loginDisableTwoStep"
    auth_mode = "tmp"


@dataclass
class RegisterDevice(RawMethod[Empty]):
    token_type: str
    token: str
    app_version: str
    lang_code: str
    system_version: str
    device_model: str
    device_hash: str

    method_name = "registerDevice"
    result = Empty


@dataclass
class UnregisterDevice(RawMethod[Empty]):
    """Sent unencrypted (plain JSON with ``auth``) like the web client does."""

    device: Optional[Dict[str, Any]] = None

    method_name = "unregisterDevice"
    auth_mode = "none"
    api_version = "4"
    result = Empty

    def to_input(self) -> Dict[str, Any]:
        return dict(self.device or {})


@dataclass
class Logout(RawMethod[Empty]):
    method_name = "logout"
    result = Empty


@dataclass
class GetTime(RawMethod[TimeResult]):
    method_name = "getTime"
    retries = 3
    result = TimeResult


@dataclass
class GetMySessions(RawMethod[MySessions]):
    method_name = "getMySessions"
    result = MySessions


@dataclass
class TerminateSession(RawMethod[Empty]):
    session_key: str

    method_name = "terminateSession"
    result = Empty


@dataclass
class TerminateOtherSessions(RawMethod[Empty]):
    method_name = "terminateOtherSessions"
    result = Empty


@dataclass
class GetUnconfirmedSessions(RawMethod[UnconfirmedSessions]):
    method_name = "getUnconfirmedSessions"
    result = UnconfirmedSessions


@dataclass
class ActionOnUnconfirmedSession(RawMethod[Empty]):
    unconfirmed_session_key: str
    action: str

    method_name = "actionOnUnconfirmedSession"
    result = Empty


__all__ = [
    "ActionOnUnconfirmedSession",
    "GetMySessions",
    "GetTime",
    "GetUnconfirmedSessions",
    "LoginDisableTwoStep",
    "LoginTwoStepForgetPassword",
    "Logout",
    "RegisterDevice",
    "SendCode",
    "SignIn",
    "SignUp",
    "TerminateOtherSessions",
    "TerminateSession",
    "UnregisterDevice",
]
