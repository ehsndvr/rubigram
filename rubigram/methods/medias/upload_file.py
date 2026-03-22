from pathlib import Path
from typing import Any, Callable, Optional

import rubigram
from rubigram.types import UploadDescriptor
from rubigram.exceptions import TransportError, LoginRequired


class UploadMedia:
    async def upload_file(
        self: "rubigram.Client",
        *,
        path: str | Path,
        descriptor: UploadDescriptor,
        progress: Optional[Callable[..., Any]] = None,
        progress_args: tuple[Any, ...] = (),
    ) -> UploadDescriptor:
        if self._upload_transport is None:
            raise TransportError("Upload transport is not initialized")
        auth = await self.storage.auth()
        if not auth:
            raise LoginRequired(
                "Uploading files requires an authenticated session")
        return await self._upload_transport.upload_file(
            auth=auth,
            descriptor=descriptor,
            path=path,
            progress=progress,
            progress_args=progress_args,
        )
