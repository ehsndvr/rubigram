"""The membership worker: signing, targets, the signed API, job processing and the login flow.

Django runs against a temporary SQLite file; every Rubika action and every
Celery dispatch is replaced by a recorder, so nothing leaves the process.
"""

# pyright: reportOptionalMemberAccess=false
# (tests assert on parsed payloads; a missing field is a test failure)

from __future__ import annotations

import asyncio
import json
import os
import tempfile
import time
from typing import Any

import pytest

pytest.importorskip("django")
pytest.importorskip("celery")

_TMP = tempfile.mkdtemp(prefix="rubigram-worker-")
os.environ["DJANGO_SETTINGS_MODULE"] = "membership_worker.project.settings"
os.environ["DATABASE_PATH"] = os.path.join(_TMP, "worker.sqlite3")
os.environ["WORKER_SHARED_SECRET"] = "test-shared-secret"
os.environ["WORKER_BONUS_PERCENTAGE"] = "0"
os.environ["WORKER_ACTION_DELAY_SECONDS"] = "0"
os.environ["CELERY_BROKER_URL"] = "memory://"
os.environ["ALLOWED_HOSTS"] = "testserver,localhost,127.0.0.1"
os.environ["MEMBERSHIP_WORKER_ENV_FILE"] = os.path.join(_TMP, "missing.env")

import django  # noqa: E402

django.setup()

from django.core.management import call_command  # noqa: E402
from django.test import Client as HttpClient  # noqa: E402

from membership_worker.worker import accounts, items, jobs, recovery, rubika, tasks  # noqa: E402
from membership_worker.worker.models import (  # noqa: E402
    AccountThrottle,
    MembershipJob,
    MembershipJobItem,
    WorkerAccount,
    WorkerAccountCredential,
    WorkerAutoLeaveSchedule,
    WorkerMembership,
    WorkerSignedNonce,
)
from membership_worker.worker.targets import TargetError, normalize_target_key, parse_target  # noqa: E402
from rubigram_internal.signing import SignatureError, sign_json, verify_body  # noqa: E402

call_command("migrate", verbosity=0, interactive=False)

SECRET = "test-shared-secret"
CALLBACK = "https://panel.example/internal/membership/callbacks/"


# ── helpers ────────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def clean_database():
    for model in (
        WorkerAutoLeaveSchedule,
        MembershipJobItem,
        MembershipJob,
        WorkerMembership,
        AccountThrottle,
        WorkerAccountCredential,
        WorkerAccount,
        WorkerSignedNonce,
    ):
        model.objects.all().delete()
    yield


class Recorder:
    """Stands in for the Celery task objects: records ``delay``/``apply_async`` calls."""

    def __init__(self):
        self.calls: list[tuple[str, tuple, dict]] = []

    def make(self, name: str):
        def delay(*args, **kwargs):
            self.calls.append((name, args, kwargs))

        def apply_async(args=(), kwargs=None, **options):
            self.calls.append((name, tuple(args), {**(kwargs or {}), **options}))

        return delay, apply_async

    def events(self) -> list[str]:
        return [args[1] for name, args, _ in self.calls if name == "send_callback"]

    def item_ids(self) -> list[int]:
        return [args[0] for name, args, _ in self.calls if name == "process_item"]


@pytest.fixture
def celery(monkeypatch) -> Recorder:
    recorder = Recorder()
    for task, name in (
        (tasks.process_membership_job_item_task, "process_item"),
        (tasks.send_membership_callback_task, "send_callback"),
        (tasks.retry_job_slot_fill_task, "retry_slot_fill"),
        (tasks.process_auto_leave_task, "auto_leave"),
    ):
        delay, apply_async = recorder.make(name)
        monkeypatch.setattr(task, "delay", delay)
        monkeypatch.setattr(task, "apply_async", apply_async)
    return recorder


def make_account(index: int, *, session_string: str = "rbg2.fake") -> WorkerAccount:
    account = WorkerAccount.objects.create(
        username="admin", phone=f"9891200000{index:02d}", session_name=f"rubi-admin-{index:06x}", user_guid=f"u0EXAMPLE{index:023d}"
    )
    WorkerAccountCredential.objects.create(account=account, session_string=session_string)
    AccountThrottle.objects.create(account=account)
    return account


def order(**overrides: Any) -> dict[str, Any]:
    payload = {
        "external_order_id": 1,
        "count": 2,
        "action": "join",
        "target": "@sample_channel",
        "callback_url": CALLBACK,
        "idempotency_key": "order-1",
    }
    payload.update(overrides)
    return payload


def signed(payload: dict[str, Any]) -> tuple[bytes, dict[str, str]]:
    body, headers = sign_json(payload, secret=SECRET)
    return body, {"HTTP_" + key.upper().replace("-", "_"): value for key, value in headers.items() if key != "Content-Type"}


def post(path: str, payload: dict[str, Any]):
    body, headers = signed(payload)
    return HttpClient().post(path, data=body, content_type="application/json", **headers)


def get(path: str):
    body, headers = signed({})  # the panel sends the signed "{}" body with GET requests too
    return HttpClient().generic("GET", path, data=body, content_type="application/json", **headers)


def process_all(recorder: Recorder) -> None:
    seen: set[int] = set()
    while True:
        pending = [item_id for item_id in recorder.item_ids() if item_id not in seen]
        if not pending:
            return
        for item_id in pending:
            seen.add(item_id)
            items.process_membership_job_item(item_id)


# ── signing and targets ────────────────────────────────────────────────────────


def test_signing_round_trip_rejects_tampering_and_old_timestamps():
    body, headers = sign_json({"b": 1, "a": "x"}, secret="s")
    assert body == b'{"a":"x","b":1}' and headers["Content-Type"] == "application/json"
    verified = verify_body(body, headers=headers, secret="s")
    assert verified.nonce == headers["X-Balegram-Nonce"]
    with pytest.raises(SignatureError):
        verify_body(body + b" ", headers=headers, secret="s")
    with pytest.raises(SignatureError):
        verify_body(body, headers=headers, secret="other")
    old = sign_json({}, secret="s")[1]
    old["X-Balegram-Timestamp"] = str(int(time.time()) - 1000)
    with pytest.raises(SignatureError):
        verify_body(b"{}", headers=old, secret="s")
    # the rubigram header names are accepted too
    _, rubi = sign_json({"k": 1}, secret="s", header_prefix="X-Rubigram")
    assert verify_body(b'{"k":1}', headers=rubi, secret="s").nonce == rubi["X-Rubigram-Nonce"]


def test_targets_are_classified_and_keyed_consistently():
    assert parse_target("https://rubika.ir/joinc/ABCDEF0123456789ABCDEF0123456789").kind == "channel_link"
    assert parse_target("rubika.ir/joing/ABCDEF0123456789ABCDEF0123456789").key == "joing:ABCDEF0123456789ABCDEF0123456789"
    assert normalize_target_key("@Some_Channel") == normalize_target_key("https://rubika.ir/some_channel/") == "user:some_channel"
    post_ref = parse_target("https://rubika.ir/news_channel/12345")
    assert post_ref.kind == "post" and post_ref.message_id == "12345" and post_ref.key == "post:news_channel:12345"
    assert parse_target("c0EXAMPLE00000000000000000000001").kind == "guid"
    for bad in ("", "u0EXAMPLE00000000000000000000001", "https://t.me/x", "rubika.ir/joinc/", "@a"):
        with pytest.raises(TargetError):
            parse_target(bad)


# ── the signed API ─────────────────────────────────────────────────────────────


def test_orders_api_reserves_capacity_and_reports_status(celery: Recorder):
    for index in range(2):
        make_account(index)
    assert get("/internal/health/").json()["provider"] == "rubigram-worker"
    assert get("/internal/accounts/available/").json() == {"ok": True, "available_count": 2}

    response = post("/internal/orders/", order())
    assert response.status_code == 202, response.content
    data = response.json()
    assert data["accepted_count"] == 2 and data["status"] == "inprogress"
    assert celery.events() == ["order_accepted"] and len(celery.item_ids()) == 2

    # the same idempotency key returns the same job; a new order finds no free account
    assert post("/internal/orders/", order()).json()["remote_order_id"] == data["remote_order_id"]
    refused = post("/internal/orders/", order(external_order_id=2, count=1, idempotency_key="order-2"))
    assert refused.status_code == 422 and refused.json()["code"] == "insufficient_capacity"

    status = get(f"/internal/orders/{data['remote_order_id']}/").json()
    assert status["ok"] and status["accepted_count"] == 2 and status["success_count"] == 0
    assert get("/internal/orders/999999/").status_code == 404


def test_api_rejects_unsigned_replayed_and_malformed_requests():
    assert HttpClient().get("/internal/accounts/available/").status_code == 401
    body, headers = signed({})
    first = HttpClient().generic("GET", "/internal/accounts/available/", data=body, content_type="application/json", **headers)
    replay = HttpClient().generic("GET", "/internal/accounts/available/", data=body, content_type="application/json", **headers)
    assert first.status_code == 200 and replay.status_code == 409
    bad = post("/internal/orders/", order(target="https://t.me/nope"))
    assert bad.status_code == 422 and "rubika.ir" in bad.json()["message"]
    assert post("/internal/orders/", order(count=0)).status_code == 422


# ── job processing ──────────────────────────────────────────────────────────────


def test_join_items_complete_the_job_and_schedule_auto_leave(celery: Recorder, monkeypatch):
    for index in range(2):
        make_account(index)
    calls: list[dict[str, Any]] = []

    def fake_join(**kwargs):
        calls.append(kwargs)
        after = 100 + len(calls)
        return rubika.JoinOutcome(
            "c0EXAMPLE00000000000000000000009",
            "Channel",
            "Sample",
            100,
            after,
            session_string="rbg2.refreshed" if len(calls) == 1 else None,
        )

    monkeypatch.setattr(rubika, "run_join", fake_join)
    job = jobs.create_membership_job(order(retention_days=7))
    process_all(celery)
    job.refresh_from_db()
    assert job.status == MembershipJob.Status.ACTIVE and job.success_count == 2 and job.failed_count == 0
    assert job.member_count_before == 100 and job.member_count_after == 102 and job.object_guid.startswith("c0")
    assert celery.events() == ["order_accepted", "order_active"]
    assert WorkerMembership.objects.filter(target_key="user:sample_channel", status=WorkerMembership.Status.JOINED).count() == 2
    assert WorkerAutoLeaveSchedule.objects.filter(source_job=job).count() == 2
    assert [call["probe_after"] for call in calls] == [True, False]
    assert WorkerAccountCredential.objects.get(account__session_name=calls[0]["session_name"]).session_string == "rbg2.refreshed"
    assert all(item.attempts == 1 for item in job.items.all())


def test_invalid_target_cancels_the_job_after_the_first_failure(celery: Recorder, monkeypatch):
    for index in range(3):
        make_account(index)
    monkeypatch.setattr(
        rubika,
        "run_join",
        lambda **kwargs: (_ for _ in ()).throw(
            rubika.ActionError(rubika.ActionError.INVALID_TARGET, "channel invite link is invalid or expired")
        ),
    )
    job = jobs.create_membership_job(order(count=3, target="https://rubika.ir/joinc/ABCDEF0123456789ABCDEF0123456789"))
    items.process_membership_job_item(celery.item_ids()[0])
    job.refresh_from_db()
    assert job.status == MembershipJob.Status.FAIL and "invalid_target" in job.last_error
    assert set(job.items.values_list("status", flat=True)) == {MembershipJobItem.Status.SKIPPED}
    assert celery.events() == ["order_accepted", "order_failed"]
    # later task deliveries for the cancelled items are dropped
    items.process_membership_job_item(celery.item_ids()[1])
    assert celery.events() == ["order_accepted", "order_failed"]


def test_connection_errors_keep_the_account_and_defer_the_job(celery: Recorder, monkeypatch):
    account = make_account(1)
    monkeypatch.setattr(
        rubika,
        "run_join",
        lambda **kwargs: (_ for _ in ()).throw(rubika.ActionError(rubika.ActionError.CONN_ERROR, "connection error: timed out")),
    )
    job = jobs.create_membership_job(order(count=1))
    items.process_membership_job_item(celery.item_ids()[0])
    job.refresh_from_db()
    item = job.items.get()
    assert item.status == MembershipJobItem.Status.SKIPPED and item.message.startswith("conn_error:")
    assert AccountThrottle.objects.get(account=account).next_available_at is not None
    assert job.status == MembershipJob.Status.INPROGRESS  # a slot-fill retry was scheduled instead of failing
    assert any(name == "retry_slot_fill" for name, _, _ in celery.calls)
    account.refresh_from_db()
    assert account.status == WorkerAccount.Status.ACTIVE


def test_dead_sessions_disable_the_account_and_another_one_takes_over(celery: Recorder, monkeypatch):
    dead, healthy = make_account(1), make_account(2)

    def fake_join(**kwargs):
        if kwargs["session_name"] == dead.session_name:
            raise rubika.ActionError(rubika.ActionError.SESSION_DEAD, "session rejected: INVALID_AUTH")
        return rubika.JoinOutcome("c0EXAMPLE00000000000000000000009", "Channel", "Sample", None, None)

    monkeypatch.setattr(rubika, "run_join", fake_join)
    job = jobs.create_membership_job(order(count=1))
    process_all(celery)
    job.refresh_from_db()
    dead.refresh_from_db()
    assert job.status == MembershipJob.Status.COMPLETED and job.success_count == 1
    assert dead.status == WorkerAccount.Status.DISABLED and "INVALID_AUTH" in dead.last_error
    assert WorkerMembership.objects.get(account=healthy).status == WorkerMembership.Status.JOINED
    assert celery.events()[-1] == "order_completed"


def test_leave_uses_joined_accounts_and_view_cycles_the_pool(celery: Recorder, monkeypatch):
    first, second = make_account(1), make_account(2)
    jobs.mark_membership(first, target_key="user:sample_channel", target="@sample_channel", joined=True, title="Sample")
    left: list[str] = []
    monkeypatch.setattr(
        rubika,
        "run_leave",
        lambda **kwargs: (
            left.append(kwargs["session_name"]),
            rubika.LeaveOutcome("c0EXAMPLE00000000000000000000009", "Channel", "Sample"),
        )[1],
    )
    leave_job = jobs.create_membership_job(order(action="leave", count=2, idempotency_key="leave-1"))
    assert leave_job.accepted_count == 1 and leave_job.skipped_count == 1
    process_all(celery)
    leave_job.refresh_from_db()
    assert left == [first.session_name] and leave_job.status == MembershipJob.Status.PARTIAL
    assert WorkerMembership.objects.get(account=first).status == WorkerMembership.Status.LEFT

    viewed: list[str] = []
    monkeypatch.setattr(
        rubika,
        "run_view",
        lambda **kwargs: (viewed.append(kwargs["session_name"]), rubika.ViewOutcome("c0EXAMPLE00000000000000000000009", ["1", "2", "3"]))[
            1
        ],
    )
    view_job = jobs.create_membership_job(order(action="view", count=3, service_id="5", idempotency_key="view-1"))
    assert view_job.accepted_count == 3
    process_all(celery)
    view_job.refresh_from_db()
    assert view_job.status == MembershipJob.Status.COMPLETED and sorted(viewed) == sorted(
        [first.session_name, second.session_name, first.session_name]
    )


def test_stale_running_items_are_recovered(celery: Recorder):
    make_account(1)
    job = jobs.create_membership_job(order(count=1))
    item = job.items.get()
    from datetime import timedelta

    from django.utils import timezone

    MembershipJobItem.objects.filter(id=item.id).update(
        status=MembershipJobItem.Status.RUNNING, started_at=timezone.now() - timedelta(minutes=10)
    )
    assert recovery.recover_stale_running_items() == 1
    item.refresh_from_db()
    assert item.status == MembershipJobItem.Status.PENDING and celery.item_ids()[-1] == item.id


# ── login flow ────────────────────────────────────────────────────────────────────


class FakeStorage:
    def __init__(self):
        self._auth = None
        self._guid = None

    async def auth(self):
        return self._auth

    async def user_guid(self):
        return self._guid


class FakeSentCode:
    def __init__(self, status="OK", phone_code_hash="hash-1", send_type="SMS"):
        self.status, self.phone_code_hash, self.send_type = status, phone_code_hash, send_type
        self.code_digits_count = 5


class FakeUser:
    user_guid = "u0EXAMPLE00000000000000000000001"
    first_name, last_name = "Sample", "User"


class FakeMe:
    user = FakeUser()


class FakeLoginClient:
    """Mimics the rubigram Client for the login flow; one instance per session name."""

    instances: dict[str, FakeLoginClient] = {}

    def __init__(self, session_name: str, session_string: str | None = None, **kwargs):
        self.session_name = session_name
        self.restored_from = session_string
        self.storage = FakeStorage()
        self.codes: list[str] = []
        self.stopped = False
        FakeLoginClient.instances[session_name] = self

    async def start(self):
        return self

    async def stop(self):
        self.stopped = True

    async def send_code(self, phone, **kwargs):
        return FakeSentCode()

    async def sign_in(self, phone, phone_code_hash, code):
        from rubigram import errors

        self.codes.append(code)
        if code != "12345":
            raise errors.CodeIsInvalid("ERROR_GENERIC", "INVALID_INPUT", {}, method="signIn")
        self.storage._auth = "a" * 32
        self.storage._guid = FakeUser.user_guid

    async def get_me(self):
        return FakeMe()

    async def export_session_string(self):
        return "rbg2.pending" if self.storage._auth is None else "rbg2.logged-in"


@pytest.fixture
def fake_login(monkeypatch):
    FakeLoginClient.instances.clear()
    monkeypatch.setattr(
        accounts,
        "build_client",
        lambda session_name, session_string=None, **kwargs: FakeLoginClient(session_name, session_string, **kwargs),
    )
    accounts._PENDING.clear()
    accounts._VERIFY_LOCKS.clear()
    yield
    accounts._PENDING.clear()


def test_login_flow_stores_the_session_string(fake_login):
    async def flow():
        started = await accounts.start_phone_login(username="Admin", phone="0912 000 0000")
        assert started.phone == "989120000000" and started.transaction_hash == "hash-1"
        assert started.login_state["login_state"] == "rbg2.pending" and started.session_name.startswith("rubi-admin-")
        with pytest.raises(accounts.WorkerServiceError):
            await accounts.verify_phone_code(
                username="",
                phone="",
                transaction_hash="hash-1",
                code="۹۹۹۹۹",
                session_name=started.session_name,
                login_state=started.login_state,
            )
        outcome = await accounts.verify_phone_code(
            username="",
            phone="",
            transaction_hash="hash-1",
            code="۱۲۳۴۵",
            session_name=started.session_name,
            login_state=started.login_state,
        )
        return started, outcome

    started, outcome = asyncio.run(flow())
    client = FakeLoginClient.instances[started.session_name]
    assert client.codes == ["99999", "12345"] and client.stopped
    account = WorkerAccount.objects.get(id=int(outcome.remote_account_id))
    assert account.phone == "989120000000" and account.user_guid == FakeUser.user_guid and account.display_name == "Sample User"
    assert account.credential.session_string == "rbg2.logged-in"
    assert outcome.auth_id == FakeUser.user_guid and outcome.user_id is None and not outcome.requires_signup
    assert started.session_name not in accounts._PENDING


def test_login_can_be_finished_by_another_process_from_the_login_state(fake_login):
    async def flow():
        started = await accounts.start_phone_login(username="admin", phone="989120000001")
        accounts._PENDING.clear()  # simulate a different worker process
        return started, await accounts.verify_phone_code(
            username="admin",
            phone="",
            transaction_hash="hash-1",
            code="12345",
            session_name=started.session_name,
            login_state=started.login_state,
        )

    started, outcome = asyncio.run(flow())
    restored = FakeLoginClient.instances[started.session_name]
    assert restored.restored_from == "rbg2.pending" and outcome.remote_account_id


def test_login_views_map_the_panel_contract(fake_login):
    started = post("/internal/accounts/start-login/", {"username": "admin", "phone": "989120000002"}).json()
    assert started["ok"] and started["transaction_hash"] == "hash-1" and started["grpc_cookies"]["login_state"] == "rbg2.pending"
    wrong = post(
        "/internal/accounts/verify-code/",
        {
            "session_name": started["session_name"],
            "transaction_hash": "hash-1",
            "code": "00000",
            "grpc_cookies": started["grpc_cookies"],
            "device_hash": started["device_hash"],
        },
    )
    assert wrong.status_code == 422 and "کد" in wrong.json()["message"]
    verified = post(
        "/internal/accounts/verify-code/",
        {
            "session_name": started["session_name"],
            "transaction_hash": "hash-1",
            "code": "12345",
            "grpc_cookies": started["grpc_cookies"],
            "device_hash": started["device_hash"],
        },
    )
    assert verified.status_code == 200, verified.content
    body = verified.json()
    assert body["remote_account_id"] and body["auth_id"] == FakeUser.user_guid and body["requires_signup"] is False
    assert WorkerAccount.objects.filter(phone="989120000002").exists()
    assert post("/internal/accounts/cancel-login/", {"session_name": started["session_name"]}).json() == {"ok": True}


def test_callback_payload_and_bonus(monkeypatch):
    from django.conf import settings

    monkeypatch.setattr(settings, "WORKER_BONUS_PERCENTAGE", 3.0)
    assert jobs.apply_bonus(500) == 515 and jobs.apply_bonus(1) == 2
    monkeypatch.setattr(settings, "WORKER_BONUS_PERCENTAGE", 0.0)
    make_account(1)
    job = MembershipJob.objects.create(
        external_order_id=7,
        idempotency_key="cb",
        action="join",
        target="@x",
        target_key="user:x",
        requested_count=1,
        total_count=1,
        accepted_count=1,
        callback_url=CALLBACK,
    )
    payload = jobs.build_callback_payload(job, "order_completed")
    assert (
        payload["event_id"] == f"order_completed-{job.id}-job"
        and payload["provider"] == "rubigram-worker"
        and payload["external_order_id"] == 7
    )
    assert json.loads(json.dumps(payload))["remote_order_id"] == str(job.id)
