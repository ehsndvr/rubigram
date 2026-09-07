# Client Methods Reference

This document describes the current public `Client` API and the typed objects returned by each method.

Peer-aware methods:
- methods that previously accepted `object_guid` can still use it unchanged
- the same methods now also accept `peer=` with a `rubigram.Peer`, a typed object, or any object carrying `object_guid` / `user_guid`

Unified client modes:
- `Client(..., phone_number=...)` or interactive auth uses the user session flow
- `Client(..., token="...")` uses the bot API flow with the same session storage and session string format

## Authentication and Session

### `await app.start() -> Client`
Starts the client.

What it does:
- Opens storage
- Refreshes DC configuration
- Loads or creates login key material
- Initializes HTTP transport
- Performs socket handshake if an authenticated session exists
- Runs `registerDevice` when required
- Starts the update listener when possible

### `await app.stop() -> None`
Stops the client and closes:
- websocket transport
- HTTP transport
- DC discovery client
- storage connection

### `await app.export_session_string() -> str`
Exports the current session state as a JSON base64-url-safe session string.

Persisted fields include:
- `api_version`
- `api_url`
- `api_urls`
- `storages`
- `cdn_urls`
- `sockets`
- `auth`
- `tmp_session`
- `public_key`
- `private_key_pem`
- `user_guid`
- `updates_state`
- `device_hash`
- `registered_device`
- `registered_device_version`

## Login Flow

### `await app.send_code(phone_number: str) -> SentCode`
Sends an OTP/login code.

Returned object:
- `SentCode.phone_code_hash`
- `SentCode.status`
- `SentCode.code_digits_count`
- `SentCode.has_confirmed_recovery_email`
- `SentCode.no_recovery_alert`
- `SentCode.send_type`

Typical Rubika data shape:

```python
SentCode(
    phone_code_hash="38044635070003564482129527665122",
    status="OK",
    code_digits_count=6,
    has_confirmed_recovery_email=False,
    no_recovery_alert="...",
    send_type="SMS",
)
```

### `await app.sign_in(phone_number, phone_code_hash, phone_code) -> Authorization`
Signs in with the OTP code.

Returned object:
- `Authorization.status`
- `Authorization.auth`
- `Authorization.user`
- `Authorization.timestamp`

Notes:
- `Authorization.auth` is the encrypted auth returned by Rubika at the payload level.
- Rubigram unwraps and stores the usable session auth internally after success.

### `await app.sign_up(first_name, last_name="") -> Authorization`
Completes registration for a new user when required.

### `await app.register_device(force: bool = False) -> Empty`
Registers the current device/session with Rubika.

Returned object:
- `Empty` (an empty typed object)

## User and Chat Methods

### `await app.get_user_info(user_guid: str) -> UserInfo`
Returns detailed information about a user and its chat relation.

Returned object:
- `UserInfo.user`
- `UserInfo.chat`
- `UserInfo.timestamp`
- `UserInfo.can_receive_call`
- `UserInfo.can_video_call`
- `UserInfo.user_additional_info`

Notes:
- Contact-related flags such as `is_in_contact` may be returned inside `UserInfo.user_additional_info`.
- If the target user is not found, the server can return `ERROR_GENERIC: INVALID_INPUT`, which maps to `rubigram.exceptions.InvalidInput`.

Common nested objects:
- `User`
- `Chat`
- `OnlineTime`
- `UserAdditionalInfo`

### `await app.get_me() -> UserInfo`
Equivalent to `get_user_info()` using the authenticated `user_guid` stored in session.

### `await app.get_object_by_username(username: str) -> ObjectByUsername`
Looks up a user/chat by username.

Returned object:
- `ObjectByUsername.exist`
- `ObjectByUsername.type`
- `ObjectByUsername.user`
- `ObjectByUsername.chat`
- `ObjectByUsername.timestamp`
- `ObjectByUsername.is_in_contact`

### `await app.search_global_objects(search_text, filter_types=()) -> SearchGlobalObjectsResult`
Searches global users, bots, channels, and other public objects.

Input:
- `search_text` is the query text
- `filter_types` is sent as a list of raw string filter names such as `Bot`

Returned object:
- `SearchGlobalObjectsResult.objects`
- `SearchGlobalObjectsResult.has_continue`
- `SearchGlobalObjectsResult.timestamp`

Common nested payload:
- `object.object_guid`
- `object.type`
- `object.title`
- `object.avatar_thumbnail`
- `object.username`
- `object.track_id`

Download helpers:
- `await result.objects[i].avatar_thumbnail.download(...)`

### `await app.get_rubino_post(post_id=None, post_profile_id=None, *, rubino_post_data=None, track_id=None) -> RawObject`
Fetches a single Rubino post payload from the Rubino DC in the discovered DC list.

Input:
- pass `post_id` and `post_profile_id`, or pass `rubino_post_data=message.rubino_post_data`
- `track_id` is accepted for convenience when you are calling this from a `RubinoPost` message, but it is not required by the upstream request

Request behavior:
- uses plain JSON `getProfilePosts`
- resolves the Rubino host from plain JSON `getBaseInfo` on `https://servicesbase.iranlms.ir/`
- targets the suggested Rubino host from `suggested_urls.suggested_rubino`, for example `https://rubino2.iranlms.ir/`
- sends `equal=True`, `limit=1`, `sort="FromMax"`, with `min_id == max_id == post_id`

Returned object:
- `result.posts`
- `result.post` as a convenience alias for `result.posts[0]` when present
- `result.liked_posts`
- `result.bookmarked_posts`

Download helpers:
- `await result.post.download(...)` downloads the main media when available
- `await result.post.thumbnail.download(...)`
- `await result.post.snapshot.download(...)`
- `await result.post.file.download(...)`
- `await result.post.file_list[i].download(...)` for multi-file posts when file URLs are present

### `await app.get_base_info() -> RawObject`
Fetches plain JSON `getBaseInfo` from `https://servicesbase.iranlms.ir/` using the authenticated session.

Returned object commonly includes:
- `result.suggested_urls`
- `result.update`
- `result.start_popup`

Notes:
- `suggested_urls` is cached in session storage
- Rubigram uses this response to resolve the current Rubino base URL

### `await app.get_avatars(object_guid: str) -> ChatAvatars`
Returns avatars for a user or chat.

Returned object:
- `ChatAvatars.avatars`

Nested:
- `Avatar.avatar_id`
- `Avatar.thumbnail`
- `Avatar.main`
- `Avatar.create_time`

Helpers:
- `await avatars[-1].download(path=None, file_name=None, use_thumbnail=False)`
- `await avatars.download(path, use_thumbnail=False)` downloads all avatars with generated names such as `avatar_id_main.jpg`

### `await app.get_contacts(offset=0, limit=100) -> RawObject`
Current status:
- implemented
- still returned as `RawObject`
- can be typed further later

### `await app.get_contacts_updates(state: int) -> ContactsUpdates`
Polls `getContactsUpdates`.

Returned object:
- `ContactsUpdates.users`
- `ContactsUpdates.deleted_users`
- `ContactsUpdates.new_state`
- `ContactsUpdates.status`
- `ContactsUpdates.timestamp`

Notes:
- this wrapper currently requires an explicit `state`
- unlike `get_chats_updates(...)`, it does not yet persist contact-update state in storage

### `await app.get_contacts_last_online(user_guids) -> ContactsLastOnline`
Returns last-online metadata for multiple users in one request.

Input:
- `user_guids` is a sequence of user guids
- each item is normalized through the same user-guid resolver used elsewhere in the client

Returned object:
- `ContactsLastOnline.users`

Nested objects:
- each item in `users` is a `User`
- commonly available fields for this method are:
- `user.user_guid`
- `user.last_online`
- `user.online_time`

Notes:
- this response is intentionally modeled as `list[User]` because the server returns user-shaped objects with a smaller field set
- the server may return fewer entries than requested if some users do not appear in the response payload
- `online_time.type` may be values such as `Approximate` and can include fields like `approximate_period`

### `await app.get_profile_link_items(object_guid, *, peer=None) -> ProfileLinkItems`
Returns profile/action link items associated with the target object.

Input:
- `object_guid` can be passed directly or via `peer=`

Returned object:
- `ProfileLinkItems.link_items`

Common nested payload:
- `link_item.title`
- `link_item.link.type`
- `link_item.link.inline_open_url_data.title`
- `link_item.link.inline_open_url_data.url`

### `await app.get_chat(object_guid: str) -> RawObject`
Current status:
- implemented
- still returned as `RawObject`

### `await app.get_messages(object_guid: str, offset=0, limit=20) -> RawObject`
Current status:
- implemented
- still returned as `RawObject`

### `await app.get_history(object_guid: str, offset=0, limit=50) -> RawObject`
Current status:
- implemented
- still returned as `RawObject`

### `await app.get_chats_updates(state: int | None = None) -> ChatsUpdates`
Polls `getChatsUpdates`.

Returned object:
- `ChatsUpdates.chats`
- `ChatsUpdates.new_state`
- `ChatsUpdates.status`
- `ChatsUpdates.timestamp`

If `state` is omitted:
- Rubigram uses `storage.updates_state()`
- if no stored state exists, it starts from current Unix time

### `await app.get_available_reactions() -> AvailableReactions`
Returns the canonical list of reaction ids and their display metadata.

Returned object:
- `AvailableReactions.reactions`

Common nested payload:
- `reaction.reaction_id`
- `reaction.emoji_char`
- `reaction.name`

Notes:
- use this method as the source of valid `reaction_id` values for APIs such as `set_group_reactions_selected(...)`

## Channels

### `await app.add_channel(title, description="", channel_type="Private", member_guids=None, *, thumbnail_file_id, main_file_id) -> AddChannelResult`
Creates a new channel with the provided metadata and avatar file ids.

Returned object:
- `AddChannelResult.channel`
- `AddChannelResult.chat_update`
- `AddChannelResult.message_update`
- `AddChannelResult.timestamp`

Common nested payload:
- `channel.channel_guid`
- `channel.channel_title`
- `channel.description`
- `channel.channel_type`
- `channel.avatar_thumbnail`
- `channel.chat_reaction_setting.reaction_type`
- `chat_update.object_guid`
- `message_update.message.text`

Notes:
- this method currently implements the confirmed `addChannel` payload shape only
- `member_guids` entries are resolved through the same peer/object-guid normalization used elsewhere
- `thumbnail_file_id` and `main_file_id` are sent exactly as provided

Alias:
- `await app.create_channel(title, description="", channel_type="Private", member_guids=None, *, thumbnail_file_id, main_file_id)`

### `await app.add_channel_members(object_guid, member_guids, *, peer=None) -> AddChannelMembersResult`
Adds users, bots, or peer-like objects to an existing channel.

Returned object:
- `AddChannelMembersResult.added_in_chat_members`
- `AddChannelMembersResult.channel`
- `AddChannelMembersResult.timestamp`

Notes:
- `object_guid` can be the channel guid directly or provided via `peer=`
- each entry in `member_guids` is resolved through the same peer-aware rules used elsewhere in the client

### `await app.get_channel_link(object_guid, *, peer=None) -> Empty`
Fetches the current channel-link payload for the target channel.

Input:
- `object_guid` can be passed directly or via `peer=`

Returned object:
- `Empty`

Notes:
- the confirmed server sample you provided currently returns `data: {}`
- this method is implemented without guessing undocumented fields beyond that shape

### `await app.get_channel_info(object_guid, *, peer=None) -> ChannelInfo`
Returns detailed information about a channel and its chat state.

Returned object:
- `ChannelInfo.channel`
- `ChannelInfo.chat`
- `ChannelInfo.timestamp`

Common nested payload:
- `channel.channel_guid`
- `channel.channel_title`
- `channel.avatar_thumbnail`
- `chat.object_guid`
- `chat.last_message`
- `chat.abs_object`

Download helpers:
- `await info.channel.avatar_thumbnail.download(...)`
- `await info.chat.abs_object.avatar_thumbnail.download(...)`

### `await app.get_channel_all_members(object_guid, *, peer=None) -> GroupMembers`
Returns the current members visible in a channel.

Returned object:
- `GroupMembers.in_chat_members`
- `GroupMembers.has_continue`
- `GroupMembers.timestamp`

Member fields commonly returned:
- `member.member_type`
- `member.member_guid`
- `member.first_name`
- `member.last_name`
- `member.username`
- `member.join_type`
- `member.online_time`

### `await app.get_channel_admin_members(object_guid, *, peer=None) -> GroupMembers`
Returns the current admin members visible in a channel.

Returned object:
- `GroupMembers.in_chat_members`
- `GroupMembers.next_start_id`
- `GroupMembers.has_continue`
- `GroupMembers.timestamp`

Member fields commonly returned:
- `member.member_type`
- `member.member_guid`
- `member.first_name`
- `member.username`
- `member.join_type`
- `member.online_time`

### `await app.get_banned_channel_members(object_guid, *, peer=None) -> GroupMembers`
Returns the current banned members visible in a channel.

Returned object:
- `GroupMembers.in_chat_members`
- `GroupMembers.has_continue`
- `GroupMembers.timestamp`

### `await app.edit_channel_info(object_guid, *, peer=None, title=None, description=None) -> EditChannelInfoResult`
Edits the currently supported mutable channel info fields.

Currently supported fields:
- `title`
- `description`

What this method does:
- builds the `updated_parameters` array automatically
- sends only the fields you explicitly provide

Returned object:
- `EditChannelInfoResult.channel`
- `EditChannelInfoResult.chat_update`
- `EditChannelInfoResult.timestamp`

Common nested payload:
- `channel.channel_title`
- `channel.description`
- `channel.chat_reaction_setting`
- `chat_update.chat.abs_object`

Validation behavior:
- if neither supported field is provided, Rubigram raises `ValueError`

### `await app.set_channel_admin(object_guid, member_guid, access_list, *, peer=None) -> SetGroupAdminResult`
Promotes a member to channel admin or updates that admin's access list.

What this method does:
- resolves the target channel from `object_guid` or `peer=`
- resolves the target member from `member_guid`
- sends `setChannelAdmin` with `action="SetAdmin"`

Returned object:
- `SetGroupAdminResult.in_chat_member`
- `SetGroupAdminResult.timestamp`

Access list typing:
- enum values such as `rubigram.enums.GroupAdminAccess` are accepted
- raw string access names are also accepted for compatibility

Aliases:
- `await app.update_channel_admin_access(object_guid, member_guid, access_list, *, peer=None)`
- `await app.unset_channel_admin(object_guid, member_guid, *, peer=None)`

Notes:
- `unset_channel_admin(...)` uses the same RPC method with `action="UnsetAdmin"`
- based on the confirmed sample you provided, `UnsetAdmin` can still return a populated `in_chat_member` plus `timestamp`

## Groups

### `await app.add_group(title, member_guids=None) -> AddGroupResult`
Creates a new group and can include initial members.

Returned object:
- `AddGroupResult.group`
- `AddGroupResult.chat_update`
- `AddGroupResult.message_update`
- `AddGroupResult.timestamp`

Common nested payload:
- `group.group_guid`
- `group.group_title`
- `group.count_members`
- `group.chat_reaction_setting.reaction_type`
- `chat_update.object_guid`
- `message_update.message.text`

Alias:
- `await app.create_group(title, member_guids=None)`

### `await app.add_group_members(object_guid, member_guids, *, peer=None) -> RawObject`
Adds users, bots, or peer-like objects to an existing group.

Notes:
- `object_guid` can be the group guid directly or provided via `peer=`
- each entry in `member_guids` is resolved through the same peer-aware rules used elsewhere in the client

### `await app.ban_group_member(object_guid, member_guid, *, peer=None) -> BanGroupMemberResult`
Bans a member from a group.

What this method does:
- resolves the target group from `object_guid` or `peer=`
- resolves the target member from `member_guid`
- sends `banGroupMember` with `action="Set"`

Returned object:
- `BanGroupMemberResult.timestamp`
- `BanGroupMemberResult.group`

Common nested payload:
- `group.group_guid`
- `group.count_members`
- `group.chat_history_for_new_members`
- `group.event_messages`
- `group.chat_reaction_setting.reaction_type`

Notes:
- this implementation currently covers the confirmed ban flow using `action="Set"`
- the target member may be a user, bot, or any peer-like value that resolves to a guid

### `await app.unban_group_member(object_guid, member_guid, *, peer=None) -> BanGroupMemberResult`
Removes a ban from a previously banned group member.

What this method does:
- resolves the target group from `object_guid` or `peer=`
- resolves the target member from `member_guid`
- sends `banGroupMember` with `action="Unset"`

Returned object:
- `BanGroupMemberResult.timestamp`
- `BanGroupMemberResult.group`

Notes:
- Rubika uses the same RPC method, `banGroupMember`, for both ban and unban operations
- in this wrapper, unban is represented explicitly as `unban_group_member(...)` for clarity
- the response shape is the same typed result used by `ban_group_member(...)`

### `await app.set_group_admin(object_guid, member_guid, access_list, *, peer=None) -> SetGroupAdminResult`
Promotes a member to admin or updates that admin's access list.

What this method does:
- resolves the target group from `object_guid` or `peer=`
- resolves the target member from `member_guid`
- sends `setGroupAdmin` with `action="SetAdmin"`
- passes the provided `access_list` as typed enum values or raw strings

Returned object:
- `SetGroupAdminResult.in_chat_member`
- `SetGroupAdminResult.timestamp`

Common nested payload:
- `in_chat_member.member_guid`
- `in_chat_member.join_type`
- `in_chat_member.promoted_by_object_guid`
- `in_chat_member.promoted_by_object_type`
- `in_chat_member.username`
- `in_chat_member.online_time`

Access list typing:
- Rubigram exposes these values as `rubigram.enums.GroupAdminAccess`
- raw string values are still accepted for compatibility

Current known enum values:
- `GroupAdminAccess.CHANGE_INFO`
- `GroupAdminAccess.PIN_MESSAGES`
- `GroupAdminAccess.DELETE_GLOBAL_ALL_MESSAGES`
- `GroupAdminAccess.BAN_MEMBER`
- `GroupAdminAccess.SET_JOIN_LINK`
- `GroupAdminAccess.SET_ADMIN`
- `GroupAdminAccess.SET_MEMBER_ACCESS`

Examples:

```python
from rubigram.enums import GroupAdminAccess

await app.set_group_admin(
    "g0...",
    "u0...",
    [
        GroupAdminAccess.CHANGE_INFO,
        GroupAdminAccess.PIN_MESSAGES,
        GroupAdminAccess.DELETE_GLOBAL_ALL_MESSAGES,
        GroupAdminAccess.BAN_MEMBER,
        GroupAdminAccess.SET_JOIN_LINK,
        GroupAdminAccess.SET_ADMIN,
        GroupAdminAccess.SET_MEMBER_ACCESS,
    ],
)
```

```python
await app.update_group_admin_access(
    "g0...",
    "u0...",
    [
        "ChangeInfo",
        "PinMessages",
        "BanMember",
        "SetJoinLink",
        "SetAdmin",
        "SetMemberAccess",
    ],
)
```

Notes:
- Rubika appears to use the same `setGroupAdmin` request both for initial promotion and later access updates
- `update_group_admin_access(...)` is provided as an alias for readability, but it sends the same RPC method and payload shape
- current implementation is scoped to the confirmed `action="SetAdmin"` flow you provided

### `await app.unset_group_admin(object_guid, member_guid, *, peer=None) -> SetGroupAdminResult`
Removes admin status from a member.

What this method does:
- resolves the target group from `object_guid` or `peer=`
- resolves the target member from `member_guid`
- sends `setGroupAdmin` with `action="UnsetAdmin"`
- does not send `access_list`, matching the confirmed request shape you provided

Returned object:
- `SetGroupAdminResult.in_chat_member`
- `SetGroupAdminResult.timestamp`

Notes:
- Rubika uses the same RPC method, `setGroupAdmin`, for promotion, access updates, and admin removal
- this wrapper exists to keep the public API explicit and easier to read
- the exact response body for `UnsetAdmin` has not yet been documented here because you only provided the request payload

### `await app.request_change_object_owner(object_guid, new_owner_user_guid, *, peer=None) -> RawObject`
Requests transferring ownership of an object, such as a group, to another user.

What this method does:
- resolves the target object from `object_guid` or `peer=`
- resolves the target new owner from `new_owner_user_guid`
- sends `requestChangeObjectOwner`

Current implementation status:
- method is implemented and callable
- a successful `OK` response shape has not been documented yet
- therefore the success path is currently left as `RawObject`

Currently observed server behavior:
- the sample response you provided returns `ERROR_GENERIC` with `status_det="INVALID_AUTH"`
- the server also includes a user-facing alert message: `از زمان ورود شما بایستی 3 روز گذشته باشد.`

Practical meaning of the current observed error:
- the server is refusing the ownership-transfer request because the session/account is too new for this action
- based on the alert text, at least 3 days must have passed since login

Error handling note:
- in Rubigram this server response currently maps to an exception rather than a normal typed success object
- the raw server payload remains attached on the raised RPC exception via `exc.raw`

Known request shape:

```python
{
    "object_guid": "g0...",
    "new_owner_user_guid": "u0...",
}
```

### `await app.remove_group(object_guid, *, peer=None) -> RawObject`
Requests deleting/removing a group.

What this method does:
- resolves the target group from `object_guid` or `peer=`
- sends `removeGroup`

Current implementation status:
- method is implemented and callable
- a successful `OK` response shape has not been documented yet
- therefore the success path is currently left as `RawObject`

Currently observed server behavior:
- the sample response you provided returns `ERROR_GENERIC` with `status_det="INVALID_AUTH"`
- the server also includes a user-facing alert message: `از زمان ورود شما بایستی 3 روز گذشته باشد.`

Practical meaning of the current observed error:
- the server is refusing the group-removal request because the session/account is too new for this action
- based on the alert text, at least 3 days must have passed since login

Error handling note:
- in Rubigram this server response currently maps to an exception rather than a normal typed success object
- the raw server payload remains attached on the raised RPC exception via `exc.raw`

Known request shape:

```python
{
    "group_guid": "g0...",
}
```

### `await app.upload_group_avatar(object_guid, path, *, peer=None, mime=None, progress=None, progress_args=()) -> RawObject`
Uploads a local image and sets it as the group avatar.

Alias:
- `await app.set_group_photo(object_guid, path, ...)`

Notes:
- current implementation uses `requestSendFile` + binary upload + `uploadNewGroupAvatar`
- the final `uploadNewGroupAvatar` request shape is inferred as `group_guid`, `file_id`, `dc_id`, and `access_hash_rec`
- `progress(current, total, *progress_args)` is called during upload

### `await app.get_group_info(object_guid, *, peer=None) -> GroupInfo`
Returns detailed information about a group.

Returned object:
- `GroupInfo.group`
- `GroupInfo.chat`
- `GroupInfo.timestamp`

Common nested payload:
- `group.group_guid`
- `group.group_title`
- `group.count_members`
- `group.chat_reaction_setting.reaction_type`
- `chat.object_guid`
- `chat.last_message`
- `chat.last_message_id`

### `await app.get_group_all_members(object_guid, *, peer=None) -> GroupMembers`
Returns the current members visible in a group.

Returned object:
- `GroupMembers.in_chat_members`
- `GroupMembers.has_continue`
- `GroupMembers.timestamp`

Member fields commonly returned:
- `member.member_type`
- `member.member_guid`
- `member.join_type`
- `member.username`
- `member.first_name` for users
- `member.title` for bots
- `member.online_time`

### `await app.get_group_default_access(object_guid, *, peer=None) -> GroupDefaultAccess`
Returns the default access list applied to regular group members.

Returned object:
- `GroupDefaultAccess.access_list`

### `await app.set_group_default_access(object_guid, access_list, *, peer=None) -> RawObject`
Sets the default permissions granted to regular group members in a group.

What this method does:
- resolves the target group from `object_guid` or `peer=`
- sends `setGroupDefaultAccess`
- every permission included in `access_list` is treated as granted
- accepts both enum values and raw strings for compatibility

Access list typing:
- Rubigram exposes these values as `rubigram.enums.GroupDefaultAccessPermission`
- raw string values are still accepted

Current known enum values:
- `GroupDefaultAccessPermission.VIEW_MEMBERS`
- `GroupDefaultAccessPermission.ADD_MEMBER`
- `GroupDefaultAccessPermission.SEND_MESSAGES`
- `GroupDefaultAccessPermission.VIEW_ADMINS`

Example:

```python
from rubigram.enums import GroupDefaultAccessPermission

await app.set_group_default_access(
    "g0...",
    [
        GroupDefaultAccessPermission.VIEW_MEMBERS,
        GroupDefaultAccessPermission.ADD_MEMBER,
        GroupDefaultAccessPermission.SEND_MESSAGES,
        GroupDefaultAccessPermission.VIEW_ADMINS,
    ],
)
```

Current implementation status:
- the request shape is confirmed
- the successful response body is not documented yet
- for that reason, this method currently returns `RawObject`

### `await app.get_pending_object_owner(object_guid, *, peer=None) -> PendingObjectOwner`
Checks whether the given chat object currently has a pending ownership transfer awaiting confirmation.

Primary use case:
- call this after initiating a group ownership transfer
- use it while waiting for the target admin/user to accept or reject the ownership handoff
- this is especially useful for groups, where ownership transfer is not final immediately after the request is sent

Input:
- `object_guid` may be a group guid directly
- or you can pass `peer=` with any peer-like value supported elsewhere in the client

Returned object:
- `PendingObjectOwner.exist_pending_owner`

Meaning of `exist_pending_owner`:
- `True`: there is still an unresolved pending owner transfer for this object
- `False`: there is no active pending owner transfer at the time of the request

Important interpretation notes:
- this method only reports whether a pending transfer exists
- it does not tell you who the pending new owner is
- it does not tell you whether the transfer was accepted, rejected, or never requested in the first place
- a `False` result should be interpreted as "no current pending request", not automatically as "ownership transfer succeeded"

Typical flow:
1. request ownership transfer for the group
2. poll or re-check `get_pending_object_owner(...)`
3. when it returns `False`, verify the final group ownership state using the relevant ownership/admin info methods or your application flow

Current known response shape:

```python
PendingObjectOwner(
    exist_pending_owner=False,
)
```

### `await app.get_group_link(object_guid, *, peer=None) -> GroupLink`
Returns the current join link for a group.

Returned object:
- `GroupLink.join_link`

Notes:
- this returns the existing active join link for the group
- the response shown so far contains only the link itself
- this method does not rotate or regenerate the link; it only fetches the current one

Typical value:

```python
GroupLink(
    join_link="https://rubika.ir/joing/JJACJHBD0WFGDWEZRHFHVQDNSLDCUTEU",
)
```

### `await app.get_join_links(object_guid, *, peer=None) -> JoinLinks`
Returns the list of generated membership/join links currently associated with the object.

Primary use case:
- use this when you create additional join links for a group and want to inspect the current list
- unlike `get_group_link(...)`, this method is list-oriented and is intended for multi-link scenarios

Returned object:
- `JoinLinks.join_links`

Notes:
- the current observed response shape is a plain list of strings
- the list may be empty, as in the sample response you provided
- this method does not create a new join link; it only fetches the existing generated links

Typical value:

```python
JoinLinks(
    join_links=[],
)
```

### `await app.create_join_link(object_guid, title, *, peer=None, request_needed=False, expire_time=0, usage_limit=0) -> CreatedJoinLink`
Creates a new join link for the target object, typically a group.

Primary use case:
- generate additional invite/join links for a group
- create links with their own title, expiration policy, and usage limit
- optionally require join requests instead of immediate access

Parameters:
- `object_guid` or `peer=`: the target object, such as a group
- `title`: display label for the generated join link
- `request_needed`: whether joining through this link should require approval
- `expire_time`: link lifetime in seconds
- `usage_limit`: maximum number of uses allowed for this link

Returned object:
- `CreatedJoinLink.join_link`

Common nested payload:
- `join_link.object_guid.type`
- `join_link.object_guid.object_guid`
- `join_link.join_link`
- `join_link.creator_guid`
- `join_link.create_time`
- `join_link.request_pending_count`
- `join_link.request_needed`
- `join_link.usage_limit`
- `join_link.title`
- `join_link.expire_time`
- `join_link.expire_at`

Notes:
- this method creates a new managed join link rather than reading the current default one
- the returned payload is richer than `get_group_link(...)` and can be used to inspect link policy and timing
- the same link should typically appear later in `get_join_links(...)`

Typical value:

```python
CreatedJoinLink(
    join_link=JoinLinkEntry(
        join_link="https://rubika.ir/joing/+JJACJHBD0ITDCAGNMHWBIUSXAXLMSZNJ",
        title="tt",
        usage_limit=10,
        expire_time=86400,
    ),
)
```

### `await app.edit_group_info(object_guid, *, peer=None, event_messages=None, chat_history_for_new_members=None, chat_reaction_setting=None, slow_mode=None) -> EditGroupInfoResult`
Edits the currently supported mutable group info fields.

Currently supported fields:
- `event_messages`
- `chat_history_for_new_members`
- `chat_reaction_setting`
- `slow_mode`

What this method does:
- builds the `updated_parameters` array automatically
- sends only the fields you explicitly provide
- returns the updated `group` payload and response `timestamp`

Returned object:
- `EditGroupInfoResult.group`
- `EditGroupInfoResult.timestamp`

Common nested payload:
- `group.group_guid`
- `group.chat_history_for_new_members`
- `group.event_messages`
- `group.chat_reaction_setting.reaction_type`
- `group.chat_reaction_setting.selected_reactions`

Validation behavior:
- if neither supported field is provided, Rubigram raises `ValueError`
- this prevents sending an empty `editGroupInfo` request

Supported values:
- `event_messages`: `True` or `False`
- `chat_history_for_new_members`: currently observed values are `"Visible"` and `"Hidden"`
- `chat_reaction_setting.reaction_type`: currently observed values are `"All"`, `"Disabled"`, and `"Selected"`
- when `reaction_type="Selected"`, include `selected_reactions` as a list of reaction ids
- `slow_mode`: integer seconds; send `0` to disable slow mode

Convenience aliases:
- `await app.set_group_event_messages(object_guid, enabled=True, *, peer=None)`
- `await app.set_group_history_for_new_members(object_guid, value="Visible", *, peer=None)`
- `await app.set_group_slow_mode(object_guid, seconds=0, *, peer=None)`
- `await app.set_group_reactions_all(object_guid, *, peer=None)`
- `await app.set_group_reactions_disabled(object_guid, *, peer=None)`
- `await app.set_group_reactions_selected(object_guid, selected_reactions, *, peer=None)`

Typical use cases:
- enable or disable group event/system messages
- choose whether chat history is visible to new members
- set a slow mode interval for sending messages in the group, or reset it back to `0`
- allow all reactions, disable reactions entirely, or restrict the group to a selected set of reactions

Examples:

```python
await app.set_group_event_messages("g0...", enabled=True)
await app.set_group_event_messages("g0...", enabled=False)
await app.set_group_history_for_new_members("g0...", value="Visible")
await app.set_group_history_for_new_members("g0...", value="Hidden")
await app.set_group_slow_mode("g0...", seconds=30)
await app.set_group_slow_mode("g0...", seconds=0)
await app.set_group_reactions_disabled("g0...")
await app.set_group_reactions_all("g0...")
await app.set_group_reactions_selected("g0...", ["1", "2", "3"])
```

Known request shapes:

```python
{
    "group_guid": "g0...",
    "event_messages": True,
    "updated_parameters": ["event_messages"],
}
```

```python
{
    "group_guid": "g0...",
    "chat_history_for_new_members": "Visible",
    "updated_parameters": ["chat_history_for_new_members"],
}
```

```python
{
    "group_guid": "g0...",
    "slow_mode": 30,
    "updated_parameters": ["slow_mode"],
}
```

```python
{
    "group_guid": "g0...",
    "chat_reaction_setting": {
        "reaction_type": "Disabled",
    },
    "updated_parameters": ["chat_reaction_setting"],
}
```

```python
{
    "group_guid": "g0...",
    "chat_reaction_setting": {
        "reaction_type": "Selected",
        "selected_reactions": ["1", "2", "3"],
    },
    "updated_parameters": ["chat_reaction_setting"],
}
```

Notes:
- this implementation is intentionally limited to the confirmed editable fields above
- if later you provide verified payloads for more editable group fields, this method can be expanded without changing its overall pattern

## Messaging

### `await app.request_send_file(file_name: str, size: int, mime: str) -> UploadDescriptor`
Requests an upload slot from Rubika before sending media bytes.

Returned object:
- `UploadDescriptor.id`
- `UploadDescriptor.dc_id`
- `UploadDescriptor.access_hash_send`
- `UploadDescriptor.upload_url`
- `UploadDescriptor.access_hash_rec`

Typical Rubika data shape:

```python
UploadDescriptor(
    id="87998036915657",
    dc_id="491",
    access_hash_send="euthauxjfybzjbaaymlitbhpio8651",
    upload_url="https://upmessenger491.iranlms.ir/UploadFile.ashx",
)
```

### `await app.send_message(object_guid, rnd, text, parse_mode=None, reply_to_message_id=None) -> SentMessage`
Sends a text message.

Returned object:
- `SentMessage.message_update`
- `SentMessage.status`
- `SentMessage.chat_update`

Common nested payload:
- `message_update.message_id`
- `message_update.message.text`
- `chat_update.chat.last_message`

### `await app.send_voice(object_guid, path, rnd=None, duration_ms=0, mime=None) -> SentMessage`
Uploads a local voice file and sends it as a `Voice` media message.

Current implemented flow:
1. `requestSendFile`
2. binary upload to `UploadFile.ashx`
3. `sendMessage` with `file_inline`

Current file-inline payload shape:

```python
{
    "file_name": "voice.ogg",
    "time": 720,
    "size": 1654,
    "type": "Voice",
    "dc_id": "491",
    "file_id": "87998036915657",
    "mime": "ogg",
    "access_hash_rec": "1827275907694936106542107050922026031521",
}
```

Notes:
- `duration_ms` is currently explicit. Rubigram does not yet derive OGG/Opus duration automatically.
- This upload pipeline is designed to be reused later for `send_photo`, `send_video`, and `send_document`.

### `await app.download_file(file, path=None, *, in_memory=False, file_name=None) -> bytes | Path`
Downloads media using Rubika `GetFile.ashx` chunked requests.

Accepted input objects:
- `Message` with `file_inline`
- `Message` with `sticker.file`
- `FileInline`
- `StickerFile`
- `Sticker`

Behavior:
- if `in_memory=True`, returns `bytes`
- otherwise returns the downloaded `Path`
- if `path` is a directory, Rubigram uses the media file name
- `progress(current, total, *progress_args)` is called during download

Related bound methods:
- `await message.download(...)`
- `await message.file_inline.download(...)`
- `await message.sticker.download(...)`

### `await app.send_music(object_guid, path, *, duration_ms, rnd=None, mime=None, progress=None, progress_args=()) -> SentMessage`
Uploads a local audio file and sends it as a `Music` media message.

### `await app.send_photo(object_guid, path, *, rnd=None, mime=None, text=None, width=None, height=None, progress=None, progress_args=()) -> SentMessage`
Uploads a local image and sends it as an `Image` media message.

### `await app.send_document(object_guid, path, *, rnd=None, mime=None, text=None, progress=None, progress_args=()) -> SentMessage`
Uploads a local file and sends it as a generic `File` media message.

Notes:
- current implementation expects `duration_ms` explicitly
- `progress(current, total, *progress_args)` is called during upload

### `await app.send_video(object_guid, path, *, duration_ms, width, height, rnd=None, mime=None, text=None, is_round=False, is_spoil=False, progress=None, progress_args=()) -> SentMessage`
Uploads a local video file and sends it as a `Video` media message.

Notes:
- current implementation expects `duration_ms`, `width`, and `height` explicitly
- if `text` is provided, it is sent as caption
- `progress(current, total, *progress_args)` is called during upload

### `await app.edit_message(object_guid, message_id, text) -> RawObject`
Current status:
- implemented
- still returned as `RawObject`

### `await app.delete_message(object_guid, message_id) -> RawObject`
Current status:
- implemented
- still returned as `RawObject`

### `await app.delete_chat_history(object_guid, last_message_id, *, peer=None) -> DeleteChatHistoryResult`
Deletes local chat history up to the provided message id.

Returned object:
- `DeleteChatHistoryResult.chat_update`

Common nested payload:
- `chat_update.object_guid`
- `chat_update.chat.last_message`
- `chat_update.chat.last_message_id`
- `chat_update.chat.last_deleted_mid`

### `await app.send_chat_activity(object_guid, activity="Typing", *, peer=None) -> Empty`
Sends a transient chat activity state for the target chat.

Input:
- `object_guid` can be passed directly or via `peer=`
- `activity` is sent exactly as provided, for example `Typing`

Returned object:
- `Empty`

Notes:
- this method is currently available only for authenticated user sessions, not token-based bot sessions
- use `await app.send_typing(object_guid, *, peer=None)` as a convenience alias for `activity="Typing"`

### `await app.block_user(object_guid) -> RawObject`
Current status:
- implemented
- still returned as `RawObject`

### `await app.unblock_user(object_guid) -> RawObject`
Current status:
- implemented
- still returned as `RawObject`

## Websocket Updates

### `await app.receive_socket_update(timeout: float | None = None) -> SocketUpdates`
Waits for the next websocket messenger update and returns a typed update object.

Returned object:
- `SocketUpdates.chat_updates`
- `SocketUpdates.message_updates`
- `SocketUpdates.show_notifications`
- `SocketUpdates.user_guid`

Nested objects:
- `SocketChatUpdate`
- `SocketMessageUpdate`
- `ShowNotification`
- `NotificationMessageData`

Message-specific nested structures currently parsed:
- `message.forwarded_from`
- `message.file_inline`
- `message.sticker`
- `message.rubino_post_data`
- `message.live_data`

## Callbacks

### `@app.on_message(filter=None)`
Registers a message handler for websocket `message_updates`.

Example:

```python
from rubigram import Client, filters

app = Client("my_account")


@app.on_message(filters.text & filters.private & ~filters.me)
async def handler(client, message):
    print(message.text)
    await message.reply("received")
```

### `await app.idle() -> None`
Keeps the process alive while the update listener is running.

## Message Convenience Methods

`Message` objects currently include:

### `await message.reply(text: str, parse_mode: str | None = None) -> Any`
Uses:
- `message.object_guid`
- `message.message_id`

Internally calls:
- `client.send_message(..., reply_to_message_id=message.message_id)`

### `message.chat_id`
Alias for:
- `message.object_guid`

## Filter System

Available from:

```python
from rubigram import filters
```

Current filters include:
- `filters.all`
- `filters.me`
- `filters.private`
- `filters.bot`
- `filters.group`
- `filters.channel`
- `filters.service`
- `filters.text`
- `filters.media`
- `filters.photo`
- `filters.video`
- `filters.voice`
- `filters.music`
- `filters.gif`
- `filters.document`
- `filters.sticker`
- `filters.rubino`
- `filters.live`
- `filters.caption`
- `filters.poll`
- `filters.quiz`
- `filters.event`
- `filters.new`
- `filters.edited`
- `filters.deleted`
- `filters.replied`
- `filters.forwarded`
- `filters.forwarded_no_link`
- `filters.bold`
- `filters.mono`
- `filters.italic`
- `filters.mention`
- `filters.member_added`
- `filters.member_joined`
- `filters.member_left`
- `filters.member_removed`
- `filters.message_pinned`
- `filters.voice_chat_started`
- `filters.voice_chat_finished`
- `filters.regex(pattern)`
- `filters.group_link`
- `filters.channel_link`

Composition is supported:

```python
filters.text & filters.private
filters.photo | filters.video
~filters.me
```

## Notes

Methods that still return `RawObject` are implemented and usable, but their result schema has not yet been locked into a dedicated typed model.

That is the current boundary between:
- stable typed API
- raw-but-usable API

