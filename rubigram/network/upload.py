"""Chunked file upload to the ``upload_url`` returned by ``requestSendFile``.

Mirrors the web client: 131072-byte parts, headers ``auth``, ``file-id``,
``access-hash-send``, ``part-number``, ``total-part``, ``chunk-size``; a part is
accepted when the JSON answer has ``status_det == "OK"``; network errors and
5xx answers are retried with the shared ladder.  Files are streamed from disk.
"""

from __future__ import annotations

import inspect
import io
import logging
import math
from pathlib import Path
from typing import Any, BinaryIO, Callable, Optional, Union

import httpx

from rubigram.errors import NetworkError, RequestTimeout, TransportError, map_rpc_error
from rubigram.network.headers import build_upload_headers
from rubigram.network.retry import DEFAULT_RETRY_POLICY, RetryPolicy, run_with_retries

log = logging.getLogger(__name__)

ProgressCallback = Callable[..., Any]


async def report_progress(progress: Optional[ProgressCallback], current: int, total: int, progress_args: tuple[Any, ...]) -> None:
    """Call ``progress(current, total, *progress_args)``; awaits coroutine callbacks."""
    if progress is None:
        return
    result = progress(current, total, *progress_args)
    if inspect.isawaitable(result):
        await result


class _Retry(Exception):
    def __init__(self, error: Exception):
        super().__init__(str(error))
        self.error = error


class UploadTransport:
    """Uploads a file in parts and returns the final ``access_hash_rec``."""

    DEFAULT_TIMEOUT = 30.0
    DEFAULT_CHUNK_SIZE = 131072

    def __init__(
        self,
        timeout: float = DEFAULT_TIMEOUT,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        *,
        proxy: Optional[str] = None,
        retry_policy: RetryPolicy = DEFAULT_RETRY_POLICY,
        user_agent: Optional[str] = None,
    ):
        self._timeout = timeout
        self._chunk_size = max(1, int(chunk_size))
        self._proxy = proxy
        self._retry_policy = retry_policy.with_overrides(timeout=timeout)
        self._user_agent = user_agent
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._timeout, headers=build_upload_headers(self._user_agent), proxy=self._proxy)
        return self._client

    def use_client(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def upload_file(
        self,
        *,
        auth: str,
        descriptor: Any,
        path: Union[str, Path, None] = None,
        data: Optional[bytes] = None,
        progress: Optional[ProgressCallback] = None,
        progress_args: tuple[Any, ...] = (),
    ) -> Any:
        """Upload ``path`` (or ``data``) using an ``UploadDescriptor``.

        Returns a copy of the descriptor with ``access_hash_rec`` filled in.
        """
        if not auth:
            raise TransportError("Uploading a file requires auth")
        upload_url = getattr(descriptor, "upload_url", None)
        file_id = getattr(descriptor, "id", None)
        access_hash_send = getattr(descriptor, "access_hash_send", None)
        if not upload_url:
            raise TransportError("Upload descriptor does not include upload_url")
        if file_id is None:
            raise TransportError("Upload descriptor does not include file id")
        if not access_hash_send:
            raise TransportError("Upload descriptor does not include access_hash_send")

        if data is not None:
            stream: BinaryIO = io.BytesIO(data)
            total_size = len(data)
        elif path is not None:
            file_path = Path(path)
            total_size = file_path.stat().st_size
            stream = file_path.open("rb")
        else:
            raise TransportError("upload_file needs a path or data")

        total_parts = max(1, math.ceil(total_size / self._chunk_size))
        access_hash_rec = getattr(descriptor, "access_hash_rec", None)
        uploaded = 0
        try:
            for index in range(total_parts):
                chunk = stream.read(self._chunk_size)
                headers = {
                    "auth": auth,
                    "file-id": str(file_id),
                    "access-hash-send": str(access_hash_send),
                    "part-number": str(index + 1),
                    "total-part": str(total_parts),
                    "chunk-size": str(len(chunk)),
                }
                payload = await self._send_part(str(upload_url), chunk, headers)
                data_payload = payload.get("data") or {}
                if isinstance(data_payload, dict) and data_payload.get("access_hash_rec"):
                    access_hash_rec = data_payload["access_hash_rec"]
                uploaded += len(chunk)
                await report_progress(progress, uploaded, total_size, progress_args)
        finally:
            stream.close()

        return descriptor.__class__(
            client=getattr(descriptor, "_client", None),
            id=file_id,
            dc_id=getattr(descriptor, "dc_id", None),
            access_hash_send=access_hash_send,
            access_hash_rec=access_hash_rec,
            upload_url=upload_url,
        )

    async def _send_part(self, url: str, chunk: bytes, headers: dict[str, str]) -> dict[str, Any]:
        client = await self._get_client()
        policy = self._retry_policy

        async def attempt(index: int) -> dict[str, Any]:
            try:
                response = await client.post(url, content=chunk, headers=headers, timeout=policy.timeout)
            except httpx.TimeoutException as exc:
                raise _Retry(RequestTimeout(f"Upload part to {url} timed out", exc)) from exc
            except httpx.HTTPError as exc:
                raise _Retry(NetworkError(f"Upload to {url} failed: {exc}", exc)) from exc
            if response.status_code >= 500:
                raise _Retry(TransportError(f"Upload failed with HTTP {response.status_code}: {response.text[:200]}"))
            if response.status_code >= 400:
                raise TransportError(f"Upload failed with HTTP {response.status_code}: {response.text[:200]}")
            try:
                payload = response.json()
            except ValueError as exc:
                raise _Retry(TransportError(f"Failed to parse upload response: {exc}")) from exc
            if not isinstance(payload, dict):
                raise TransportError("Unexpected upload response payload")
            status = payload.get("status")
            status_det = payload.get("status_det")
            if status and status != "OK":
                raise map_rpc_error(str(status), status_det, payload, method="uploadFile")
            if status_det and status_det != "OK":
                raise _Retry(TransportError(f"Upload part rejected: {status_det}"))
            return payload

        try:
            return await run_with_retries(policy, attempt, retryable=lambda exc: isinstance(exc, _Retry), label="upload part")
        except _Retry as failure:
            raise failure.error from failure.error

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None


__all__ = ["UploadTransport", "report_progress", "ProgressCallback"]
