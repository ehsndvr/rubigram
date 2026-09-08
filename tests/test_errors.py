import importlib
import warnings

import pytest

from rubigram import errors
from rubigram.errors import (
    AuthKeyInvalid,
    CodeIsInvalid,
    FloodWaitError,
    InvalidAuth,
    InvalidInput,
    NotRegistered,
    RegisterDeviceRequired,
    RpcError,
    RubigramError,
    RubikaError,
    TooRequests,
    extract_show_message,
    map_rpc_error,
    parse_retry_after,
    raise_for_status,
)


@pytest.mark.parametrize(
    ("status_det", "expected"),
    [
        ("INVALID_INPUT", errors.InvalidInput),
        ("NOT_SUPPORTED_API_VERSION", errors.NotSupportedApiVersion),
        ("SERVER_ERROR", errors.ServerError),
        ("INVALID_METHOD", errors.InvalidMethod),
        ("CODE_IS_USED", errors.CodeIsUsed),
        ("CODE_IS_EXPIRED", errors.CodeIsExpired),
        ("INVALID_AUTH", errors.InvalidAuth),
        ("NOT_REGISTERED", errors.NotRegistered),
        ("TOO_REQUESTS", errors.TooRequests),
        ("USERNAME_EXIST", errors.UsernameExists),
        ("UNDELIVERABLE", errors.Undeliverable),
    ],
)
def test_every_web_client_status_det_maps_to_a_class(status_det, expected):
    error = map_rpc_error("ERROR_GENERIC", status_det, {"status": "ERROR_GENERIC", "status_det": status_det})
    assert type(error) is expected
    assert error.status == "ERROR_GENERIC"
    assert error.status_det == status_det
    assert isinstance(error, RpcError)
    assert isinstance(error, RubigramError)


def test_unknown_status_det_falls_back_to_rpc_error():
    error = map_rpc_error("ERROR_GENERIC", "SOMETHING_NEW", {})
    assert type(error) is RpcError
    assert "SOMETHING_NEW" in str(error)


def test_aliases_keep_old_names_working():
    assert AuthKeyInvalid is InvalidAuth
    assert RegisterDeviceRequired is NotRegistered
    assert FloodWaitError is TooRequests
    assert RubikaError is RubigramError
    assert errors.PhoneCodeInvalid is CodeIsInvalid


def test_sign_in_invalid_input_becomes_code_is_invalid_but_stays_invalid_input():
    error = map_rpc_error("ERROR_GENERIC", "INVALID_INPUT", {}, method="signIn")
    assert isinstance(error, CodeIsInvalid)
    assert isinstance(error, InvalidInput)
    assert error.method == "signIn"


def test_client_show_message_is_extracted_and_used_in_str():
    payload = {
        "status": "ERROR_GENERIC",
        "status_det": "INVALID_AUTH",
        "client_show_message": {"link": {"alert_data": {"message": "نمونه پیام سرور"}}},
    }
    error = map_rpc_error(payload["status"], payload["status_det"], payload, method="removeGroup")
    assert error.client_show_message == "نمونه پیام سرور"
    assert error.raw is payload
    assert "نمونه پیام سرور" in str(error)
    assert extract_show_message({"client_show_message": {"text": "hello"}}) == "hello"
    assert extract_show_message({"client_show_message": "not a dict"}) is None
    assert extract_show_message(None) is None


def test_invalid_auth_reports_dead_session_only_for_error_action():
    dead = map_rpc_error("ERROR_ACTION", "INVALID_AUTH", {})
    denied = map_rpc_error("ERROR_GENERIC", "INVALID_AUTH", {})
    assert dead.is_session_dead is True
    assert denied.is_session_dead is False


def test_too_requests_parses_retry_after_from_server_text():
    payload = {"client_show_message": {"link": {"alert_data": {"message": "لطفا ۳۰ ثانیه صبر کنید"}}}}
    error = map_rpc_error("ERROR_GENERIC", "TOO_REQUESTS", payload)
    assert isinstance(error, TooRequests)
    assert error.retry_after == 30.0
    assert error.wait_time == 30.0
    assert parse_retry_after("try again in 2 minutes") == 120.0
    assert parse_retry_after("no number here") is None
    flood = map_rpc_error("ERROR_GENERIC", "TOO_REQUESTS", {})
    assert isinstance(flood, TooRequests) and flood.retry_after is None


def test_legacy_status_only_payloads_still_map():
    error = map_rpc_error("TOO_REQUESTS", None, {"status": "TOO_REQUESTS"})
    assert isinstance(error, TooRequests)


def test_raise_for_status_only_raises_on_non_ok():
    raise_for_status({"status": "OK", "status_det": "OK"})
    raise_for_status({"data": {}})
    with pytest.raises(NotRegistered):
        raise_for_status({"status": "ERROR_GENERIC", "status_det": "NOT_REGISTERED"}, method="getUserInfo")


def test_exceptions_package_is_a_deprecated_alias():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        module = importlib.import_module("rubigram.exceptions")
        importlib.reload(module)
    assert any(issubclass(w.category, DeprecationWarning) for w in caught)
    assert module.InvalidInput is InvalidInput
    assert module.map_rpc_error is map_rpc_error
