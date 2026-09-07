"""Rubino (in-app social network) models."""

from __future__ import annotations

from typing import Any, Optional

from .files import UrlFile
from .object import Object, model
from .raw_object import RawObject


def _rubino_default_name(data: dict[str, Any], *, kind: str) -> Optional[str]:
    post_id = data.get("id") or data.get("post_id")
    file_type = str(data.get("file_type") or "").lower()
    if not post_id:
        return None
    if kind == "thumbnail":
        return f"{post_id}_thumbnail.jpg"
    if kind == "snapshot":
        return f"{post_id}_snapshot.jpg"
    extension = {"video": ".mp4", "image": ".jpg", "picture": ".jpg", "gif": ".gif", "audio": ".mp3", "voice": ".ogg"}.get(file_type, "")
    return f"{post_id}{extension}"


@model
class RubinoPostMedia(Object):
    """One media item of a post (``full_file_url`` / thumbnail / snapshot)."""

    full_file_url: Optional[str] = None
    full_thumbnail_url: Optional[str] = None
    full_snapshot_url: Optional[str] = None
    file_type: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    duration: Optional[float] = None
    file: Optional[UrlFile] = None
    thumbnail: Optional[UrlFile] = None
    snapshot: Optional[UrlFile] = None

    def __post_parse__(self, client: Any, data: dict[str, Any]) -> None:
        self._attach_url_files(client, data)

    def _attach_url_files(self, client: Any, data: dict[str, Any]) -> None:
        if self.file is None:
            self.file = UrlFile.from_url(client, self.full_file_url, file_name=_rubino_default_name(data, kind="file"))
        if self.thumbnail is None:
            self.thumbnail = UrlFile.from_url(client, self.full_thumbnail_url, file_name=_rubino_default_name(data, kind="thumbnail"))
        if self.snapshot is None:
            self.snapshot = UrlFile.from_url(client, self.full_snapshot_url, file_name=_rubino_default_name(data, kind="snapshot"))

    async def download(self, path: Any = None, *, in_memory: bool = False, file_name: Optional[str] = None, progress: Any = None, progress_args: tuple[Any, ...] = (), kind: str = "file") -> Any:
        target = {"file": self.file, "thumbnail": self.thumbnail, "snapshot": self.snapshot}.get(kind)
        if target is None:
            raise RuntimeError(f"This Rubino media does not contain downloadable {kind} data")
        if target._client is None:
            target.bind(self._client)
        return await target.download(path=path, in_memory=in_memory, file_name=file_name, progress=progress, progress_args=progress_args)


@model
class RubinoPost(RubinoPostMedia):
    id: Optional[str] = None
    profile_id: Optional[str] = None
    likes_count: Optional[int] = None
    caption: Optional[str] = None
    create_date: Optional[int] = None
    comment_count: Optional[int] = None
    post_profile_username: Optional[str] = None
    full_post_profile_thumbnail_url: Optional[str] = None
    allow_show_comment: Optional[bool] = None
    most_liked_comment: Optional[RawObject] = None
    is_for_sale: Optional[bool] = None
    sale_price: Optional[Any] = None
    is_multi_file: Optional[bool] = None
    video_view_count: Optional[int] = None
    product_types: list[Any] = None  # type: ignore[assignment]
    share_url: Optional[str] = None
    file_list: list[RubinoPostMedia] = None  # type: ignore[assignment]
    sponsored_text: Optional[Any] = None
    store_product_ids: list[Any] = None  # type: ignore[assignment]
    profile_store_id: Optional[Any] = None
    tagged_profiles: list[Any] = None  # type: ignore[assignment]
    show_type: Optional[Any] = None
    post_profile_is_verified: Optional[Any] = None
    track_id: Optional[str] = None

    def __post_init__(self, client: Any = None) -> None:
        super().__post_init__(client)
        for name in ("product_types", "file_list", "store_product_ids", "tagged_profiles"):
            if getattr(self, name) is None:
                setattr(self, name, [])

    @property
    def post_id(self) -> Optional[str]:
        return self.id


@model
class RubinoPostsResult(Object):
    """Result of ``getProfilePosts``; ``post`` is the first post for convenience."""

    posts: list[RubinoPost] = None  # type: ignore[assignment]
    liked_posts: list[Any] = None  # type: ignore[assignment]
    bookmarked_posts: list[Any] = None  # type: ignore[assignment]
    post: Optional[RubinoPost] = None
    track_id: Optional[str] = None
    has_continue: Optional[bool] = None

    def __post_init__(self, client: Any = None) -> None:
        super().__post_init__(client)
        self.posts = self.posts or []
        self.liked_posts = self.liked_posts or []
        self.bookmarked_posts = self.bookmarked_posts or []
        if self.post is None and self.posts:
            self.post = self.posts[0]


@model
class RubinoStory(RubinoPostMedia):
    id: Optional[str] = None
    profile_id: Optional[str] = None
    story_id: Optional[str] = None
    create_date: Optional[int] = None
    story_type: Optional[str] = None
    view_count: Optional[int] = None

    @property
    def story_identifier(self) -> Optional[str]:
        return self.story_id or self.id


@model
class RubinoStoriesResult(Object):
    """Result of ``getProfilesStoryList``."""

    stories: list[RubinoStory] = None  # type: ignore[assignment]
    profiles: list[Any] = None  # type: ignore[assignment]
    timestamp: Optional[str] = None

    def __post_init__(self, client: Any = None) -> None:
        super().__post_init__(client)
        self.stories = self.stories or []
        self.profiles = self.profiles or []


@model
class BaseInfo(Object):
    """Result of ``getBaseInfo`` on the services base."""

    suggested_urls: Optional[RawObject] = None
    update: Optional[RawObject] = None
    start_popup: Optional[RawObject] = None
    timestamp: Optional[str] = None


__all__ = ["RubinoPostMedia", "RubinoPost", "RubinoPostsResult", "RubinoStory", "RubinoStoriesResult", "BaseInfo"]
