"""Database models of the membership worker.

An *account* is a logged-in Rubika session owned by the worker.  A *job* is one
panel order (join / leave / view a target with N accounts); every account
assigned to a job is an *item*.  *Memberships* remember which account joined
which target, *throttles* pace the accounts, *auto-leave schedules* undo joins
after the retention period and *nonces* refuse replayed requests.
"""

from __future__ import annotations

from django.db import models


class WorkerAccount(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        DISABLED = "disabled", "Disabled"
        ERROR = "error", "Error"

    username = models.CharField(max_length=128)  # panel user who added the number
    phone = models.CharField(max_length=32)
    session_name = models.CharField(max_length=255, unique=True)
    user_guid = models.CharField(max_length=64, blank=True)
    display_name = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    last_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["phone"]),
        ]

    def __str__(self) -> str:
        return f"{self.phone} - {self.session_name}"


class WorkerAccountCredential(models.Model):
    """The rubigram session string of an account (the only secret in the database)."""

    account = models.OneToOneField(WorkerAccount, on_delete=models.CASCADE, related_name="credential")
    session_string = models.TextField()
    updated_at = models.DateTimeField(auto_now=True)


class AccountThrottle(models.Model):
    account = models.OneToOneField(WorkerAccount, on_delete=models.CASCADE, related_name="throttle")
    next_available_at = models.DateTimeField(null=True, blank=True)
    locked_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)


class WorkerMembership(models.Model):
    class Status(models.TextChoices):
        JOINED = "joined", "Joined"
        LEFT = "left", "Left"

    account = models.ForeignKey(WorkerAccount, on_delete=models.CASCADE, related_name="memberships")
    target_key = models.CharField(max_length=512)
    target_display = models.CharField(max_length=512)
    object_guid = models.CharField(max_length=64, blank=True)
    object_type = models.CharField(max_length=16, blank=True)  # Channel / Group
    group_title = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.LEFT)
    joined_at = models.DateTimeField(null=True, blank=True)
    left_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["account", "target_key"], name="uniq_worker_account_target")]
        indexes = [models.Index(fields=["target_key", "status"])]


class MembershipJob(models.Model):
    class Action(models.TextChoices):
        JOIN = "join", "Join"
        LEAVE = "leave", "Leave"
        VIEW = "view", "View"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        INPROGRESS = "inprogress", "In progress"
        ACTIVE = "active", "Active"  # joined and waiting for the retention period to end
        COMPLETED = "completed", "Completed"
        PARTIAL = "partial", "Partial"
        FAIL = "fail", "Fail"
        ERROR = "error", "Error"

    external_order_id = models.BigIntegerField(db_index=True)
    idempotency_key = models.CharField(max_length=128, unique=True)
    action = models.CharField(max_length=16, choices=Action.choices)
    target = models.CharField(max_length=512)
    target_key = models.CharField(max_length=512)
    object_guid = models.CharField(max_length=64, blank=True)
    requested_count = models.PositiveIntegerField()
    total_count = models.PositiveIntegerField(default=0)
    accepted_count = models.PositiveIntegerField(default=0)
    success_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)
    skipped_count = models.PositiveIntegerField(default=0)
    member_count_before = models.PositiveIntegerField(null=True, blank=True)
    member_count_after = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    service_id = models.CharField(max_length=16, blank=True)
    retention_days = models.PositiveIntegerField(null=True, blank=True)
    callback_url = models.URLField(max_length=1024)
    last_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["target_key", "status"]),
        ]

    @property
    def processed_count(self) -> int:
        return self.success_count + self.failed_count + self.skipped_count


class MembershipJobItem(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"
        SKIPPED = "skipped", "Skipped"

    job = models.ForeignKey(MembershipJob, on_delete=models.CASCADE, related_name="items")
    account = models.ForeignKey(WorkerAccount, on_delete=models.CASCADE, related_name="job_items")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    group_title = models.CharField(max_length=255, blank=True)
    message = models.TextField(blank=True)
    attempts = models.PositiveIntegerField(default=0)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
        indexes = [
            models.Index(fields=["job", "status"]),
            models.Index(fields=["account", "status"]),
        ]


class WorkerAutoLeaveSchedule(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAIL = "fail", "Fail"

    source_job = models.ForeignKey(MembershipJob, on_delete=models.CASCADE, related_name="auto_leave_schedules")
    source_item = models.OneToOneField(MembershipJobItem, on_delete=models.CASCADE, related_name="auto_leave_schedule")
    account = models.ForeignKey(WorkerAccount, on_delete=models.CASCADE, related_name="auto_leave_schedules")
    target = models.CharField(max_length=512)
    target_key = models.CharField(max_length=512)
    due_at = models.DateTimeField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    attempts = models.PositiveIntegerField(default=0)
    last_error = models.TextField(blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["due_at", "id"]
        indexes = [models.Index(fields=["status", "due_at"])]


class WorkerSignedNonce(models.Model):
    nonce = models.CharField(max_length=128, unique=True)
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-received_at"]
