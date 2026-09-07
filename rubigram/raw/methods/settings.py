"""Settings, privacy, two-step verification, phone change and account deletion RPCs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from rubigram.raw.base import RawMethod
from rubigram.types import ChangePhoneRequest, Empty, PrivacySettingResult, TwoStepStatusResult, UserSettingResult


@dataclass
class GetPrivacySetting(RawMethod[PrivacySettingResult]):
    method_name = "getPrivacySetting"
    result = PrivacySettingResult


@dataclass
class GetUserSetting(RawMethod[UserSettingResult]):
    method_name = "getUserSetting"
    result = UserSettingResult


@dataclass
class GetAppearanceSetting(RawMethod[Any]):
    method_name = "getAppearanceSetting"


@dataclass
class SetSetting(RawMethod[Any]):
    settings: Dict[str, Any]
    update_parameters: List[str]

    method_name = "setSetting"


@dataclass
class GetTwoPasscodeStatus(RawMethod[TwoStepStatusResult]):
    method_name = "getTwoPasscodeStatus"
    result = TwoStepStatusResult


@dataclass
class SetupTwoStepVerification(RawMethod[TwoStepStatusResult]):
    password: str
    hint: Optional[str] = None
    recovery_email: Optional[str] = None

    method_name = "setupTwoStepVerification"
    result = TwoStepStatusResult


@dataclass
class CheckTwoStepPasscode(RawMethod[Any]):
    password: str

    method_name = "checkTwoStepPasscode"


@dataclass
class ChangePassword(RawMethod[TwoStepStatusResult]):
    password: str
    new_password: str
    new_hint: Optional[str] = None

    method_name = "changePassword"
    result = TwoStepStatusResult


@dataclass
class TurnOffTwoStep(RawMethod[TwoStepStatusResult]):
    password: str

    method_name = "turnOffTwoStep"
    result = TwoStepStatusResult


@dataclass
class RequestRecoveryEmail(RawMethod[TwoStepStatusResult]):
    password: str
    recovery_email: str

    method_name = "requestRecoveryEmail"
    result = TwoStepStatusResult


@dataclass
class VerifyRecoveryEmail(RawMethod[TwoStepStatusResult]):
    password: str
    code: str

    method_name = "verifyRecoveryEmail"
    result = TwoStepStatusResult


@dataclass
class ResendCodeRecoveryEmail(RawMethod[Any]):
    password: str

    method_name = "resendCodeRecoveryEmail"


@dataclass
class AbortSetRecoveryEmail(RawMethod[TwoStepStatusResult]):
    password: str

    method_name = "abortSetRecoveryEmail"
    result = TwoStepStatusResult


@dataclass
class AbortTwoStepSetup(RawMethod[Any]):
    method_name = "abortTwoStepSetup"


@dataclass
class RequestChangePhoneNumber(RawMethod[ChangePhoneRequest]):
    new_phone_number: str

    method_name = "requestChangePhoneNumber"
    result = ChangePhoneRequest


@dataclass
class VerifyChangePhoneNumber(RawMethod[Any]):
    code: str
    hash: str

    method_name = "verifyChangePhoneNumber"


@dataclass
class RequestDeleteAccount(RawMethod[Empty]):
    method_name = "requestDeleteAccount"
    result = Empty


__all__ = [
    "AbortSetRecoveryEmail",
    "AbortTwoStepSetup",
    "ChangePassword",
    "CheckTwoStepPasscode",
    "GetAppearanceSetting",
    "GetPrivacySetting",
    "GetTwoPasscodeStatus",
    "GetUserSetting",
    "RequestChangePhoneNumber",
    "RequestDeleteAccount",
    "RequestRecoveryEmail",
    "ResendCodeRecoveryEmail",
    "SetSetting",
    "SetupTwoStepVerification",
    "TurnOffTwoStep",
    "VerifyChangePhoneNumber",
    "VerifyRecoveryEmail",
]
