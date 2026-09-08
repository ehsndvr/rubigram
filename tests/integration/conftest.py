"""Live tests against the real Rubika servers.

Skipped unless ``RUBIGRAM_INTEGRATION=1``.  They only *read*: no message is
sent, nothing is joined or changed.  A user session needs a previously
logged-in session file whose name is given by ``RUBIGRAM_SESSION`` (default
``integration``); the bot tests need ``RUBIGRAM_BOT_TOKEN``.
"""

from __future__ import annotations

import os

import pytest


def pytest_collection_modifyitems(config, items):
    if os.environ.get("RUBIGRAM_INTEGRATION") == "1":
        return
    skip = pytest.mark.skip(reason="live tests run only with RUBIGRAM_INTEGRATION=1")
    for item in items:
        if "integration" in str(item.fspath):
            item.add_marker(skip)
