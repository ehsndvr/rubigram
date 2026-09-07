# Method reference

Generated from the docstrings of `rubigram.Client` (run `python tools/gen_method_reference.py`).

Tags: `[HTTP]` encrypted RPC over HTTPS, `[WS]` needs the socket (Transport.WS), `[both]` works in either mode, `[bot]` Bot API (`Client(token=...)`).
Every method is `async` unless it is marked *sync*. Any `object_guid` argument also accepts a `Peer`, a typed object with a guid, or `peer=`.

## Lifecycle and handlers

`Client` itself: construction, start/stop, transport switching and handler registration.

| Method | Transport | Description |
|---|---|---|
| `add_handler(handler, group=0)` *(sync)* | [both] | Register a :class:`~rubigram.handlers.Handler` instance in ``group``. |
| `from_session_string(cls, name, session_string, **kwargs)` *(sync)* | [both] | Create an in-memory client from a portable session string. |
| `on_activity(filters=None, group=0)` *(sync)* | [WS] | Register a handler for typing/recording/uploading activities (``show_activities``). |
| `on_callback_query(filters=None, group=0)` *(sync)* | [bot] | Register a handler for bot button presses (messages carrying ``aux_data.button_id``). |
| `on_chat_update(filters=None, group=0)` *(sync)* | [WS] | Register a handler for chat list changes (``chat_updates``: unread counts, pins, new chats). |
| `on_deleted_message(filters=None, group=0)` *(sync)* | [both] | Register a handler for deleted messages (``action == "Delete"``; bot ``RemovedMessage``). |
| `on_draft_update(filters=None, group=0)` *(sync)* | [WS] | Register a handler for draft changes (``draft_message_updates``). |
| `on_edited_message(filters=None, group=0)` *(sync)* | [both] | Register a handler for edited messages (``action == "Edit"``; bot ``UpdatedMessage``). |
| `on_inline_message(filters=None, group=0)` *(sync)* | [bot] | Register a handler for bot inline messages delivered by webhooks. |
| `on_message(filters=None, group=0)` *(sync)* | [both] | Register a handler for new messages (user sessions and bots). |
| `on_notification(filters=None, group=0)` *(sync)* | [WS] | Register a handler for ``show_notifications`` entries. |
| `on_raw_update(filters=None, group=0)` *(sync)* | [both] | Register a handler that receives every decrypted frame (:class:`~rubigram.types.Updates`) or bot update. |
| `remove_handler(handler, group=None)` *(sync)* | [both] | Unregister a handler; returns whether it was found. |
| `run(coroutine=None)` *(sync)* | [both] | Start the client, run ``coroutine`` (or idle until Ctrl-C), then stop. |
| `set_transport(mode)` *(sync)* | [both] | Switch the update delivery mode; the socket is opened or closed lazily. |
| `start()` | [both] | Open the session, discover DCs, log in if needed and connect. |
| `stop()` | [both] | Close every transport and the storage. |
| `use_transport(mode)` *(sync)* | [both] | Temporarily switch the transport mode for the duration of the block. |

## Authentication

Phone login, device registration, logout.

| Method | Transport | Description |
|---|---|---|
| `authorize()` | [HTTP] | rubigram 0.1 name of :meth:`login` (bots just persist their token). |
| `get_time()` | [HTTP] | Server time (``getTime``). |
| `login(phone_number=None, *, code=None, code_callback=None, password=None, max_attempts=3, first_name=None, last_name=None)` | [HTTP] | Full phone login: ``sendCode`` → ``signIn`` (→ ``signUp`` for new accounts). |
| `logout()` | [HTTP] | ``logout`` and forget the stored auth. |
| `register_device(force=False)` | [HTTP] | ``registerDevice`` with the web-client payload; skipped when already registered for this app version. |
| `send_code(phone_number, *, send_type='SMS', pass_key=None)` | [HTTP] | Ask Rubika to send a login code (``sendCode``). |
| `sign_in(phone_number, phone_code_hash, phone_code)` | [HTTP] | Confirm the code (``signIn``); on success the session ``auth`` is stored. |
| `sign_up(first_name, last_name='')` | [HTTP] | Register a new account (``signUp``); unverified against the current server. |
| `unregister_device(device=None)` | [HTTP] | ``unregisterDevice`` (sent unencrypted like the web client). |

## Sessions

Active devices and the portable session string.

| Method | Transport | Description |
|---|---|---|
| `action_on_unconfirmed_session(unconfirmed_session_key, action)` | [HTTP] | Accept or reject a login attempt from another device (``actionOnUnconfirmedSession``). |
| `confirm_session(unconfirmed_session_key)` | [HTTP] | Accept a login attempt from another device. |
| `export_session_dict()` | [HTTP] | The session as a plain dict (``auth``, ``user_guid``, keys, DC configuration). |
| `export_session_string()` | [HTTP] | Portable session string (contains the auth key; treat it as a secret). |
| `get_my_sessions()` | [HTTP] | Active sessions of the account (``getMySessions``). |
| `get_unconfirmed_sessions()` | [HTTP] | Login attempts waiting for confirmation (``getUnconfirmedSessions``). |
| `import_session_string(session_string)` | [HTTP] | Load a session string into this client's storage. |
| `reject_session(unconfirmed_session_key)` | [HTTP] | Reject a login attempt from another device. |
| `terminate_other_sessions()` | [HTTP] | Log every other device out (``terminateOtherSessions``). |
| `terminate_session(session_key)` | [HTTP] | Log another device out (``terminateSession``). |

## Users and contacts

| Method | Transport | Description |
|---|---|---|
| `add_contact(phone, first_name, last_name='')` | [HTTP] | Add a phone number to the address book (``addAddressBook``). |
| `block_user(object_guid=None, *, peer=None)` | [HTTP] | Block a user (``setBlockUser`` / ``Block``). |
| `check_username(username)` | [HTTP] | Whether a username is taken (``checkUserUsername``). |
| `delete_contact(user_guid)` | [HTTP] | ``deleteContact``. |
| `get_abs_objects(object_guids)` | [HTTP] | Minimal info (title, avatar, type) for up to 50 guids (``getAbsObjects``). |
| `get_avatars(object_guid=None, *, peer=None)` | [HTTP] | ``getAvatars`` of a user, group or channel. |
| `get_blocked_users(start_id=None)` | [HTTP] | ``getBlockedUsers``. |
| `get_common_groups(user_guid)` | [HTTP] | Groups shared with a user (``getCommonGroups``). |
| `get_contacts(start_id=None)` | [HTTP] | A page of contacts (``getContacts``); pass ``next_start_id`` to continue. |
| `get_contacts_last_online(user_guids)` | [HTTP] | ``getContactsLastOnline``. |
| `get_contacts_updates(state=None)` | [HTTP] | ``getContactsUpdates`` since ``state`` (defaults to the stored contacts state). |
| `get_me()` | [HTTP] [bot] | The logged-in user (``getUserInfo`` on the stored guid) or the bot profile. |
| `get_object_by_username(username)` | [HTTP] | Resolve a ``@username`` to a user/group/channel/bot (``getObjectByUsername``). |
| `get_profile_link_items(object_guid=None, *, peer=None)` | [HTTP] | ``getProfileLinkItems``. |
| `get_user_info(user_guid)` | [HTTP] | ``getUserInfo``. |
| `report_object(object_guid, report_type, *, description=None, message_id=None, report_type_object=None)` | [HTTP] | ``reportObject``. |
| `reset_contacts()` | [HTTP] | ``resetContacts``. |
| `search_global(search_text, filter_types=())` | [HTTP] | Alias of `search_global_objects`. Global search of users, groups, channels and bots (``searchGlobalObjects``). |
| `search_global_objects(search_text, filter_types=())` | [HTTP] | Global search of users, groups, channels and bots (``searchGlobalObjects``). |
| `set_ask_spam_action(object_guid, action)` | [HTTP] | ``setAskSpamAction``. |
| `set_block_user(user_guid, action='Block')` | [HTTP] | ``setBlockUser`` with ``Block`` / ``Unblock``. |
| `unblock_user(object_guid=None, *, peer=None)` | [HTTP] | Unblock a user (``setBlockUser`` / ``Unblock``). |
| `update_profile(*, first_name=None, last_name=None, bio=None, birth_date=None)` | [HTTP] | Change name, bio or birth date (``updateProfile``). |
| `update_username(username)` | [HTTP] | ``updateUsername``. |

## Chats

Dialog list, read state, chat actions.

| Method | Transport | Description |
|---|---|---|
| `archive_chat(object_guid)` | [HTTP] | Move a chat to the archive (``setActionChat`` / ``Archive``). |
| `click_message_url(object_guid, message_id, link_url)` | [HTTP] | Report a click on a link inside a message (``clickMessageUrl``). |
| `delete_bot_chat(bot_guid, last_deleted_message_id='0')` | [HTTP] | Delete the chat with a bot (``deleteBotChat``). |
| `delete_chat_history(object_guid=None, last_message_id='', *, peer=None)` | [HTTP] | Clear the local history up to ``last_message_id`` (``deleteChatHistory``). |
| `delete_no_access_group_chat(group_guid)` | [HTTP] | Remove a group you can no longer access from the list (``deleteNoAccessGroupChat``). |
| `delete_service_chat(service_guid, last_deleted_message_id='0')` | [HTTP] | Delete a service chat (``deleteServiceChat``). |
| `delete_user_chat(user_guid, last_deleted_message_id='0')` | [HTTP] | Delete a private chat (``deleteUserChat``). |
| `get_chat(object_guid=None, *, peer=None)` | [HTTP] [bot] | One dialog (``getChatsByID``); for bots the Bot API ``getChat``. |
| `get_chat_ads(state=None)` | [HTTP] | Sponsored entries for the chat list (``getChatAds``). |
| `get_chats(start_id=None)` | [HTTP] | One page of the dialog list (``getChats``); pass ``next_start_id`` to continue. |
| `get_chats_by_id(object_guids)` | [HTTP] | ``getChatsByID``. |
| `get_link_from_app_url(app_url)` | [HTTP] | Resolve an in-app URL (``getLinkFromAppUrl``). |
| `get_link_object(share_string)` | [HTTP] | Resolve a ``rubika.ir`` share string (``getlinkObject``). |
| `get_message_share_url(object_guid, message_id)` | [HTTP] | Public link of a channel message (``getMessageShareUrl``). |
| `get_related_objects(object_guid, start_id=None)` | [HTTP] | Related chats suggested for an object (``getRelatedObjects``). |
| `iter_chats(limit=None)` *(sync)* | [HTTP] | Iterate over every dialog, paging with ``getChats``. |
| `mute_chat(object_guid, *, duration=None)` | [HTTP] | Mute a chat, optionally for ``duration`` seconds (``setActionChat`` / ``Mute``). |
| `pin_chat(object_guid)` | [HTTP] | Pin a chat to the top of the list (``setActionChat`` / ``Pin``). |
| `seen(object_guid, message_id)` | [HTTP] | Mark one chat as read up to ``message_id``. |
| `seen_chats(seen_list)` | [HTTP] | Mark messages as read: ``{object_guid: last_seen_message_id}`` (``seenChats``). |
| `set_action_chat(object_guid, action, *, duration=None)` | [HTTP] | ``setActionChat`` (``Mute``/``Unmute``/``Pin``/``Unpin``/``Archive``/``Unarchive``). |
| `set_chat_use_time(object_guid, time)` | [HTTP] | Record when a chat was last opened (``setChatUseTime``). |
| `unarchive_chat(object_guid)` | [HTTP] | Move a chat out of the archive (``setActionChat`` / ``Unarchive``). |
| `unmute_chat(object_guid)` | [HTTP] | Unmute a chat (``setActionChat`` / ``Unmute``). |
| `unpin_chat(object_guid)` | [HTTP] | Unpin a chat (``setActionChat`` / ``Unpin``). |

## Messages

Sending, editing, history, search, reactions, polls, drafts.

| Method | Transport | Description |
|---|---|---|
| `action_on_message_reaction(object_guid, message_id, reaction_id, action='Add')` | [HTTP] | ``actionOnMessageReaction`` (``Add`` / ``Remove``). |
| `clear_drafts(object_guid=None)` | [HTTP] | Clear one chat's draft or every draft (``clearDrafts``). |
| `create_poll(object_guid, question, options, *, poll_type='Regular', is_anonymous=True, allows_multiple_answers=False, correct_option_index=None, explanation=None)` | [HTTP] [bot] | Create a poll or quiz (``createPoll``; Bot API ``sendPoll`` for bots). |
| `delete_message(object_guid=None, message_id='', *, delete_type='Global', peer=None)` | [HTTP] [bot] | Delete one message (``deleteMessages``; Bot API ``deleteMessage`` for bots). |
| `delete_messages(object_guid, message_ids, *, delete_type='Global', peer=None)` | [HTTP] | Delete messages for everyone (``Global``) or locally (``Local``) (``deleteMessages``). |
| `edit_message(object_guid=None, message_id='', text='', *, parse_mode=None, entities=None, peer=None)` | [HTTP] [bot] | Edit the text of a message (``editMessage``). |
| `forward_message(from_object_guid, message_id, to_object_guid, *, disable_notification=False)` | [HTTP] [bot] | Forward one message (user sessions and bots). |
| `forward_messages(from_object_guid, to_object_guid, message_ids)` | [HTTP] | ``forwardMessages``. |
| `get_all_drafts()` | [HTTP] | Every unsent draft (``getAllDrafts``). |
| `get_available_reactions()` | [HTTP] | ``getAvailableReactions``. |
| `get_chat_reaction(object_guid)` | [HTTP] | Reactions allowed in a chat (``getChatReaction``). |
| `get_history(object_guid=None, offset=None, limit=50, *, peer=None)` | [HTTP] | rubigram 0.1 name of :meth:`get_messages` (``offset`` is treated as ``max_id``). |
| `get_message(object_guid, message_id)` | [HTTP] | One message by id, or ``None``. |
| `get_message_reactions(object_guid, message_id, *, reaction_id=None, start_id=None)` | [HTTP] | Who reacted to a message, optionally for one ``reaction_id`` (``getMessageReactions``). |
| `get_message_read_participants(group_guid, message_id)` | [HTTP] | Who read a group message (``getGroupMessageReadParticipants``). |
| `get_messages(object_guid=None, *, max_id=None, min_id=None, sort='FromMax', limit=20, filter_type=None, peer=None)` | [HTTP] | A page of history (``getMessages``): ``max_id`` + ``FromMax`` goes backwards. |
| `get_messages_by_id(object_guid, message_ids)` | [HTTP] | ``getMessagesByID``. |
| `get_messages_interval(object_guid, middle_message_id, *, filter_type=None)` | [HTTP] | Messages around ``middle_message_id`` (``getMessagesInterval``). |
| `get_poll_option_voters(poll_id, selection_index, start_id=None)` | [HTTP] | Voters of one poll option (``getPollOptionVoters``). |
| `get_poll_status(poll_id)` | [HTTP] | Current votes of a poll (``getPollStatus``). |
| `get_transcription(message_id, transcription_id)` | [HTTP] | Fetch a voice transcription started with :meth:`transcribe_voice` (``getTranscription``). |
| `iter_messages(object_guid, *, limit=None, filter_type=None, page_size=20)` *(sync)* | [HTTP] | Walk a chat history from the newest message backwards. |
| `pin_message(object_guid, message_id)` | [HTTP] | ``setPinMessage`` / ``Pin``. |
| `react(object_guid, message_id, reaction_id)` | [HTTP] | Add a reaction (see :meth:`get_available_reactions` for ids). |
| `search_chat_messages(object_guid, search_text, *, search_type='Text')` | [HTTP] | ``searchChatMessages`` (returns message ids). |
| `search_global_messages(search_text, *, search_type='Text', start_id=None)` | [HTTP] | ``searchGlobalMessages``. |
| `send_chat_activity(object_guid=None, activity='Typing', *, peer=None)` | [HTTP] | ``sendChatActivity`` (``Typing`` / ``Recording`` / ``Uploading``); never retried. |
| `send_location(object_guid, latitude, longitude, *, reply_to_message_id=None, **bot_kwargs)` | [HTTP] [bot] | Send a location. |
| `send_message(object_guid=None, text=None, rnd=None, *, parse_mode=None, entities=None, reply_to_message_id=None, file_inline=None, metadata=None, sticker=None, location=None, aux_data=None, is_mute=None, peer=None, chat_keypad=None, inline_keypad=None, chat_keypad_type=None, disable_notification=False)` | [HTTP] [bot] | Send a text (or an already uploaded ``file_inline``) message. |
| `send_poll(object_guid, question, options, **kwargs)` | [HTTP] [bot] | Alias of :meth:`create_poll` (Bot API name). |
| `send_typing(object_guid=None, *, peer=None)` | [HTTP] | Show the *typing…* activity in a chat (``sendChatActivity`` / ``Typing``). |
| `transcribe_voice(object_guid, message_id)` | [HTTP] | Ask the server to transcribe a voice message (``transcribeVoice``). |
| `unpin_message(object_guid, message_id)` | [HTTP] | ``setPinMessage`` / ``Unpin``. |
| `unreact(object_guid, message_id, reaction_id)` | [HTTP] | Remove your reaction from a message (``actionOnMessageReaction`` / ``Remove``). |
| `vote_poll(poll_id, selection_index)` | [HTTP] | Vote for ``selection_index`` in a poll (``votePoll``). |

## Media

Uploads, downloads, media messages, avatars, wallpapers.

| Method | Transport | Description |
|---|---|---|
| `add_set_wallpaper(thumbnail_file_id, main_file_id)` | [HTTP] | Upload ids of a custom chat wallpaper (``addSetWallpaper``). |
| `delete_avatar(object_guid, avatar_id)` | [HTTP] | Delete one avatar of a user, group or channel (``deleteAvatar``). |
| `download_file(file, path=None, *, in_memory=False, file_name=None, progress=None, progress_args=())` | [HTTP] [bot] | Download a message/file/avatar object; returns the path or the bytes. |
| `download_url(url, path=None, *, in_memory=False, file_name=None, progress=None, progress_args=())` | [HTTP] | Download a public URL (Rubino media, CDN) to disk or memory. |
| `get_wallpapers()` | [HTTP] | Built-in and custom chat wallpapers (``getWallpapers``). |
| `request_send_file(file_name=None, size=None, mime=None, *, type=None)` | [HTTP] [bot] | ``requestSendFile``: an upload slot (``upload_url``, ``id``, ``dc_id``, ``access_hash_send``). |
| `reset_wallpapers()` | [HTTP] | Remove custom wallpapers (``resetWallpapers``). |
| `send_document(object_guid=None, path=None, *, text=None, **kwargs)` | [HTTP] [bot] | Send any file as a document (``File`` media type). |
| `send_file_message(object_guid=None, path=None, *, text=None, **kwargs)` | [HTTP] [bot] | Alias of `send_document`. Send any file as a document (``File`` media type). |
| `send_gif(object_guid=None, path=None, *, text=None, width=None, height=None, duration_ms=None, **kwargs)` | [HTTP] [bot] | Send an animated GIF. |
| `send_media(object_guid=None, path=None, *, media_type='File', text=None, data=None, file_name=None, mime=None, rnd=None, reply_to_message_id=None, parse_mode=None, width=None, height=None, duration_ms=None, thumb_inline=None, is_round=None, is_spoil=None, music_performer=None, extra_file_inline=None, progress=None, progress_args=(), peer=None)` | [HTTP] [bot] | Upload ``path`` (or ``data``) and send it as ``media_type`` (``File``/``Image``/``Video``/``Voice``/``Music``/``Gif``). |
| `send_music(object_guid=None, path=None, *, duration_ms=None, music_performer=None, text=None, **kwargs)` | [HTTP] [bot] | Send an audio track with an optional performer name. |
| `send_photo(object_guid=None, path=None, *, text=None, width=None, height=None, is_spoil=None, **kwargs)` | [HTTP] [bot] | Send an image. |
| `send_uploaded_media(*, object_guid=None, path, media_type, **kwargs)` | [HTTP] | rubigram 0.1 name of :meth:`send_media`. |
| `send_video(object_guid=None, path=None, *, text=None, duration_ms=None, width=None, height=None, is_round=False, is_spoil=False, thumb_inline=None, **kwargs)` | [HTTP] [bot] | Send a video (``duration_ms``/``width``/``height`` are what the apps display). |
| `send_voice(object_guid=None, path=None, *, duration_ms=None, text=None, **kwargs)` | [HTTP] [bot] | Send a voice note; the duration is read from OGG/Opus files when omitted. |
| `set_channel_photo(object_guid=None, path='', *, peer=None, **kwargs)` | [HTTP] | Alias of `set_group_photo`. Set the avatar of a group (``uploadAvatar``). |
| `set_group_photo(object_guid=None, path='', *, peer=None, **kwargs)` | [HTTP] | Set the avatar of a group (``uploadAvatar``). |
| `set_profile_photo(path, **kwargs)` | [HTTP] | Set your own profile picture (``uploadAvatar`` on the logged-in guid). |
| `upload_avatar(object_guid, path, *, thumbnail_path=None, progress=None, progress_args=())` | [HTTP] | Set the avatar of a user (own guid), group or channel (``uploadAvatar``). |
| `upload_file(path=None, *, data=None, file_name=None, mime=None, descriptor=None, upload_url=None, progress=None, progress_args=())` | [HTTP] [bot] | Upload a file and return its :class:`~rubigram.types.UploadDescriptor` (bots: the ``file_id``). |
| `upload_group_avatar(object_guid=None, path='', *, peer=None, **kwargs)` | [HTTP] | rubigram 0.1 name of :meth:`set_group_photo`. |

## Groups

| Method | Transport | Description |
|---|---|---|
| `add_group(title, member_guids=None)` | [HTTP] | Create a group (``addGroup``). |
| `add_group_members(object_guid=None, member_guids=None, *, peer=None)` | [HTTP] | ``addGroupMembers``. |
| `ban_group_member(object_guid=None, member_guid=None, *, peer=None)` | [HTTP] | ``banGroupMember`` / ``Set``. |
| `cancel_change_object_owner(object_guid)` | [HTTP] | Cancel a pending ownership transfer (``cancelChangeObjectOwner``). |
| `create_group(title, member_guids=None)` | [HTTP] | Alias of `add_group`. Create a group (``addGroup``). |
| `edit_group_info(object_guid=None, *, peer=None, title=None, description=None, slow_mode=None, chat_history_for_new_members=None, event_messages=None, chat_reaction_setting=None, sign_messages=None)` | [HTTP] | Change group settings (``editGroupInfo``); only the given fields are sent. |
| `get_banned_group_members(object_guid=None, *, peer=None, start_id=None, search_text=None)` | [HTTP] | Banned members of a group, one page at a time (``getBannedGroupMembers``). |
| `get_group_admin_access_list(object_guid, member_guid)` | [HTTP] | The admin rights of one member (``getGroupAdminAccessList``). |
| `get_group_admin_members(object_guid=None, *, peer=None, start_id=None, search_text=None)` | [HTTP] | Admins of a group (``getGroupAdminMembers``). |
| `get_group_all_members(object_guid=None, *, peer=None, start_id=None, search_text=None)` | [HTTP] | One page of members (``getGroupAllMembers``); ``next_start_id`` continues. |
| `get_group_default_access(object_guid=None, *, peer=None)` | [HTTP] | Permissions of ordinary members (``getGroupDefaultAccess``). |
| `get_group_info(object_guid=None, *, peer=None)` | [HTTP] | ``getGroupInfo``. |
| `get_group_link(object_guid=None, *, peer=None)` | [HTTP] | The primary join link of a group (``getGroupLink``). |
| `get_group_mention_list(object_guid, search_mention=None)` | [HTTP] | Members that can be mentioned, filtered by ``search_mention`` (``getGroupMentionList``). |
| `get_group_online_count(object_guid)` | [HTTP] | How many members are online (``getGroupOnlineCount``). |
| `get_group_preview(link)` | [HTTP] | Preview a group before joining (``groupPreviewByJoinLink``). |
| `get_pending_object_owner(object_guid=None, *, peer=None)` | [HTTP] | The pending ownership transfer, if any (``getPendingObjectOwner``). |
| `group_preview_by_join_link(link)` | [HTTP] | Alias of `get_group_preview`. Preview a group before joining (``groupPreviewByJoinLink``). |
| `join_group(link)` | [HTTP] | Join by ``rubika.ir/joing/<hash>`` link or bare hash (``joinGroup``). |
| `leave_group(object_guid)` | [HTTP] | ``leaveGroup``. |
| `remove_group(object_guid=None, *, peer=None)` | [HTTP] | Delete a group you own (``removeGroup``). |
| `reply_request_object_owner(object_guid, action)` | [HTTP] | Accept or reject an ownership transfer offered to you (``replyRequestObjectOwner``). |
| `request_change_object_owner(object_guid=None, new_owner_user_guid=None, *, peer=None)` | [HTTP] | Offer the ownership of a group or channel to another member (``requestChangeObjectOwner``). |
| `set_group_admin(object_guid=None, member_guid=None, access_list=(), *, peer=None)` | [HTTP] | Promote a member (``setGroupAdmin`` / ``SetAdmin``) with a :class:`~rubigram.enums.GroupAdminAccess` list. |
| `set_group_default_access(object_guid=None, access_list=(), *, peer=None)` | [HTTP] | Set the permissions of ordinary members with :class:`~rubigram.enums.GroupDefaultAccess` values (``setGroupDefaultAccess``). |
| `set_group_event_messages(object_guid=None, enabled=True, *, peer=None)` | [HTTP] | Show or hide join/leave event messages (``editGroupInfo`` / ``event_messages``). |
| `set_group_history_for_new_members(object_guid=None, value='Visible', *, peer=None)` | [HTTP] | Whether new members see the old history (``editGroupInfo`` / ``chat_history_for_new_members``). |
| `set_group_link(object_guid)` | [HTTP] | Regenerate the primary join link (``setGroupLink``). |
| `set_group_reaction_setting(object_guid=None, *, peer=None, reaction_type='All', selected_reactions=None)` | [HTTP] | Configure which reactions the group allows (``editGroupInfo`` / ``chat_reaction_setting``). |
| `set_group_reactions_all(object_guid=None, *, peer=None)` | [HTTP] | Allow every reaction in the group. |
| `set_group_reactions_disabled(object_guid=None, *, peer=None)` | [HTTP] | Disable reactions in the group. |
| `set_group_reactions_selected(object_guid=None, selected_reactions=None, *, peer=None)` | [HTTP] | Allow only the given reaction ids in the group. |
| `set_group_slow_mode(object_guid=None, seconds=0, *, peer=None)` | [HTTP] | Set the slow mode delay in seconds, ``0`` to disable (``editGroupInfo`` / ``slow_mode``). |
| `set_group_title(object_guid, title, *, description=None)` | [HTTP] | Rename a group and optionally change its description (``editGroupInfo``). |
| `unban_group_member(object_guid=None, member_guid=None, *, peer=None)` | [HTTP] | Lift a group ban (``banGroupMember`` / ``Unset``). |
| `unset_group_admin(object_guid=None, member_guid=None, *, peer=None)` | [HTTP] | Demote a group admin (``setGroupAdmin`` / ``UnsetAdmin``). |
| `update_group_admin_access(object_guid=None, member_guid=None, access_list=(), *, peer=None)` | [HTTP] | Alias of `set_group_admin`. Promote a member (``setGroupAdmin`` / ``SetAdmin``) with a :class:`~rubigram.enums.GroupAdminAccess` list. |

## Channels

| Method | Transport | Description |
|---|---|---|
| `add_channel(title, description='', channel_type='Private', member_guids=None, *, thumbnail_file_id=None, main_file_id=None)` | [HTTP] | Create a channel (``addChannel``); avatar ids are optional. |
| `add_channel_members(object_guid=None, member_guids=None, *, peer=None)` | [HTTP] | Add users to a channel (``addChannelMembers``). |
| `ban_channel_member(object_guid, member_guid)` | [HTTP] | Ban a member from a channel (``banChannelMember`` / ``Set``). |
| `channel_preview_by_join_link(link)` | [HTTP] | Alias of `get_channel_preview`. Preview a private channel before joining (``channelPreviewByJoinLink``). |
| `check_channel_username(username)` | [HTTP] | Whether a channel username is free (``checkChannelUsername``). |
| `create_channel(title, description='', channel_type='Private', member_guids=None, *, thumbnail_file_id=None, main_file_id=None)` | [HTTP] | Alias of `add_channel`. Create a channel (``addChannel``); avatar ids are optional. |
| `edit_channel_info(object_guid=None, *, peer=None, title=None, description=None, channel_type=None, sign_messages=None, chat_reaction_setting=None)` | [HTTP] | Change channel settings (``editChannelInfo``); only the given fields are sent. |
| `get_banned_channel_members(object_guid=None, *, peer=None, start_id=None, search_text=None)` | [HTTP] | Banned members of a channel, one page at a time (``getBannedChannelMembers``). |
| `get_channel_admin_access_list(object_guid, member_guid)` | [HTTP] | The admin rights of one member (``getChannelAdminAccessList``). |
| `get_channel_admin_members(object_guid=None, *, peer=None, start_id=None, search_text=None)` | [HTTP] | Admins of a channel (``getChannelAdminMembers``). |
| `get_channel_all_members(object_guid=None, *, peer=None, start_id=None, search_text=None)` | [HTTP] | Members of a channel, one page at a time (``getChannelAllMembers``); ``next_start_id`` continues. |
| `get_channel_info(object_guid=None, *, peer=None)` | [HTTP] | ``getChannelInfo``. |
| `get_channel_link(object_guid=None, *, peer=None)` | [HTTP] | The primary join link (``getChannelLink``). |
| `get_channel_preview(link)` | [HTTP] | Preview a private channel before joining (``channelPreviewByJoinLink``). |
| `join_channel(channel)` | [HTTP] | Join a public channel by guid, or a private one by ``rubika.ir/joinc/<hash>`` link. |
| `join_channel_action(object_guid, action)` | [HTTP] | ``joinChannelAction`` (``Join`` / ``Leave`` / ``Remove``). |
| `join_channel_by_link(link)` | [HTTP] | Join a private channel by its ``rubika.ir/joinc/<hash>`` link (``joinChannelByLink``). |
| `leave_channel(object_guid)` | [HTTP] | Leave a channel (``joinChannelAction`` / ``Leave``). |
| `remove_channel(object_guid)` | [HTTP] | Delete a channel you own (``removeChannel``). |
| `set_channel_admin(object_guid=None, member_guid=None, access_list=(), *, peer=None)` | [HTTP] | Promote a member with a list of :class:`~rubigram.enums.ChannelAdminAccess` rights (``setChannelAdmin`` / ``SetAdmin``). |
| `set_channel_link(object_guid)` | [HTTP] | Regenerate the primary join link (``setChannelLink``). |
| `unban_channel_member(object_guid, member_guid)` | [HTTP] | Lift a channel ban (``banChannelMember`` / ``Unset``). |
| `unset_channel_admin(object_guid=None, member_guid=None, *, peer=None)` | [HTTP] | Demote an admin (``setChannelAdmin`` / ``UnsetAdmin``). |
| `update_channel_admin_access(object_guid=None, member_guid=None, access_list=(), *, peer=None)` | [HTTP] | Alias of `set_channel_admin`. Promote a member with a list of :class:`~rubigram.enums.ChannelAdminAccess` rights (``setChannelAdmin`` / ``SetAdmin``). |
| `update_channel_username(object_guid, username)` | [HTTP] | Set the public username of a channel (``updateChannelUsername``). |

## Join links

| Method | Transport | Description |
|---|---|---|
| `accept_join_request(object_guid, user_guid)` | [HTTP] | Approve a pending join request (``actionOnJoinRequest`` / ``Accept``). |
| `action_on_join_request(object_guid, user_guid, action)` | [HTTP] | ``actionOnJoinRequest`` (``Accept`` / ``Reject``). |
| `create_join_link(object_guid=None, title='', *, peer=None, request_needed=False, expire_time=0, usage_limit=0)` | [HTTP] | ``createJoinLink``. |
| `delete_revoked_join_link(object_guid, join_link=None)` | [HTTP] | Delete one revoked link, or all of them when ``join_link`` is omitted (``deleteRevokedJoinLink``). |
| `edit_join_link(object_guid, join_link, *, title=None, request_needed=None, expire_time=None, usage_limit=None)` | [HTTP] | ``editJoinLink``; only the given fields are updated. |
| `get_join_link_user_joined(object_guid, join_link, start_id=None)` | [HTTP] | Users who joined through a link (``getJoinLinkUserJoined``). |
| `get_join_links(object_guid=None, *, peer=None, creator_guid=None)` | [HTTP] | ``getJoinLinks`` of a group or channel. |
| `get_join_requests(object_guid, start_id=None)` | [HTTP] | Pending join requests of a group or channel (``getJoinRequests``). |
| `reject_join_request(object_guid, user_guid)` | [HTTP] | Reject a pending join request (``actionOnJoinRequest`` / ``Reject``). |
| `revoke_join_link(object_guid, join_link)` | [HTTP] | Revoke an extra join link (``revokeJoinLink``). |

## Stickers, GIFs and folders

| Method | Transport | Description |
|---|---|---|
| `action_on_sticker_set(sticker_set_id, action)` | [HTTP] | ``actionOnStickerSet`` (``Add`` / ``Remove``). |
| `add_folder(name, *, include_chat_types=None, exclude_chat_types=None, include_object_guids=None, exclude_object_guids=None, is_add_to_top=None)` | [HTTP] | Create a chat folder (``addFolder``). |
| `add_sticker_set(sticker_set_id)` | [HTTP] | Install a sticker set (``actionOnStickerSet`` / ``Add``). |
| `add_to_my_gif_set(object_guid, message_id)` | [HTTP] | Save a GIF message to your GIF set (``addToMyGifSet``). |
| `delete_folder(folder_id)` | [HTTP] | Delete a chat folder (``deleteFolder``). |
| `edit_folder(folder_id, *, name=None, include_chat_types=None, exclude_chat_types=None, include_object_guids=None, exclude_object_guids=None)` | [HTTP] | Change a chat folder; only the given fields are sent (``editFolder``). |
| `get_folders(last_state=None)` | [HTTP] | Chat folders (``getFolders``); the state is persisted. |
| `get_my_archived_sticker_sets(*, search_text=None, start_id=None)` | [HTTP] | Archived sticker sets (``getMyArchivedStickerSets``). |
| `get_my_gif_set()` | [HTTP] | Saved GIFs (``getMyGifSet``). |
| `get_my_sticker_sets()` | [HTTP] | Installed sticker sets (``getMyStickerSets``). |
| `get_sticker_set_by_id(sticker_set_id)` | [HTTP] | One sticker set with its stickers (``getStickerSetByID``). |
| `get_sticker_setting()` | [HTTP] | Sticker suggestion settings (``getStickerSetting``). |
| `get_stickers_by_emoji(emoji_character, *, suggest_by='All')` | [HTTP] | Stickers matching an emoji (``getStickersByEmoji``). |
| `get_stickers_by_set_ids(sticker_set_ids)` | [HTTP] | Several sticker sets at once (``getStickersBySetIDs``). |
| `get_suggested_folders()` | [HTTP] | Folder suggestions (``getSuggestedFolders``). |
| `get_trend_sticker_sets(start_id=None)` | [HTTP] | Trending sticker sets (``getTrendStickerSets``). |
| `remove_sticker_set(sticker_set_id)` | [HTTP] | Uninstall a sticker set (``actionOnStickerSet`` / ``Remove``). |
| `search_stickers(search_text, start_id=None)` | [HTTP] | Search sticker sets by text (``searchStickers``). |
| `send_sticker(object_guid, sticker, *, reply_to_message_id=None)` | [HTTP] | Send a sticker object (from a sticker set or a received message). |
| `set_pin_chat_in_folder(folder_id, object_guid, action='Pin')` | [HTTP] | Pin or unpin a chat inside a folder (``setPinChatInFolder``). |

## Settings and security

| Method | Transport | Description |
|---|---|---|
| `abort_set_recovery_email(password)` | [HTTP] | Cancel a pending recovery e-mail change (``abortSetRecoveryEmail``). |
| `abort_two_step_setup()` | [HTTP] | Cancel a pending two-step setup (``abortTwoStepSetup``). |
| `change_password(password, new_password, *, new_hint=None)` | [HTTP] | Change the two-step password (``changePassword``). |
| `check_two_step_passcode(password)` | [HTTP] | Verify the two-step password (``checkTwoStepPasscode``). |
| `get_appearance_setting()` | [HTTP] | Theme and appearance settings (``getAppearanceSetting``). |
| `get_privacy_setting()` | [HTTP] | ``getPrivacySetting``. |
| `get_two_passcode_status()` | [HTTP] | Whether two-step verification is enabled (``getTwoPasscodeStatus``). |
| `get_user_setting()` | [HTTP] | ``getUserSetting``. |
| `request_change_phone_number(new_phone_number)` | [HTTP] | Start changing the account phone number (``requestChangePhoneNumber``). |
| `request_delete_account()` | [HTTP] | Ask Rubika to delete the account (``requestDeleteAccount``). |
| `request_recovery_email(password, recovery_email)` | [HTTP] | Set a recovery e-mail for two-step verification (``requestRecoveryEmail``). |
| `resend_code_recovery_email(password)` | [HTTP] | Resend the recovery e-mail code (``resendCodeRecoveryEmail``). |
| `set_privacy(**settings)` | [HTTP] | Alias of :meth:`set_setting`. |
| `set_setting(**settings)` | [HTTP] | Update privacy/notification settings (``setSetting``), e.g. ``set_setting(show_my_phone_number="Nobody")``. |
| `setup_two_step_verification(password, *, hint=None, recovery_email=None)` | [HTTP] | Enable two-step verification with a password (``setupTwoStepVerification``). |
| `turn_off_two_step(password)` | [HTTP] | Disable two-step verification (``turnOffTwoStep``). |
| `verify_change_phone_number(code, hash)` | [HTTP] | Confirm the new phone number with the received code (``verifyChangePhoneNumber``). |
| `verify_recovery_email(password, code)` | [HTTP] | Confirm the recovery e-mail with the received code (``verifyRecoveryEmail``). |

## Bots (user side), services, wallet, live and voice chats

| Method | Transport | Description |
|---|---|---|
| `add_live_comment(live_id, text)` | [HTTP] | Post a comment on a live stream (``addLiveComment``). |
| `click_bot_button(object_guid, message_id, button_id, *, text=None, aux_data=None)` | [HTTP] | Press an inline button of a bot message (``sendMessageAPICall``). |
| `create_group_voice_chat(chat_guid)` | [HTTP] | Start a voice chat in a group or channel (``createGroupVoiceChat``). |
| `discard_group_voice_chat(chat_guid, voice_chat_id)` | [HTTP] | End a voice chat (``discardGroupVoiceChat``). |
| `get_barcode_action(barcode)` | [HTTP] | What a scanned Rubika QR code does (``getBarcodeAction``). |
| `get_bot_info(bot_guid)` | [HTTP] | ``getBotInfo``. |
| `get_display_as_in_group_voice_chat(chat_guid, start_id=None)` | [HTTP] | Identities you can join a voice chat as (``getDisplayAsInGroupVoiceChat``). |
| `get_group_voice_chat(chat_guid, voice_chat_id)` | [HTTP] | State of a voice chat (``getGroupVoiceChat``). |
| `get_group_voice_chat_participants(chat_guid, voice_chat_id, start_id=None)` | [HTTP] | Participants of a voice chat, one page at a time (``getGroupVoiceChatParticipants``). |
| `get_group_voice_chat_participants_by_object_guids(chat_guid, voice_chat_id, object_guids)` | [HTTP] | Voice chat state of specific participants (``getGroupVoiceChatParticipantsByObjectGuids``). |
| `get_group_voice_chat_updates(chat_guid, voice_chat_id, state)` | [HTTP] | Changes in a voice chat since ``state`` (``getGroupVoiceChatUpdates``). |
| `get_landing_page(page_id=None, **data)` | [HTTP] | A services landing page (``getLandingPage`` on the services base). |
| `get_live_comments(live_id, start_id=None)` | [HTTP] | Comments of a live stream (``getLiveComments``). |
| `get_live_play_url(live_id, access_token)` | [HTTP] | Playback URL of a live stream (``getLivePlayUrl``). |
| `get_live_status(live_id, access_token)` | [HTTP] | Status of a live stream (``getLiveStatus``). |
| `get_live_viewers(live_id, start_id=None)` | [HTTP] | Viewers of a live stream (``getLiveViewers``). |
| `get_map_view(latitude, longitude)` | [HTTP] | Map tile information for a location (``getMapView``). |
| `get_payment_info(payment_id)` | [HTTP] | Details of a payment (``getPaymentInfo``). |
| `get_selection(bot_guid, selection_id, start_id=None)` | [HTTP] | Items of a bot selection keypad (``getSelection``). |
| `get_service_info(service_guid)` | [HTTP] | Information about a Rubika service (``getServiceInfo``). |
| `get_wallet_transfer_message(object_guid, message_id, transfer_id=None)` | [HTTP] | Details of a wallet transfer message (``getWalletTransferMessage``). |
| `get_web_app_function(app_id)` | [HTTP] | Web-app function metadata (``getWebAppFunction`` on the web-app base). |
| `join_group_voice_chat(chat_guid, voice_chat_id, sdp_offer_data, self_object_guid=None)` | [HTTP] | Join a voice chat with a WebRTC SDP offer (``joinGroupVoiceChat``). |
| `leave_group_voice_chat(chat_guid, voice_chat_id)` | [HTTP] | Leave a voice chat (``leaveGroupVoiceChat``). |
| `search_selection(bot_guid, selection_id, search_text, limit=20)` | [HTTP] | Search inside a bot selection keypad (``searchSelection``). |
| `send_group_voice_chat_activity(chat_guid, voice_chat_id, *, activity='Speaking', participant_object_guid=None)` | [HTTP] | Report speaking activity in a voice chat (``sendGroupVoiceChatActivity``). |
| `send_live(object_guid, *, title=None, thumb_inline=None, live_id=None, access_token=None)` | [HTTP] | Start a live stream message (``sendLive``). |
| `send_message_api_call(object_guid, message_id, button_id, *, text=None, aux_data=None)` | [HTTP] | Alias of `click_bot_button`. Press an inline button of a bot message (``sendMessageAPICall``). |
| `send_wallet_transfer_message(object_guid, *, amount=None, text=None, wallet_transfer=None)` | [HTTP] | Send money through the wallet (``sendWalletTransferMessage``). |
| `set_group_voice_chat_setting(chat_guid, voice_chat_id, *, join_muted=None, title=None)` | [HTTP] | Change the title or join-muted flag of a voice chat (``setGroupVoiceChatSetting``). |
| `set_group_voice_chat_state(chat_guid, voice_chat_id, participant_object_guid, action)` | [HTTP] | Mute or unmute a participant (``setGroupVoiceChatState``). |
| `set_live_setting(live_id, *, allow_comment=None)` | [HTTP] | Change live stream settings such as ``allow_comment`` (``setLiveSetting``). |
| `stop_bot(bot_guid)` | [HTTP] | Stop (block) a bot (``stopBot``). |
| `stop_live(live_id)` | [HTTP] | End a live stream (``stopLive``). |

## Rubino

| Method | Transport | Description |
|---|---|---|
| `get_base_info()` | [HTTP] | ``getBaseInfo`` on the services base; stores the suggested Rubino/wallet URLs. |
| `get_rubino_post(post_id=None, post_profile_id=None, *, rubino_post_data=None, track_id=None)` | [HTTP] | Fetch one Rubino post (``getProfilePosts`` on the Rubino DC). |
| `get_rubino_stories(story_id, story_profile_id)` | [HTTP] | Fetch a story (``getProfilesStoryList`` on the Rubino DC). |
| `send_rubino_post(object_guid, post_id, post_profile_id, *, text=None)` | [HTTP] | Share a Rubino post into a chat (``sendRubinoPost``). |

## Bot API

Only on `Client(token=...)`. Shared methods such as `send_message` or `get_me` switch to the Bot API automatically.

| Method | Transport | Description |
|---|---|---|
| `ban_chat_member(chat_id, user_id)` | [bot] | ``banChatMember``. |
| `dispatch_webhook_update(payload)` | [bot] | Parse a webhook body and run the registered handlers. |
| `download_bot_file(file, path=None, *, in_memory=False, file_name=None)` | [bot] | Download a Bot API file (``getFile`` + ``download_url``). |
| `edit_chat_keypad(chat_id, *, chat_keypad_type, chat_keypad=None)` | [bot] | ``editChatKeypad``. |
| `edit_inline_keypad(chat_id, message_id, inline_keypad)` | [bot] | Alias of `edit_message_keypad`. ``editMessageKeypad``. |
| `edit_message_keypad(chat_id, message_id, inline_keypad)` | [bot] | ``editMessageKeypad``. |
| `edit_message_text(chat_id, message_id, text)` | [HTTP] [bot] | ``editMessageText`` (user sessions fall back to :meth:`edit_message`). |
| `get_bot_updates(offset_id=None, limit=None)` | [bot] | ``getUpdates`` (long polling); the offset is persisted in the session. |
| `get_file(file_id)` | [bot] | ``getFile`` (returns ``download_url``). |
| `parse_webhook_update(payload)` | [bot] | Parse a webhook body into typed objects (no network). |
| `send_contact(chat_id, first_name, last_name, phone_number, *, chat_keypad=None, inline_keypad=None, reply_to_message_id=None, disable_notification=False, chat_keypad_type=None)` | [bot] | ``sendContact``. |
| `send_file(chat_id, file_id, *, text=None, reply_to_message_id=None, disable_notification=False, chat_keypad=None, inline_keypad=None, chat_keypad_type=None)` | [bot] | ``sendFile`` with an uploaded ``file_id``. |
| `set_commands(bot_commands)` | [bot] | ``setCommands``. |
| `unban_chat_member(chat_id, user_id)` | [bot] | ``unbanChatMember``. |
| `update_bot_endpoints(url, type)` | [bot] | ``updateBotEndpoints`` (webhook registration). |
| `upload_bot_file(upload_url, path)` | [bot] | Upload to the URL returned by ``requestSendFile`` and return the ``file_id``. |

## Updates

Receiving updates over the socket or by polling; the background listener.

| Method | Transport | Description |
|---|---|---|
| `dispatch_update(update)` | [HTTP] | Feed an update object (``Updates``, bot ``Update`` or ``InlineMessage``) to the handlers. |
| `get_chats_updates(state=None)` | [HTTP] | ``getChatsUpdates`` since ``state`` (defaults to the stored state); persists ``new_state``. |
| `get_messages_updates(object_guid, state=None)` | [HTTP] | ``getMessagesUpdates`` for one chat; the per-chat state is persisted. |
| `get_updates(*, timeout=None, transport=None, **kwargs)` | [both] | Fetch pending updates. |
| `idle()` | [both] | Keep receiving updates until :meth:`stop` is called or the loop is cancelled. |
| `receive_socket_update(timeout=None)` | [HTTP] | rubigram 0.1 name of :meth:`receive_update`. |
| `receive_update(timeout=None)` | [WS] | Wait for the next pushed frame and return it decrypted. |
| `start_polling(*, limit=100, idle_sleep=None)` | [HTTP] | rubigram 0.1 bot API: start the background polling loop. |
| `stop_polling()` | [both] | Stop the background update loop started by :meth:`start_polling` or :meth:`idle`. |

## Low level

The invoke seam for raw methods.

| Method | Transport | Description |
|---|---|---|
| `invoke(method, *, timeout=None, retries=None)` | [HTTP] | Send a raw method and return its typed result. |
| `invoke_raw(method_name, input_data=None, *, auth_mode='auth', dc_type=<DcType.API: 'api'>, api_version=None, service_url=None, timeout=None, retries=None)` | [HTTP] | Call any Rubika method by name and return a :class:`~rubigram.types.RawObject`. |
