# Update Message Types

This document describes the websocket `message_updates` payload types currently seen from Rubika and how Rubigram exposes them as typed objects.

Base update envelope:

```python
SocketUpdates(
    chat_updates=[...],
    message_updates=[...],
    show_notifications=[...],
    user_guid="..."
)
```

Each item in `message_updates` is parsed into `SocketMessageUpdate`.

Base fields on `SocketMessageUpdate`:
- `message_id`
- `action`
- `message`
- `updated_parameters`
- `timestamp`
- `prev_message_id`
- `object_guid`
- `type`
- `state`
- `is_scheduled`

Rubigram copies important update-level fields down onto `message` so filters and handlers can work directly with the message object:
- `message.action`
- `message.chat_type`
- `message.state`
- `message.is_scheduled`
- `message.prev_message_id`
- `message.object_guid`
- `message.message_id`

## 1. Text

Rubika payload:
- `message.type == "Text"`

Rubigram object:
- `Message`

Common fields:
- `message.message_id`
- `message.text`
- `message.time`
- `message.is_edited`
- `message.author_type`
- `message.author_object_guid`
- `message.allow_transcription`

Useful filters:
- `filters.text`
- `filters.private`
- `filters.group`
- `filters.new`
- `filters.edited`
- `filters.deleted`

## 2. Rubino Post

Rubino is Rubika’s in-app Instagram-like post system.

Rubika payload:
- `message.type == "RubinoPost"`
- `message.rubino_post_data`
- often `message.forwarded_from`

Rubigram object:
- `Message`
- `message.rubino_post_data -> RubinoPostData`
- `message.forwarded_from -> ForwardedFrom`

Parsed fields:
- `message.rubino_post_data.post_id`
- `message.rubino_post_data.post_profile_id`
- `message.rubino_post_data.track_id`
- `message.forwarded_from.type_from`
- `message.forwarded_from.message_id`
- `message.forwarded_from.object_guid`

Useful filters:
- `filters.rubino`
- `filters.forwarded`
- `filters.media`

## 3. Sticker

Rubika payload:
- `message.type == "Sticker"`
- `message.sticker`

Rubigram object:
- `Message`
- `message.sticker -> Sticker`
- `message.sticker.file -> StickerFile`

Parsed fields:
- `message.sticker.emoji_character`
- `message.sticker.w_h_ratio`
- `message.sticker.sticker_id`
- `message.sticker.sticker_set_id`
- `message.sticker.file.file_id`
- `message.sticker.file.mime`
- `message.sticker.file.dc_id`
- `message.sticker.file.access_hash_rec`
- `message.sticker.file.file_name`
- `message.sticker.file.cdn_tag`

Useful filters:
- `filters.sticker`
- `filters.media`

## 4. Voice

Rubika payload:
- `message.type == "FileInline"`
- `message.file_inline.type == "Voice"`

Rubigram object:
- `Message`
- `message.file_inline -> FileInline`

Parsed fields:
- `message.file_inline.file_id`
- `message.file_inline.mime`
- `message.file_inline.dc_id`
- `message.file_inline.access_hash_rec`
- `message.file_inline.file_name`
- `message.file_inline.time`
- `message.file_inline.size`
- `message.file_inline.type`

Useful filters:
- `filters.media`
- `filters.voice`

## 5. GIF

Rubika payload:
- `message.type == "FileInline"`
- `message.file_inline.type == "Gif"`

Rubigram object:
- `Message`
- `message.file_inline -> FileInline`
- optional forwarded info:
  - `message.forwarded_from -> ForwardedFrom`

Common fields:
- `message.file_inline.file_id`
- `message.file_inline.mime`
- `message.file_inline.thumb_inline`
- `message.file_inline.width`
- `message.file_inline.height`
- `message.file_inline.time`
- `message.file_inline.size`
- `message.file_inline.type`

Useful filters:
- `filters.media`
- `filters.gif`
- `filters.forwarded`

## 6. Image With Caption

Rubika payload:
- `message.type == "FileInlineCaption"`
- `message.file_inline.type == "Image"`
- `message.text` contains the caption

Rubigram object:
- `Message`
- `message.file_inline -> FileInline`
- `message.forwarded_from -> ForwardedFrom` if present

Common fields:
- `message.text`
- `message.file_inline.file_id`
- `message.file_inline.mime`
- `message.file_inline.width`
- `message.file_inline.height`
- `message.file_inline.thumb_inline`
- `message.file_inline.size`
- `message.file_inline.is_round`
- `message.file_inline.cdn_tag`
- `message.file_inline.is_spoil`

Useful filters:
- `filters.caption`
- `filters.media`
- `filters.photo`

## 7. Video With Caption

Rubika payload:
- `message.type == "FileInlineCaption"`
- `message.file_inline.type == "Video"`
- `message.text` contains the caption

Rubigram object:
- `Message`
- `message.file_inline -> FileInline`
- `message.forwarded_from -> ForwardedFrom` if present

Common fields:
- `message.text`
- `message.file_inline.file_id`
- `message.file_inline.mime`
- `message.file_inline.width`
- `message.file_inline.height`
- `message.file_inline.time`
- `message.file_inline.size`
- `message.file_inline.thumb_inline`
- `message.file_inline.is_round`
- `message.file_inline.is_spoil`

Useful filters:
- `filters.caption`
- `filters.media`
- `filters.video`

## 8. Document / File

Rubika payload:
- `message.type == "FileInline"`
- `message.file_inline.type == "File"`

Rubigram object:
- `Message`
- `message.file_inline -> FileInline`

Common fields:
- `message.file_inline.file_id`
- `message.file_inline.mime`
- `message.file_inline.dc_id`
- `message.file_inline.access_hash_rec`
- `message.file_inline.file_name`
- `message.file_inline.size`
- `message.file_inline.type`

Useful filters:
- `filters.media`
- `filters.document`

## 9. Live

Rubika payload:
- `message.type == "Live"`
- `message.live_data`

Rubigram object:
- `Message`
- `message.live_data -> LiveData`
- `message.live_data.live_status -> LiveStatus`

Parsed fields:
- `message.live_data.live_id`
- `message.live_data.thumb_inline`
- `message.live_data.access_token`
- `message.live_data.title`
- `message.live_data.live_status.status`
- `message.live_data.live_status.play_count`
- `message.live_data.live_status.allow_comment`
- `message.live_data.live_status.can_play`
- `message.live_data.live_status.timestamp`
- `message.live_data.live_status.title`

Useful filters:
- `filters.live`
- `filters.media`

## 10. Notification Layer

Rubika also sends `show_notifications`.

Rubigram object:
- `ShowNotification`
- `ShowNotification.message_data -> NotificationMessageData`

Common fields:
- `notification_id`
- `type`
- `title`
- `text`
- `message_data.object_guid`
- `message_data.object_type`
- `message_data.message_id`

## 11. Chat Layer

Rubika also sends `chat_updates`.

Rubigram object:
- `SocketChatUpdate`

Common fields:
- `object_guid`
- `action`
- `chat`
- `updated_parameters`
- `timestamp`
- `type`

Nested `chat` is parsed as `Chat`.

## Current Filter Coverage

The current filter layer covers the message types above with:
- `filters.text`
- `filters.rubino`
- `filters.sticker`
- `filters.voice`
- `filters.gif`
- `filters.photo`
- `filters.video`
- `filters.document`
- `filters.live`
- `filters.caption`
- `filters.forwarded`
- `filters.new`
- `filters.edited`
- `filters.deleted`

## Notes

1. Rubika can still add more fields than shown here.
2. Unknown fields are preserved on typed objects as dynamic attributes.
3. If a payload field is not yet modeled explicitly, Rubigram still keeps it through `RawObject` parsing.
