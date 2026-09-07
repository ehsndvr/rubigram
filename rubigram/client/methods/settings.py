"""Settings, privacy, two-step verification, phone change, account deletion."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional

from rubigram.raw.functions import build_settings_input
from rubigram.raw.methods import (
    AbortSetRecoveryEmail,
    AbortTwoStepSetup,
    ChangePassword,
    CheckTwoStepPasscode,
    GetAppearanceSetting,
    GetPrivacySetting,
    GetTwoPasscodeStatus,
    GetUserSetting,
    RequestChangePhoneNumber,
    RequestDeleteAccount,
    RequestRecoveryEmail,
    ResendCodeRecoveryEmail,
    SetSetting,
    SetupTwoStepVerification,
    TurnOffTwoStep,
    VerifyChangePhoneNumber,
    VerifyRecoveryEmail,
)
from rubigram.types import ChangePhoneRequest, Empty, PrivacySettingResult, RawObject, TwoStepStatusResult, UserSettingResult
from rubigram.utils import normalize_phone_number

if TYPE_CHECKING:  # pragma: no cover
    from rubigram.client.client import Client


class Settings:
    async def get_privacy_setting(self: "Client") -> PrivacySettingResult:
        """``getPrivacySetting``. [HTTP]"""
        return await self.invoke(GetPrivacySetting())

    async def get_user_setting(self: "Client") -> UserSettingResult:
        """``getUserSetting``. [HTTP]"""
        return await self.invoke(GetUserSetting())

    async def get_appearance_setting(self: "Client") -> RawObject:
        return await self.invoke(GetAppearanceSetting())

    async def set_setting(self: "Client", **settings: Any) -> RawObject:
        """Update privacy/notification settings (``setSetting``), e.g. ``set_setting(show_my_phone_number="Nobody")``. [HTTP]"""
        payload = build_settings_input({key: (value.value if hasattr(value, "value") else value) for key, value in settings.items()})
        return await self.invoke(SetSetting(**payload))

    async def set_privacy(self: "Client", **settings: Any) -> RawObject:
        return await self.set_setting(**settings)

    # -- two-step verification ------------------------------------------------------

    async def get_two_passcode_status(self: "Client") -> TwoStepStatusResult:
        return await self.invoke(GetTwoPasscodeStatus())

    async def setup_two_step_verification(self: "Client", password: str, *, hint: Optional[str] = None, recovery_email: Optional[str] = None) -> TwoStepStatusResult:
        return await self.invoke(SetupTwoStepVerification(password=password, hint=hint, recovery_email=recovery_email))

    async def check_two_step_passcode(self: "Client", password: str) -> RawObject:
        return await self.invoke(CheckTwoStepPasscode(password=password))

    async def change_password(self: "Client", password: str, new_password: str, *, new_hint: Optional[str] = None) -> TwoStepStatusResult:
        return await self.invoke(ChangePassword(password=password, new_password=new_password, new_hint=new_hint))

    async def turn_off_two_step(self: "Client", password: str) -> TwoStepStatusResult:
        return await self.invoke(TurnOffTwoStep(password=password))

    async def request_recovery_email(self: "Client", password: str, recovery_email: str) -> TwoStepStatusResult:
        return await self.invoke(RequestRecoveryEmail(password=password, recovery_email=recovery_email))

    async def verify_recovery_email(self: "Client", password: str, code: str) -> TwoStepStatusResult:
        return await self.invoke(VerifyRecoveryEmail(password=password, code=code))

    async def resend_code_recovery_email(self: "Client", password: str) -> RawObject:
        return await self.invoke(ResendCodeRecoveryEmail(password=password))

    async def abort_set_recovery_email(self: "Client", password: str) -> TwoStepStatusResult:
        return await self.invoke(AbortSetRecoveryEmail(password=password))

    async def abort_two_step_setup(self: "Client") -> RawObject:
        return await self.invoke(AbortTwoStepSetup())

    # -- phone number and account --------------------------------------------------------

    async def request_change_phone_number(self: "Client", new_phone_number: str) -> ChangePhoneRequest:
        return await self.invoke(RequestChangePhoneNumber(new_phone_number=normalize_phone_number(new_phone_number)))

    async def verify_change_phone_number(self: "Client", code: str, hash: str) -> RawObject:
        return await self.invoke(VerifyChangePhoneNumber(code=code, hash=hash))

    async def request_delete_account(self: "Client") -> Empty:
        """Ask Rubika to delete the account (``requestDeleteAccount``). [HTTP]"""
        return await self.invoke(RequestDeleteAccount())


__all__ = ["Settings"]
