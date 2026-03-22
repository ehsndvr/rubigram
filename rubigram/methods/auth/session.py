from __future__ import annotations

import rubigram
from rubigram.raw.methods import RegisterDevice, SendCode, SignIn, SignUp
from rubigram.types import Authorization, Empty, SentCode
from rubigram.exceptions import LoginRequired


class SessionAuth:
    async def send_code(self: "rubigram.Client", phone_number: str) -> SentCode:
        return await self.invoke(SendCode(phone_number=self._normalize_phone_number(phone_number)))

    async def sign_in(
        self: "rubigram.Client",
        phone_number: str,
        phone_code_hash: str,
        phone_code: str,
    ) -> Authorization:
        return await self.invoke(
            SignIn(
                phone_number=self._normalize_phone_number(phone_number),
                phone_code_hash=phone_code_hash,
                phone_code=phone_code,
            )
        )

    async def sign_up(
        self: "rubigram.Client",
        first_name: str,
        last_name: str = "",
    ) -> Authorization:
        return await self.invoke(SignUp(first_name=first_name, last_name=last_name))

    async def register_device(self: "rubigram.Client", force: bool = False) -> Empty:
        if not self.enable_register_device:
            return Empty()

        auth = await self.storage.auth()
        if not auth:
            raise LoginRequired("registerDevice requires an authenticated session")

        if not force:
            if await self.storage.registered_device() and await self.storage.registered_device_version() == self.APP_VERSION:
                return Empty()

        await self.storage.set_registered_device(False)
        await self.storage.set_registered_device_version(None)
        device_hash = await self._ensure_device_hash()
        result = await self._invoke_once(
            RegisterDevice(
                token_type=self.REGISTER_DEVICE_TOKEN_TYPE,
                token="",
                app_version=self._register_device_app_version(),
                lang_code=self.device_info["lang_code"],
                system_version=self.system_version,
                device_model=self.device_model,
                device_hash=device_hash,
            ),
            allow_register_retry=False,
        )
        await self.storage.set_registered_device(True)
        await self.storage.set_registered_device_version(self.APP_VERSION)
        return result
