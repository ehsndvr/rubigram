from __future__ import annotations

import inspect
from pathlib import Path
from typing import Any, Callable, Optional

import httpx

from rubigram.exceptions import LoginRequired, NetworkError, TransportError
from rubigram.network.headers import build_download_headers


async def _report_progress(
    progress: Optional[Callable[..., Any]],
    current: int,
    total: int,
    progress_args: tuple[Any, ...],
) -> None:
    if progress is None:
        return
    result = progress(current, total, *progress_args)
    if inspect.isawaitable(result):
        await result


class DownloadTransport:
    DEFAULT_TIMEOUT = 60.0
    DEFAULT_CHUNK_SIZE = 262144

    def __init__(self, timeout: float = DEFAULT_TIMEOUT, chunk_size: int = DEFAULT_CHUNK_SIZE):
        self._timeout = timeout
        self._chunk_size = chunk_size
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self._timeout,
                headers=build_download_headers(),
            )
        return self._client

    async def download_file(
        self,
        *,
        auth: str,
        file_id: str | int,
        dc_id: str | int,
        access_hash_rec: str,
        file_size: int | None = None,
        path: str | Path | None = None,
        in_memory: bool = False,
        progress: Optional[Callable[..., Any]] = None,
        progress_args: tuple[Any, ...] = (),
    ) -> bytes | Path:
        if not auth:
            raise LoginRequired("Downloading files requires an authenticated session")
        if not file_id:
            raise TransportError("Downloading a file requires file_id")
        if not dc_id:
            raise TransportError("Downloading a file requires dc_id")
        if not access_hash_rec:
            raise TransportError("Downloading a file requires access_hash_rec")

        url = f"https://messenger{dc_id}.iranlms.ir/GetFile.ashx"
        client = await self._get_client()
        start_index = 0
        requested_length = self._chunk_size + 1
        chunks: list[bytes] = []
        output_path: Path | None = None
        file_handle = None
        downloaded = 0

        try:
            if not in_memory:
                if path is None:
                    raise TransportError("Downloading to disk requires a destination path")
                output_path = Path(path)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                file_handle = output_path.open("wb")

            while True:
                last_index = start_index + self._chunk_size
                try:
                    response = await client.post(
                        url,
                        content=b"",
                        headers={
                            "Auth": auth,
                            "Start-Index": str(start_index),
                            "Last-Index": str(last_index),
                            "File-Id": str(file_id),
                            "Access-Hash-Rec": access_hash_rec,
                        },
                    )
                    response.raise_for_status()
                except httpx.RequestError as e:
                    raise NetworkError(f"Download from {url} failed: {e}", e) from e
                except httpx.HTTPStatusError as e:
                    raise TransportError(f"Download failed with HTTP {e.response.status_code}: {e.response.text}") from e

                chunk = response.content
                if not chunk:
                    break

                if in_memory:
                    chunks.append(chunk)
                else:
                    assert file_handle is not None
                    file_handle.write(chunk)

                downloaded += len(chunk)
                await _report_progress(progress, downloaded, file_size or downloaded, progress_args)
                if file_size is not None and downloaded >= file_size:
                    break
                if len(chunk) < requested_length:
                    break

                start_index = last_index + 1

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
