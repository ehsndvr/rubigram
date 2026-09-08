"""Django settings of the rubigram membership worker.

Values come from the process environment first, then from ``membership_worker/.env``
(see ``.env.example``).  Nothing here talks to Rubika; the worker settings are
read by ``membership_worker.worker``.
"""

from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BASE_DIR.parent


def _parse_dotenv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        line = line.removeprefix("export ").strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        values[key.strip()] = value
    return values


_DOTENV = _parse_dotenv(Path(os.environ.get("MEMBERSHIP_WORKER_ENV_FILE", BASE_DIR / ".env")))


def env(name: str, default: str = "") -> str:
    """Environment variable, else ``.env`` value, else ``default``."""
    return os.environ.get(name, _DOTENV.get(name, default))


def env_bool(name: str, default: bool = False) -> bool:
    return env(name, "true" if default else "false").strip().lower() in {"1", "true", "yes", "on"}


def env_float(name: str, default: float) -> float:
    try:
        return float(env(name, str(default)))
    except ValueError:
        return default


def env_int(name: str, default: int) -> int:
    try:
        return int(env(name, str(default)))
    except ValueError:
        return default


def _resolve_path(raw_value: str, *, base_dir: Path) -> Path:
    candidate = Path(raw_value)
    if not candidate.is_absolute():
        candidate = base_dir / candidate
    return candidate.resolve()


SECRET_KEY = env("SECRET_KEY", "unsafe-membership-worker-dev-secret-key")
DEBUG = env_bool("DEBUG", False)
ALLOWED_HOSTS = [host.strip() for host in env("ALLOWED_HOSTS", "127.0.0.1,localhost").split(",") if host.strip()]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "membership_worker.worker",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "membership_worker.project.urls"
WSGI_APPLICATION = "membership_worker.project.wsgi.application"
ASGI_APPLICATION = "membership_worker.project.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": env("DATABASE_ENGINE", "django.db.backends.sqlite3"),
        "NAME": env("DATABASE_NAME") or str(_resolve_path(env("DATABASE_PATH", "./data/membership_worker.sqlite3"), base_dir=BASE_DIR)),
        "USER": env("DATABASE_USER"),
        "PASSWORD": env("DATABASE_PASSWORD"),
        "HOST": env("DATABASE_HOST"),
        "PORT": env("DATABASE_PORT"),
    }
}
if DATABASES["default"]["ENGINE"] == "django.db.backends.sqlite3":
    Path(str(DATABASES["default"]["NAME"])).parent.mkdir(parents=True, exist_ok=True)

LANGUAGE_CODE = "fa-ir"
TIME_ZONE = "Asia/Tehran"
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ── Worker ──────────────────────────────────────────────────────────────────────
WORKER_PROVIDER = env("WORKER_PROVIDER", "rubigram-worker")
WORKER_SHARED_SECRET = env("WORKER_SHARED_SECRET")
WORKER_SIGNATURE_HEADER_PREFIX = env("WORKER_SIGNATURE_HEADER_PREFIX", "X-Balegram")  # what the panel expects on callbacks
WORKER_SIGNATURE_MAX_AGE_SECONDS = env_int("WORKER_SIGNATURE_MAX_AGE_SECONDS", 300)
WORKER_CALLBACK_TIMEOUT_SECONDS = env_float("WORKER_CALLBACK_TIMEOUT_SECONDS", 10.0)
WORKER_ACTION_DELAY_SECONDS = env_float("WORKER_ACTION_DELAY_SECONDS", 2.0)  # minimum gap between two actions of one account
WORKER_ACTION_TIMEOUT_SECONDS = env_float("WORKER_ACTION_TIMEOUT_SECONDS", 20.0)  # per Rubika request
WORKER_LOGIN_TIMEOUT_SECONDS = env_float("WORKER_LOGIN_TIMEOUT_SECONDS", 60.0)
WORKER_BONUS_PERCENTAGE = env_float("WORKER_BONUS_PERCENTAGE", 3.0)  # extra members on join orders
WORKER_JOB_MAX_WAIT_HOURS = env_int("WORKER_JOB_MAX_WAIT_HOURS", 6)
WORKER_USER_AGENT = env("WORKER_USER_AGENT")  # empty → rubigram's Chrome profile
WORKER_DEVICE_HASH = env("WORKER_DEVICE_HASH")  # empty → derived from the user agent like the web client
WORKER_SYSTEM_VERSION = env("WORKER_SYSTEM_VERSION", "Windows 10")
WORKER_DEVICE_MODEL = env("WORKER_DEVICE_MODEL", "Chrome 145")
WORKER_PROXY = env("WORKER_PROXY")  # optional http(s)://, socks5:// proxy for every Rubika call
# Where "which address did Rubika see?" is asked. Empty turns the check off,
# which is the right answer for a deployment with no outbound to it: the
# measurement is evidence, never a precondition, and a login must not wait on
# a service that cannot answer.
WORKER_EGRESS_ECHO_URL = env("WORKER_EGRESS_ECHO_URL", "https://api.ipify.org")
WORKER_EGRESS_TIMEOUT_SECONDS = env_float("WORKER_EGRESS_TIMEOUT_SECONDS", 8.0)
WORKER_VIEW_POST_COUNTS = {"4": 1, "5": 5, "6": 10, "7": 20, "8": 30}  # service_id → posts viewed per account
WORKER_THROTTLE_CONN_ERROR_SECONDS = env_int("WORKER_THROTTLE_CONN_ERROR_SECONDS", 60)
WORKER_THROTTLE_TOO_REQUESTS_SECONDS = env_int("WORKER_THROTTLE_TOO_REQUESTS_SECONDS", 3600)

# ── Celery ──────────────────────────────────────────────────────────────────────
CELERY_BROKER_URL = env("CELERY_BROKER_URL", "redis://127.0.0.1:6379/1")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", CELERY_BROKER_URL)
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = USE_TZ
CELERY_TASK_IGNORE_RESULT = True
CELERY_TASK_ALWAYS_EAGER = env_bool("CELERY_TASK_ALWAYS_EAGER", False)  # tests and single-process setups
CELERY_TASK_ROUTES = {
    "membership_worker.process_membership_job_item": {"queue": "membership"},
    "membership_worker.process_auto_leave": {"queue": "membership"},
    "membership_worker.retry_job_slot_fill": {"queue": "membership"},
    "membership_worker.send_callback": {"queue": "callbacks"},
    "membership_worker.enqueue_due_auto_leaves": {"queue": "default"},
    "membership_worker.recover_stale_running_items": {"queue": "default"},
    "membership_worker.recover_stale_pending_items": {"queue": "default"},
    "membership_worker.recover_stale_inprogress_jobs": {"queue": "default"},
}
CELERY_WORKER_CONCURRENCY = env_int("CELERY_WORKER_CONCURRENCY", 0) or None
CELERY_WORKER_PREFETCH_MULTIPLIER = 1  # each task holds a Rubika session; never prefetch
CELERY_TASK_ACKS_LATE = True  # a crashed worker re-queues its task
CELERY_WORKER_MAX_TASKS_PER_CHILD = env_int("CELERY_WORKER_MAX_TASKS_PER_CHILD", 0) or None
CELERY_BEAT_SCHEDULE = {
    "enqueue-due-auto-leaves": {
        "task": "membership_worker.enqueue_due_auto_leaves",
        "schedule": env_float("AUTO_LEAVE_SCAN_INTERVAL_SECONDS", 60.0),
    },
    "recover-stale-running-items": {"task": "membership_worker.recover_stale_running_items", "schedule": 30.0},
    "recover-stale-pending-items": {"task": "membership_worker.recover_stale_pending_items", "schedule": 60.0},
    "recover-stale-inprogress-jobs": {"task": "membership_worker.recover_stale_inprogress_jobs", "schedule": 30.0},
    # Read-only, and paced by how stale an answer may get rather than by how
    # fast it could run: every sweep is one live connection per account.
    "scan-account-health": {
        "task": "membership_worker.scan_account_health",
        "schedule": env_float("HEALTH_SCAN_INTERVAL_SECONDS", 900.0),
        "kwargs": {"limit": env_int("HEALTH_SCAN_BATCH", 100)},
    },
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"verbose": {"format": "[{asctime}] [{levelname}] {name}: {message}", "style": "{"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "verbose"}},
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "membership_worker": {"handlers": ["console"], "level": env("WORKER_LOG_LEVEL", "INFO"), "propagate": False},
        "rubigram": {"handlers": ["console"], "level": env("RUBIGRAM_LOG_LEVEL", "WARNING"), "propagate": False},
    },
}
