from __future__ import annotations

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "membership_worker.project.settings")

app = Celery("membership_worker")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks(["membership_worker.worker"])
