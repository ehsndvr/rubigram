from __future__ import annotations

from typing import Optional

from .auth import AuthSigner, AuthUnwrapper
from .cipher import caesar_encode, decrypt_aes_cbc, encrypt_aes_cbc


class Codec:
    """Build encrypted request payloads and decrypt Rubika responses."""

    def __init__(self, signer: AuthSigner, unwrapper: AuthUnwrapper):
        self.signer = signer
        self.unwrapper = unwrapper

    def build_payload(
        self,
        api_version: str,
        auth: str,
        data_obj: dict,
        tmp_session: Optional[str] = None,
    ) -> dict:
        request_key = auth if auth else (tmp_session or "")
        data_enc = encrypt_aes_cbc(data_obj, request_key)
        auth_hash = caesar_encode(auth) if auth else ""
        sign_b64 = self.signer.sign(data_enc.encode("utf-8"))

        return {
            "api_version": api_version,
            "auth": auth_hash,
            "data_enc": data_enc,
            "sign": sign_b64,
        }

    def build_tmp_payload(
        self,
        api_version: str,
        tmp_session: str,
        data_obj: dict,
    ) -> dict:
        return {
            "api_version": api_version,
            "tmp_session": tmp_session,
            "data_enc": encrypt_aes_cbc(data_obj, tmp_session),
        }

    def decrypt_response(self, payload: dict, request_key: str) -> dict:
        return decrypt_aes_cbc(payload["data_enc"], request_key)

    def unwrap_server_auth(self, encrypted_auth: str) -> str:
        return self.unwrapper.unwrap(encrypted_auth)
