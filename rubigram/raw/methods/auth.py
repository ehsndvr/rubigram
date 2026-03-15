from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, Optional

from rubigram.raw.base import RawMethod
from rubigram.types import Authorization, Empty, SentCode

if TYPE_CHECKING:
    import rubigram


@dataclass
class SendCode(RawMethod[SentCode]):
    """
    Send a verification code to a phone number.

    This method requires a temporary session (tmp_session).
    """
    phone_number: str
    send_type: str = "SMS"

    method_name = "sendCode"
    auth_mode = "tmp"

    def to_input(self) -> Dict[str, Any]:
        return {
            "phone_number": self.phone_number,
            "send_type": self.send_type,
        }

    def parse_response(self, client: "rubigram.Client", data: Any) -> SentCode:
        return SentCode._parse(client, data)


@dataclass
class SignIn(RawMethod[Authorization]):
    """
    Sign in with a phone number, code hash, and verification code.

    This method requires a temporary session (tmp_session).

    Upon success, the response contains a new 'auth' key that must be
    unwrapped and saved to the session.
    """
    phone_number: str
    phone_code_hash: str
    phone_code: str
    public_key: Optional[str] = None

    method_name = "signIn"
    auth_mode = "tmp"
    unwrap_auth_on_success = True

    def to_input(self) -> Dict[str, Any]:
        input_data = {
            "phone_number": self.phone_number,
            "phone_code_hash": self.phone_code_hash,
            "phone_code": self.phone_code,
        }
        if self.public_key:
            input_data["public_key"] = self.public_key
        return input_data

    def parse_response(self, client: "rubigram.Client", data: Any) -> Authorization:
        return Authorization._parse(client, data)


@dataclass
class SignUp(RawMethod[Authorization]):
    """
    Sign up with a new account (typically after signIn).

    This method requires a temporary session (tmp_session).

    Upon success, the response contains a new 'auth' key that must be
    unwrapped and saved to the session.
    """
    first_name: str
    last_name: Optional[str] = ""
    public_key: Optional[str] = None

    method_name = "signUp"
    auth_mode = "tmp"
    unwrap_auth_on_success = True

    def to_input(self) -> Dict[str, Any]:
        input_data = {
            "first_name": self.first_name,
            "last_name": self.last_name,
        }
        if self.public_key:
            input_data["public_key"] = self.public_key
        return input_data

    def parse_response(self, client: "rubigram.Client", data: Any) -> Authorization:
        return Authorization._parse(client, data)


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

    def to_input(self) -> Dict[str, Any]:
        return {
            "token_type": self.token_type,
            "token": self.token,
            "app_version": self.app_version,
            "lang_code": self.lang_code,
            "system_version": self.system_version,
            "device_model": self.device_model,
            "device_hash": self.device_hash,
        }

    def parse_response(self, client: "rubigram.Client", data: Any) -> Empty:
        return Empty._parse(client, data or {})
