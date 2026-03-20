from __future__ import annotations

import inspect
import math
from pathlib import Path
from typing import Any, Callable, Optional

import httpx

from rubigram.exceptions import NetworkError, TransportError, map_rpc_error
from rubigram.network.headers import build_upload_headers
from rubigram.types import UploadDescriptor


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


class UploadTransport:
    DEFAULT_TIMEOUT = 60.0
    DEFAULT_CHUNK_SIZE = 131072

    def __init__(self, timeout: float = DEFAULT_TIMEOUT, chunk_size: int = DEFAULT_CHUNK_SIZE):
        self._timeout = timeout
        self._chunk_size = chunk_size
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self._timeout,
                headers=build_upload_headers(),
            )
        return self._client

    async def upload_file(
        self,
        *,
        auth: str,
        descriptor: UploadDescriptor,
        path: str | Path,
        progress: Optional[Callable[..., Any]] = None,
        progress_args: tuple[Any, ...] = (),
    ) -> UploadDescriptor:
        if not auth:
            raise TransportError("Uploading a file requires auth")
        if descriptor.upload_url is None:
            raise TransportError("Upload descriptor does not include upload_url")
        if descriptor.id is None:
            raise TransportError("Upload descriptor does not include file id")
        if descriptor.access_hash_send is None:
            raise TransportError("Upload descriptor does not include access_hash_send")

        file_path = Path(path)
        data = file_path.read_bytes()
        total_parts = max(1, math.ceil(len(data) / self._chunk_size))

        client = await self._get_client()
        access_hash_rec = descriptor.access_hash_rec

        for index in range(total_parts):
            start = index * self._chunk_size
            end = min(len(data), start + self._chunk_size)
            chunk = data[start:end]

            try:
                response = await client.post(
                    descriptor.upload_url,
                    content=chunk,
                    headers={
                        "Auth": auth,
                        "File-Id": str(descriptor.id),
                        "Access-Hash-Send": descriptor.access_hash_send,
                        "Part-Number": str(index + 1),
                        "Total-Part": str(total_parts),
                        "Chunk-Size": str(len(chunk)),
                    },
                )
                response.raise_for_status()
                payload = response.json()
            except httpx.RequestError as e:
                raise NetworkError(f"Upload to {descriptor.upload_url} failed: {e}", e) from e
            except httpx.HTTPStatusError as e:
                raise TransportError(f"Upload failed with HTTP {e.response.status_code}: {e.response.text}") from e
            except Exception as e:
                raise TransportError(f"Failed to parse upload response: {e}") from e

            status = payload.get("status")
            if status and status != "OK":
                raise map_rpc_error(status, payload.get("status_det"), payload)

            data_payload = payload.get("data") or {}
            if data_payload.get("access_hash_rec"):
                access_hash_rec = data_payload["access_hash_rec"]

            await _report_progress(progress, end, len(data), progress_args)

        return UploadDescriptor(
            client=descriptor._client,
            id=descriptor.id,
            dc_id=descriptor.dc_id,
            access_hash_send=descriptor.access_hash_send,
            access_hash_rec=access_hash_rec,
            upload_url=descriptor.upload_url,
        )

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
