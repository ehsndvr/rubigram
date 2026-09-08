"""Settings, privacy, two-step verification, phone change, account deletion."""

from __future__ import annotations

from typing import Any, Optional

from rubigram.client.base import BaseClient
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


class Settings(BaseClient):
    async def get_privacy_setting(self) -> PrivacySettingResult:
        """``getPrivacySetting``. [HTTP]"""
        return await self.invoke(GetPrivacySetting())

    async def get_user_setting(self) -> UserSettingResult:
        """``getUserSetting``. [HTTP]"""
        return await self.invoke(GetUserSetting())

    async def get_appearance_setting(self) -> RawObject:
        """Theme and appearance settings (``getAppearanceSetting``). [HTTP]"""
        return await self.invoke(GetAppearanceSetting())

    async def set_setting(self, **settings: Any) -> RawObject:
        """Update privacy/notification settings (``setSetting``), e.g. ``set_setting(show_my_phone_number="Nobody")``. [HTTP]"""
        payload = build_settings_input({key: (value.value if hasattr(value, "value") else value) for key, value in settings.items()})
        return await self.invoke(SetSetting(**payload))

    async def set_privacy(self, **settings: Any) -> RawObject:
        """Alias of :meth:`set_setting`. [HTTP]"""
        return await self.set_setting(**settings)

    # -- two-step verification ------------------------------------------------------

    async def get_two_passcode_status(self) -> TwoStepStatusResult:
        """Whether two-step verification is enabled (``getTwoPasscodeStatus``). [HTTP]"""
        return await self.invoke(GetTwoPasscodeStatus())

    async def setup_two_step_verification(
        self, password: str, *, hint: Optional[str] = None, recovery_email: Optional[str] = None
    ) -> TwoStepStatusResult:
        """Enable two-step verification with a password (``setupTwoStepVerification``). [HTTP]"""
        return await self.invoke(SetupTwoStepVerification(password=password, hint=hint, recovery_email=recovery_email))

    async def check_two_step_passcode(self, password: str) -> RawObject:
        """Verify the two-step password (``checkTwoStepPasscode``). [HTTP]"""
        return await self.invoke(CheckTwoStepPasscode(password=password))

    async def change_password(self, password: str, new_password: str, *, new_hint: Optional[str] = None) -> TwoStepStatusResult:
        """Change the two-step password (``changePassword``). [HTTP]"""
        return await self.invoke(ChangePassword(password=password, new_password=new_password, new_hint=new_hint))

    async def turn_off_two_step(self, password: str) -> TwoStepStatusResult:
        """Disable two-step verification (``turnOffTwoStep``). [HTTP]"""
        return await self.invoke(TurnOffTwoStep(password=password))

    async def request_recovery_email(self, password: str, recovery_email: str) -> TwoStepStatusResult:
        """Set a recovery e-mail for two-step verification (``requestRecoveryEmail``). [HTTP]"""
        return await self.invoke(RequestRecoveryEmail(password=password, recovery_email=recovery_email))

    async def verify_recovery_email(self, password: str, code: str) -> TwoStepStatusResult:
        """Confirm the recovery e-mail with the received code (``verifyRecoveryEmail``). [HTTP]"""
        return await self.invoke(VerifyRecoveryEmail(password=password, code=code))

    async def resend_code_recovery_email(self, password: str) -> RawObject:
        """Resend the recovery e-mail code (``resendCodeRecoveryEmail``). [HTTP]"""
        return await self.invoke(ResendCodeRecoveryEmail(password=password))

    async def abort_set_recovery_email(self, password: str) -> TwoStepStatusResult:
        """Cancel a pending recovery e-mail change (``abortSetRecoveryEmail``). [HTTP]"""
        return await self.invoke(AbortSetRecoveryEmail(password=password))

    async def abort_two_step_setup(self) -> RawObject:
        """Cancel a pending two-step setup (``abortTwoStepSetup``). [HTTP]"""
        return await self.invoke(AbortTwoStepSetup())

    # -- phone number and account --------------------------------------------------------

    async def request_change_phone_number(self, new_phone_number: str) -> ChangePhoneRequest:
        """Start changing the account phone number (``requestChangePhoneNumber``). [HTTP]"""
        return await self.invoke(RequestChangePhoneNumber(new_phone_number=normalize_phone_number(new_phone_number)))

    async def verify_change_phone_number(self, code: str, hash: str) -> RawObject:
        """Confirm the new phone number with the received code (``verifyChangePhoneNumber``). [HTTP]"""
        return await self.invoke(VerifyChangePhoneNumber(code=code, hash=hash))

    async def request_delete_account(self) -> Empty:
        """Ask Rubika to delete the account (``requestDeleteAccount``). [HTTP]"""
        return await self.invoke(RequestDeleteAccount())


__all__ = ["Settings"]
