from __future__ import annotations

import base64
import json

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


def create_secret_passphrase(value: str) -> str:
    """Derive the AES key material used by Rubika from auth/tmp_session."""
    t = value[:8]
    i = value[8:16]
    n = value[16:24] + t + value[24:32] + i

    result: list[str] = []
    for ch in n:
        if "0" <= ch <= "9":
            new_ch = chr((ord(ch) - ord("0") + 5) % 10 + ord("0"))
        else:
            new_ch = chr((ord(ch) - ord("a") + 9) % 26 + ord("a"))
        result.append(new_ch)

    return "".join(result)


def caesar_encode(value: str) -> str:
    """Apply Rubika's auth obfuscation to the auth field sent in requests."""
    result: list[str] = []

    for ch in value:
        if "0" <= ch <= "9":
            result.append(chr((ord(ch) - ord("0") + 3) % 10 + ord("0")))
        elif "A" <= ch <= "Z":
            result.append(chr((ord(ch) - ord("A") + 3) % 26 + ord("A")))
        else:
            old_offset = ord(ch) - ord("a")
            result.append(chr(((32 - old_offset) % 26) + ord("a")))

    return "".join(result)


def caesar_decode(value: str) -> str:
    """Reverse Rubika's auth obfuscation."""
    result: list[str] = []

    for ch in value:
        if "0" <= ch <= "9":
            result.append(chr((ord(ch) - ord("0") - 3) % 10 + ord("0")))
        elif "A" <= ch <= "Z":
            result.append(chr((ord(ch) - ord("A") - 3) % 26 + ord("A")))
        else:
            offset = ord(ch) - ord("a")
            result.append(chr(((32 - offset) % 26) + ord("a")))

    return "".join(result)


def decrypt_aes_cbc(ciphertext_b64: str, auth: str) -> dict:
    key = create_secret_passphrase(auth).encode("utf-8")
    iv = bytes([0] * 16)
    ciphertext = base64.b64decode(ciphertext_b64)

    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    padded_plain = decryptor.update(ciphertext) + decryptor.finalize()

    unpadder = padding.PKCS7(128).unpadder()
    plain_bytes = unpadder.update(padded_plain) + unpadder.finalize()
    return json.loads(plain_bytes.decode("utf-8"))


def encrypt_aes_cbc(data_obj: dict, auth: str) -> str:
    key = create_secret_passphrase(auth).encode("utf-8")
    plaintext = json.dumps(data_obj, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(plaintext) + padder.finalize()

    iv = bytes([0] * 16)
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(padded_data) + encryptor.finalize()

    return base64.b64encode(ciphertext).decode("utf-8")
