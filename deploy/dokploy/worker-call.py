#!/usr/bin/env python3
"""Call the worker's signed API from a shell (smoke tests after a deploy).

    export WORKER_SHARED_SECRET=...            # the same secret as the panel
    python deploy/dokploy/worker-call.py https://worker.example.com health
    python deploy/dokploy/worker-call.py http://127.0.0.1:8092 available
    python deploy/dokploy/worker-call.py https://worker.example.com order 42

Only read-only endpoints are exposed here on purpose; orders are created by the
panel.  Needs the repository on the path (run from a checkout) and no extra
packages (urllib only).
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from rubigram_internal.signing import sign_json  # noqa: E402

ENDPOINTS = {
    "health": ("GET", "/internal/health/"),
    "available": ("GET", "/internal/accounts/available/"),
    "order": ("GET", "/internal/orders/{id}/"),
}


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[1] not in ENDPOINTS:
        print(__doc__)
        return 2
    base_url = argv[0].rstrip("/")
    method, path = ENDPOINTS[argv[1]]
    if "{id}" in path:
        if len(argv) < 3:
            print("order needs the remote order id")
            return 2
        path = path.replace("{id}", argv[2])
    secret = os.environ.get("WORKER_SHARED_SECRET", "")
    if not secret:
        print("set WORKER_SHARED_SECRET in the environment")
        return 2
    body, headers = sign_json({}, secret=secret, header_prefix=os.environ.get("WORKER_SIGNATURE_HEADER_PREFIX", "X-Balegram"))
    request = urllib.request.Request(base_url + path, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310 - operator-supplied URL
            status, payload = response.status, response.read()
    except urllib.error.HTTPError as exc:
        status, payload = exc.code, exc.read()
    except urllib.error.URLError as exc:
        print(f"connection failed: {exc.reason}")
        return 1
    try:
        print(status, json.dumps(json.loads(payload), ensure_ascii=False, indent=2))
    except json.JSONDecodeError:
        print(status, payload[:500].decode("utf-8", "replace"))
    return 0 if status < 400 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
