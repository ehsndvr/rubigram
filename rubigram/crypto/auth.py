from __future__ import annotations

import base64
import binascii

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey, RSAPublicKey


def rsa_sign(data: bytes, pem_private_key: str) -> str:
    private_key = serialization.load_pem_private_key(
        pem_private_key.encode("utf-8"),
        password=None,
        backend=default_backend(),
    )

    sig_bytes = private_key.sign(
        data,
        asym_padding.PKCS1v15(),
        hashes.SHA256(),
    )

    sig_hex = binascii.hexlify(sig_bytes).decode("utf-8")
    return base64.b64encode(binascii.unhexlify(sig_hex)).decode("utf-8")


def change_auth_type(public_key_b64: str) -> str:
    transformed = []
    for char in public_key_b64:
        if "a" <= char <= "z":
            transformed.append(chr(((32 - (ord(char) - 97)) % 26) + 97))
        elif "A" <= char <= "Z":
            transformed.append(chr(((29 - (ord(char) - 65)) % 26) + 65))
        elif "0" <= char <= "9":
            transformed.append(chr(((13 - (ord(char) - 48)) % 10) + 48))
        else:
            transformed.append(char)
    return "".join(transformed)


def _encode_public_key_for_login(public_key: RSAPublicKey) -> str:
    public_pem = _export_public_key_pem(public_key)
    return change_auth_type(base64.b64encode(public_pem.encode("utf-8")).decode("utf-8"))


def _export_public_key_pem(public_key: RSAPublicKey) -> str:
    public_der = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return public_der.decode("utf-8").strip()


def _export_private_key_pem(private_key: RSAPrivateKey) -> str:
    return private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8").strip()


def export_public_key_for_login(pem_private_key: str) -> str:
    private_key = serialization.load_pem_private_key(
        pem_private_key.encode("utf-8"),
        password=None,
        backend=default_backend(),
    )
    return _encode_public_key_for_login(private_key.public_key())


def rsa_key_generate() -> tuple[str, str]:
    """
    Match the original web-client flow:
    1. generate a 1024-bit RSA keypair
    2. export the public key
    3. base64 it
    4. pass it through changeAuthType
    5. export the private key PEM
    """
    key_pair = rsa.generate_private_key(
        public_exponent=65537,
        key_size=1024,
        backend=default_backend(),
    )
    public = _encode_public_key_for_login(key_pair.public_key())
    private = _export_private_key_pem(key_pair)
    return public, private


def generate_rsa_key_pair() -> tuple[str, str]:
    """Generate a login RSA key pair and return `(public_key, private_key_pem)`."""
    return rsa_key_generate()


class AuthSigner:
    """Provider for RSA signature generation."""

    def __init__(self, pem_private_key: str):
        self._pem = pem_private_key

    def sign(self, data: bytes) -> str:
        return rsa_sign(data, self._pem)


class AuthUnwrapper:
    """
    Decrypt the auth returned by the server after successful login/signup.

    The user-provided client code decrypts auth with PKCS1_OAEP default params.
    OAEP/SHA1 is tried first, with PKCS#1 v1.5 and OAEP/SHA256 kept as fallbacks
    for tolerance against server-side/client-version differences.
    """

    def __init__(self, pem_private_key: str):
        self._pem = pem_private_key

    def unwrap(self, encrypted_auth: str) -> str:
        private_key = serialization.load_pem_private_key(
            self._pem.encode("utf-8"),
            password=None,
            backend=default_backend(),
        )
        decoded = base64.b64decode(encrypted_auth)

        paddings = [
            asym_padding.OAEP(
                mgf=asym_padding.MGF1(algorithm=hashes.SHA1()),
                algorithm=hashes.SHA1(),
                label=None,
            ),
            asym_padding.PKCS1v15(),
            asym_padding.OAEP(
                mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        ]

        for padding_scheme in paddings:
            try:
                unwrapped = private_key.decrypt(decoded, padding_scheme)
                return unwrapped.decode("utf-8")
            except Exception:
                continue

        raise ValueError("Failed to unwrap auth with supported RSA paddings")
