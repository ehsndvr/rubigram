"""Chunked downloads from a DC storage (``GetFile.ashx``) and direct URL downloads.

The web client posts an empty ``text/plain`` body to the ``storages[dc_id]``
URL from ``getDCs`` with the headers ``auth``, ``file-id``,
``access-hash-rec``, ``start-index``, ``last-index`` (inclusive byte range)
and reads the total size from the ``total_length`` response header.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional, Union

import httpx

from rubigram.errors import LoginRequired, NetworkError, RequestTimeout, TransportError
from rubigram.network.headers import build_download_headers
from rubigram.network.retry import DEFAULT_RETRY_POLICY, RetryPolicy, run_with_retries
from rubigram.network.upload import ProgressCallback, report_progress

log = logging.getLogger(__name__)


def fallback_storage_url(dc_id: Union[str, int]) -> str:
    """Best-effort ``GetFile.ashx`` URL when the ``storages`` map is unavailable.

    The real hosts come from ``getDCs`` (for example dc ``2`` is
    ``https://messanger2.iranlms.ir/GetFile.ashx``); this pattern is only a
    last resort and is logged when used.
    """
    return f"https://messanger{dc_id}.iranlms.ir/GetFile.ashx"


class _Retry(Exception):
    def __init__(self, error: Exception):
        super().__init__(str(error))
        self.error = error


class DownloadTransport:
    DEFAULT_TIMEOUT = 30.0
    DEFAULT_CHUNK_SIZE = 262144

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
            self._client = httpx.AsyncClient(timeout=self._timeout, headers=build_download_headers(self._user_agent), proxy=self._proxy)
        return self._client

    def use_client(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def download_file(
        self,
        *,
        auth: str,
        file_id: Union[str, int],
        access_hash_rec: str,
        url: Optional[str] = None,
        dc_id: Union[str, int, None] = None,
        file_size: Optional[int] = None,
        path: Union[str, Path, None] = None,
        in_memory: bool = False,
        progress: Optional[ProgressCallback] = None,
        progress_args: tuple[Any, ...] = (),
    ) -> Union[bytes, Path]:
        """Download a Rubika file by ``file_id``/``access_hash_rec``.

        ``url`` must be the DC's ``GetFile.ashx`` endpoint (``DcRepository.storage_url``);
        when only ``dc_id`` is given a fallback host pattern is used.
        """
        if not auth:
            raise LoginRequired("Downloading files requires an authenticated session")
        if not file_id:
            raise TransportError("Downloading a file requires file_id")
        if not access_hash_rec:
            raise TransportError("Downloading a file requires access_hash_rec")
        if not url:
            if dc_id in (None, ""):
                raise TransportError("Downloading a file requires the storage URL or dc_id")
            url = fallback_storage_url(dc_id)
            log.warning("No storage URL for dc %s; falling back to %s", dc_id, url)

        output_path: Optional[Path] = None
        file_handle = None
        chunks: list[bytes] = []
        downloaded = 0
        total: Optional[int] = int(file_size) if file_size else None
        start = 0
        try:
            if not in_memory:
                if path is None:
                    raise TransportError("Downloading to disk requires a destination path")
                output_path = Path(path)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                file_handle = output_path.open("wb")
            while True:
                end = start + self._chunk_size - 1
                if total is not None:
                    end = min(end, total - 1)
                    if start > total - 1:
                        break
                headers = {
                    "auth": auth,
                    "file-id": str(file_id),
                    "access-hash-rec": str(access_hash_rec),
                    "start-index": str(start),
                    "last-index": str(end),
                }
                chunk, total_length = await self._fetch_chunk(url, headers)
                if total is None and total_length:
                    total = total_length
                if not chunk:
                    break
                if in_memory:
                    chunks.append(chunk)
                else:
                    assert file_handle is not None
                    file_handle.write(chunk)
                downloaded += len(chunk)
                await report_progress(progress, downloaded, total or downloaded, progress_args)
                if total is not None and downloaded >= total:
                    break
                if len(chunk) < end - start + 1:
                    break
                start = end + 1
        finally:
            if file_handle is not None:
                file_handle.close()
        if in_memory:
            return b"".join(chunks)
        assert output_path is not None
        return output_path

    async def _fetch_chunk(self, url: str, headers: dict[str, str]) -> tuple[bytes, Optional[int]]:
        client = await self._get_client()
        policy = self._retry_policy

        async def attempt(index: int) -> tuple[bytes, Optional[int]]:
            try:
                response = await client.post(url, content=b"", headers=headers, timeout=policy.timeout)
            except httpx.TimeoutException as exc:
                raise _Retry(RequestTimeout(f"Download from {url} timed out", exc)) from exc
            except httpx.HTTPError as exc:
                raise _Retry(NetworkError(f"Download from {url} failed: {exc}", exc)) from exc
            if response.status_code >= 500:
                raise _Retry(TransportError(f"Download failed with HTTP {response.status_code}"))
            if response.status_code >= 400:
                raise TransportError(f"Download failed with HTTP {response.status_code}: {response.text[:200]}")
            length_header = response.headers.get("total_length") or response.headers.get("total-length")
            total_length = int(length_header) if length_header and length_header.isdigit() else None
            return response.content, total_length

        try:
            return await run_with_retries(policy, attempt, retryable=lambda exc: isinstance(exc, _Retry), label="download chunk")
        except _Retry as failure:
            raise failure.error from failure.error

    async def download_url(
        self,
        *,
        url: str,
        path: Union[str, Path, None] = None,
        in_memory: bool = False,
        progress: Optional[ProgressCallback] = None,
        progress_args: tuple[Any, ...] = (),
    ) -> Union[bytes, Path]:
        """Stream a public URL (Rubino media, CDN) to disk or memory."""
        if not url:
            raise TransportError("Downloading a file requires a URL")
        client = await self._get_client()
        output_path: Optional[Path] = None
        file_handle = None
        downloaded = 0
        total: Optional[int] = None
        chunks: list[bytes] = []
        try:
            if not in_memory:
                if path is None:
                    raise TransportError("Downloading to disk requires a destination path")
                output_path = Path(path)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                file_handle = output_path.open("wb")
            try:
                async with client.stream("GET", url) as response:
                    if response.status_code >= 400:
                        raise TransportError(f"Download failed with HTTP {response.status_code}")
                    header_length = response.headers.get("content-length")
                    total = int(header_length) if header_length and header_length.isdigit() else None
                    async for chunk in response.aiter_bytes(self._chunk_size):
                        if not chunk:
                            continue
                        if in_memory:
                            chunks.append(chunk)
                        else:
                            assert file_handle is not None
                            file_handle.write(chunk)
                        downloaded += len(chunk)
                        await report_progress(progress, downloaded, total or downloaded, progress_args)
            except httpx.TimeoutException as exc:
                raise RequestTimeout(f"Download from {url} timed out", exc) from exc
            except httpx.HTTPError as exc:
                raise NetworkError(f"Download from {url} failed: {exc}", exc) from exc
        finally:
            if file_handle is not None:
                file_handle.close()
        if in_memory:
            return b"".join(chunks)
        assert output_path is not None
        return output_path

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None


__all__ = ["DownloadTransport", "fallback_storage_url"]
