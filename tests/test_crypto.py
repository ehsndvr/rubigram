import base64

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding as asym_padding

from rubigram.crypto import (
    AuthSigner,
    AuthUnwrapper,
    Codec,
    caesar_decode,
    caesar_encode,
    change_auth_type,
    create_secret_passphrase,
    decrypt_aes_cbc,
    encrypt_aes_cbc,
    export_public_key_for_login,
    generate_rsa_key_pair,
    rsa_key_generate,
)


def test_caesar_round_trip():
    value = "zjbyfpwfoxtvhfgdlohvtjcczxxqhsnb"
    assert caesar_decode(caesar_encode(value)) == value


def test_secret_passphrase_derivation_is_32_chars():
    value = "zjbyfpwfoxtvhfgdlohvtjcczxxqhsnb"
    assert len(create_secret_passphrase(value)) == 32


def test_aes_encrypt_decrypt_round_trip():
    auth = "zjbyfpwfoxtvhfgdlohvtjcczxxqhsnb"
    data = {"method": "getUserInfo", "input": {"user_guid": "u123"}}
    ciphertext = encrypt_aes_cbc(data, auth)
    assert decrypt_aes_cbc(ciphertext, auth) == data


def test_codec_build_payload_supports_auth_and_tmp_session():
    _, private_pem = generate_rsa_key_pair()
    signer = AuthSigner(private_pem)
    unwrapper = AuthUnwrapper(private_pem)
    codec = Codec(signer, unwrapper)
    data = {"method": "sendCode", "input": {"phone_number": "98912"}}

    auth_payload = codec.build_payload("6", "zjbyfpwfoxtvhfgdlohvtjcczxxqhsnb", data)
    tmp_payload = codec.build_tmp_payload("6", "abcdefghijklmnopqrstuvwxyzabcdef", data)

    assert auth_payload["auth"]
    assert "auth" not in tmp_payload
    assert "sign" not in tmp_payload
    assert tmp_payload["tmp_session"] == "abcdefghijklmnopqrstuvwxyzabcdef"
    assert decrypt_aes_cbc(
        auth_payload["data_enc"],
        "zjbyfpwfoxtvhfgdlohvtjcczxxqhsnb",
    ) == data
    assert decrypt_aes_cbc(
        tmp_payload["data_enc"],
        "abcdefghijklmnopqrstuvwxyzabcdef",
    ) == data


def test_auth_unwrapper_supports_pkcs1_v15():
    _, private_pem = generate_rsa_key_pair()
    private_key = serialization.load_pem_private_key(
        private_pem.encode("utf-8"),
        password=None,
        backend=default_backend(),
    )
    public_key = private_key.public_key()
    expected_auth = "zjbyfpwfoxtvhfgdlohvtjcczxxqhsnb"
    encrypted_auth = base64.b64encode(
        public_key.encrypt(
            expected_auth.encode("utf-8"),
            asym_padding.PKCS1v15(),
        )
    ).decode("utf-8")

    unwrapper = AuthUnwrapper(private_pem)
    assert unwrapper.unwrap(encrypted_auth) == expected_auth


def test_auth_unwrapper_supports_oaep_sha1():
    _, private_pem = generate_rsa_key_pair()
    private_key = serialization.load_pem_private_key(
        private_pem.encode("utf-8"),
        password=None,
        backend=default_backend(),
    )
    public_key = private_key.public_key()
    expected_auth = "zjbyfpwfoxtvhfgdlohvtjcczxxqhsnb"
    encrypted_auth = base64.b64encode(
        public_key.encrypt(
            expected_auth.encode("utf-8"),
            asym_padding.OAEP(
                mgf=asym_padding.MGF1(algorithm=hashes.SHA1()),
                algorithm=hashes.SHA1(),
                label=None,
            ),
        )
    ).decode("utf-8")

    unwrapper = AuthUnwrapper(private_pem)
    assert unwrapper.unwrap(encrypted_auth) == expected_auth


def test_change_auth_type_matches_known_transform():
    assert change_auth_type("AbcXYZ019+/=") == "DfeGFE324+/="


def test_rsa_key_generate_returns_usable_public_and_private_keys():
    public_key, private_pem = rsa_key_generate()
    private_key = serialization.load_pem_private_key(
        private_pem.encode("utf-8"),
        password=None,
        backend=default_backend(),
    )
    raw_public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8").strip()
    raw_public_b64 = base64.b64encode(raw_public_pem.encode("utf-8")).decode("utf-8")

    assert "BEGIN RSA PRIVATE KEY" in private_pem
    assert not private_pem.endswith("\n")
    assert public_key == export_public_key_for_login(private_pem)
    assert public_key != raw_public_b64
    assert generate_rsa_key_pair()[1].startswith("-----BEGIN RSA PRIVATE KEY-----")
