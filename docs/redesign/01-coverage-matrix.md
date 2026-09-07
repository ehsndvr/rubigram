# Phase 1 — live protocol discovery and coverage matrix

Date: 2026-09-07. Source of truth for everything below: the web client
`https://web.rubika.ir/` (Angular bundle `main-es2015.6421623571994c9dd619.js`,
3.4 MB, app version **4.4.34**), read in the built-in browser with
`javascript_tool` (observation only), plus one unauthenticated `getDCs` call
from Python. The login page was open the whole time; no phone number, code or
token was entered by the assistant, and no message was sent. Live, logged-in
traffic (request headers on the wire, real response bodies for the methods
that have no recording, socket frames) is the remaining gap and is marked
**not observed** where it matters.

Recorded responses come from the owner's `examples.json` (41 methods + one
socket frame), sanitized into `tests/fixtures/rubika/*.json` (every GUID,
phone number, name, text, link and hash replaced by placeholders; the
sanitizer asserts nothing survived) and summarized in
[01-samples.md](01-samples.md).

## 1. Protocol constants (bundle) vs rubigram

| Item | web.rubika.ir 4.4.34 | rubigram today | Action |
|---|---|---|---|
| `app_version` | `4.4.34` (`vh.AppVersion`, also `?v=4.4.34` on assets) | `4.4.27` | update; make it a constructor option |
| `app_name` / `platform` / `package` / `lang_code` | `Main` / `Web` / `web.rubika.ir` / locale prefix (`fa`) | same | keep |
| service calls (`getBaseInfo`, Rubino, wallet, landing page) client | `{app_name, app_version, platform:"PWA", package}` (no lang_code) | same (owner's `_service_client_info`) | keep |
| socket handshake `api_version` | `"5"` (`vh.ApiVersion`) | `"5"` | keep |
| encrypted RPC `api_version` | `"6"` **only when** the stored key material has `version:"6"` (RSA-key login); then `auth` is caesar-transformed and `sign` is added. Legacy sessions send `"5"` without `sign`. | always `"6"` + sign | keep (rubigram always logs in with the RSA flow); document |
| unencrypted calls | `getDCs` `"4"`, `getBaseInfo`/Rubino/landing `"0"`, `getWebAppFunction` `"1"`, `sendCode`/`signIn` `"6"` with `tmp_session` | matches for the ones implemented | keep |
| `registerDevice` | `token_type:"Web"`, `token:""`, `app_version:"WB_"+4.4.34`, `lang_code`, `system_version` from UA (`Windows 10`, `Mac/iOS`, `Linux`, …), `device_model` = browser name + major (`Chrome 145`), `device_hash` = `navigator.mimeTypes.length` + all digits of the user agent. PWA never registers. | `WB_4.4.27`, random 26 digits | bump version; derive `device_hash` from the configured user agent the same way |
| request `Content-Type` | `text/plain` for RPC, `application/json` for `getDCs`/services | same | keep |
| browser headers | the JS sets nothing else; Chrome adds `user-agent`, `origin`, `referer`, `sec-ch-ua*`, `sec-fetch-*` itself | profile without `sec-ch-ua*` | add the `sec-ch-ua*` triple to the Chrome profile so on-wire requests look like the real browser (cosmetic; the failing header test expects it) |
| request timeout | 20 s (`RequestTimeout`), files 30 s (`FileRequestTimeout`) | 20 s / 60 s | keep, expose per call |
| retry policy | `RetryDelays=[0,2,3,5,10]` s, up to 5 retries, **switching to the next DC URL before each retry** (`dcUrl=""` → `getNextUrl`); `try_count:0` disables retries for `sendChatActivity`/voice activity; `getTime` uses 3 | one pass over the URL pool, no delay, no per-call override | implement the same ladder with a per-call `retries=` |
| DC URL rotation | `activeIndexDcs[type]` cycles per DC type with a 2 s lock (`switchUrlDelay`); socket connects use index 0 first, then rotate | pool per API only | pool per `DcType` |
| `getDCs` response | `default_api_urls[3]`, `default_sockets[3]`, `storages{dc_id → "https://messanger{n}.iranlms.ir/GetFile.ashx"}` (822 entries, note the spelling), `default_cdn_urls{tag → [".../GetFile"]}` (22 tags) | stored, but downloads ignore it | see §3 |
| socket ping | send the literal `{}` **30 s after the last received frame** (`SocketPingDelay`); every received frame clears the reconnect timer; after each ping a 20 s reconnect timer (`SocketWaitingTime`) is armed; on close/error reconnect after 5 s (`SocketRetryDelay`) to the next socket URL | fixed 30 s heartbeat, no silence detection, no reconnect | implement ping-after-idle, silence detection and reconnect with URL rotation |
| socket frames | `{type:"messenger", data_enc}` → decrypt with the auth key → update object; frames without `type` are pongs | same decode; unknown frames raise `DecodeError` | ignore non-messenger frames |
| update kinds inside a socket frame | `message_updates`, `chat_updates`, `show_activities`, `draft_message_updates`, `group_voice_chat_updates`, `group_voice_chat_participant_updates`, live status pushes; `show_notifications` was seen by the owner but is not handled by the web client | `chat_updates`, `message_updates`, `show_notifications` | model all of them, keep unknown keys |
| `getChatsUpdates` | `{state}` → `{status:"OK"\|"OldState", new_state, chats, deleted_chats}`; `OldState` ⇒ full reload via `getChats` | ignores `OldState` and `deleted_chats` | handle both |
| `getMessagesUpdates` | `{object_guid, state}` → `{status, new_state, updated_messages}` | missing | add |
| error `status` values | `OK, ERROR_TRY_AGAIN, ERROR_IGNORE, ERROR_MESSAGE_TRY, ERROR_MESSAGE_IGN, ERROR_GENERIC, ERROR_ACTION` | free text | enum |
| error `status_det` values | `OK, INVALID_INPUT, NOT_SUPPORTED_API_VERSION, SERVER_ERROR, INVALID_METHOD, CODE_IS_USED, CODE_IS_EXPIRED, INVALID_AUTH, NOT_REGISTERED, TOO_REQUESTS, USERNAME_EXIST, UNDELIVERABLE` | substring matching | exact mapping |
| client reaction to errors | `INVALID_AUTH`+`ERROR_ACTION` → session invalid (logout); `INVALID_AUTH`+`ERROR_GENERIC` → access denied (keep session); `NOT_REGISTERED` → `registerDevice` then retry (except for registerDevice/logout); `ERROR_GENERIC`+`TOO_REQUESTS` → rate-limit UI; any `client_show_message` → show its text/link | `NOT_REGISTERED` retry exists; the rest is lost | map to classes, expose `client_show_message` |
| upload | chunks of **131072** bytes to `upload_url` with headers `access-hash-send, auth, file-id, part-number, total-part, chunk-size`; success when `status_det == "OK"`; `access_hash_rec` taken from the last part's `data`; retries with the same delay ladder on network/5xx; files ≥ 10 MiB are flagged `inputFileBig` client-side only | same headers and chunk size, no retry, whole file read into memory | stream from disk, add retries |
| download | POST (empty body, `Content-Type: text/plain`) to `storages[dc_id]` with headers `auth, file-id, access-hash-rec, start-index, last-index`; response header `total_length` gives the full size; `responseType` arraybuffer | POST to `https://messenger{dc_id}.iranlms.ir/GetFile.ashx` | **bug**: use `storages[dc_id]` from `getDCs` (hosts are `messanger…`, not derivable from the id) and `total_length` |
| crypto | AES-256-CBC, zero IV, PKCS7, key = `createSecretPassphrase(auth)`; `auth` on the wire = caesar transform; `sign` = RSA PKCS#1 v1.5 SHA-256 over `data_enc` (jsrsasign); login key = RSA-1024, e=65537; server `auth` decrypted with the private key | identical (tests + working sessions confirm) | keep |
| limits | `MaxSendMessageLength=4096`, `FileMaxSize=1 GB`, `ChatPagingSize=20`, `EmailVerifyCodeLength=6` | none | validate before sending |

## 2. Web client method inventory

The bundle contains **203** distinct RPC method names as string literals (every
`method:"…"`) plus `signIn`, whose name is passed through an obfuscated constant
in the login module (204 in total). This is a superset of what any single click-flow would show, so the
matrix below is complete for the web client. Six raw methods that rubigram
implements do **not** exist in the web client:

| rubigram method | Where | What to do |
|---|---|---|
| `signUp` | SignUp raw method + sign_up() | Not called by the web client (registration happens through signIn). Keep, mark unverified. |
| `getChat` | GetChat raw method + get_chat() | No such RPC. Replace with getChatsByID / getAbsObjects; keep get_chat() as a wrapper. |
| `getHistory` | GetHistory raw method + get_history() | No such RPC. Remove; get_messages() with sort/limit covers it. |
| `deleteMessage` | DeleteMessage raw method + delete_message() | Real RPC is deleteMessages with message_ids and type. Keep delete_message() as a wrapper. |
| `blockUser / unblockUser` | BlockUser / UnblockUser + block_user()/unblock_user() | Real RPC is setBlockUser with action Block/Unblock. Keep the wrappers. |
| `uploadNewGroupAvatar` | UploadNewGroupAvatar + upload_group_avatar() | Real RPC is uploadAvatar with object_guid, thumbnail_file_id, main_file_id. Keep set_group_photo() as a wrapper. |

## 3. Differences that are very likely bugs today

1. **Downloads hit the wrong host.** The web client posts to `storages[dc_id]`
   from `getDCs` (for example dc `2` → `https://messanger2.iranlms.ir/GetFile.ashx`);
   rubigram builds `https://messenger{dc_id}.iranlms.ir/GetFile.ashx`.
2. **Outdated app version** `4.4.27` (server-visible in every request and in
   `registerDevice`).
3. **`getMessages` sends `offset`/`limit`**; the server paginates with
   `max_id`/`min_id`, `sort` and `limit` (and `filter_type`). `getHistory` and
   `getChat` do not exist at all.
4. **`deleteMessage`, `blockUser`, `unblockUser`, `uploadNewGroupAvatar` do not
   exist**; the real RPCs are `deleteMessages`, `setBlockUser` and `uploadAvatar`.
5. **`getContacts` sends `offset`/`limit`** instead of `start_id`.
6. **No retry ladder / DC rotation on retry**, no `try_count`, so transient
   errors surface immediately where the web client silently recovers.
7. **Socket never reconnects** and never detects silence; the web client
   pings after 30 s idle and reconnects after 20 s without an answer.
8. **`OldState` is ignored** for `getChatsUpdates`, so a stale state silently
   returns nothing.
9. **Error mapping by substring** and the lost `client_show_message`.
10. **`getChannelLink` result typed as `Empty`** although it carries `join_link`.
11. `sendMessage` cannot send `sticker`, `location`, `aux_data` (bot buttons) or
    `is_mute`; `editMessage` drops `metadata`; `editGroupInfo`/`editChannelInfo`
    cannot change `title`/`description`/`sign_messages`; member lists have no
    `start_id`/`search_text` pagination; `addChannel` forces avatar ids.

## 4. Coverage matrix

Status: **typed** = raw method + typed result exist; **partial** = exists but
the input or result misses fields the web client uses; **raw** = exists,
returns `RawObject`; **wrong** = exists but calls a non-existent method or
sends the wrong input; **missing** = not implemented. Priority: **P0** core
parity (implement first), **P1** full feature coverage, **P2** niche (live,
voice chat, wallet, web apps). "sample" = a sanitized recorded pair exists in
`tests/fixtures/rubika/`. Inputs prefixed `dyn:` were assembled from variables
in the bundle; the field list was reconstructed from the surrounding code.


| Status | Count |
|---|---|
| typed | 31 |
| partial | 8 |
| raw | 5 |
| wrong | 6 |
| missing | 154 |
| **total** | 204 |

### DC discovery and service base

| Method | Input (bundle) | rubigram | Priority | Notes |
|---|---|---|---|---|
| `getDCs` | `{} (api_version 4, plain JSON, no auth)` | typed | P0 | Response: default_api_urls[3], default_sockets[3], storages{dc_id: GetFile.ashx URL}(822), default_cdn_urls{tag: [urls]} |
| `getBaseInfo` | `{} (api_version 0, plain JSON, services base, platform PWA)` | typed | P0 | suggested_urls.suggested_rubino replaces the rubino DC list |

### WebSocket

| Method | Input (bundle) | rubigram | Priority | Notes |
|---|---|---|---|---|
| `handShake` | `{"api_version":"5","auth":<auth>,"data":"","method":"handShake"}` | typed | P0 | Ping is the literal {} 30 s after the last frame; reconnect if silent for 20 s; retry 5 s after close |

### Authentication and device

| Method | Input (bundle) | rubigram | Priority | Notes |
|---|---|---|---|---|
| `sendCode` | `dyn: {phone_number, send_type} (not_authorized, api_version 6, tmp_session)` | typed | P0 | Web sends the model built by the login form; send_type SMS/Internal |
| `signIn` | `dyn: {phone_number, phone_code_hash, phone_code, public_key} (not_authorized, api_version 6)` | typed | P0 | public_key = changeAuthType(base64(PEM)) of a fresh RSA-1024 key; response auth is RSA-decrypted with the private key |
| `registerDevice` | `{token_type:"Web", token:"", app_version:"WB_4.4.34", lang_code, system_version, device_model, device_hash}` | typed | P0 | rubigram sends WB_4.4.27; device_hash = mimeTypes.length + digits(userAgent); PWA skips it |
| `unregisterDevice` | `dyn: device descriptor (not_encrypt)` | missing | P1 |  |
| `logout` | `{}` | missing | P0 |  |
| `getTime` | `{} (try_count 3)` | missing | P1 | Server time offset used for message ordering |
| `loginTwoStepForgetPassword` | `{phone_number} (not_authorized)` | missing | P1 |  |
| `loginDisableTwoStep` | `dyn (not_authorized)` | missing | P1 |  |

### Sessions

| Method | Input (bundle) | rubigram | Priority | Notes |
|---|---|---|---|---|
| `getMySessions` | `{}` | missing | P0 | Active sessions list (view only) |
| `terminateSession` | `{session_key}` | missing | P0 |  |
| `terminateOtherSessions` | `{}` | missing | P1 |  |
| `getUnconfirmedSessions` | `{}` | missing | P1 | Response: unconfirmed_sessions |
| `actionOnUnconfirmedSession` | `{unconfirmed_session_key, action}` | missing | P1 |  |

### Two-step verification, recovery, phone change

| Method | Input (bundle) | rubigram | Priority | Notes |
|---|---|---|---|---|
| `getTwoPasscodeStatus` | `{}` | missing | P1 | Response: two_step_status |
| `setupTwoStepVerification` | `dyn: {password, hint, recovery_email?}` | missing | P1 |  |
| `checkTwoStepPasscode` | `{password}` | missing | P1 |  |
| `changePassword` | `dyn: {password, new_password, new_hint}` | missing | P1 |  |
| `turnOffTwoStep` | `{password}` | missing | P1 |  |
| `requestRecoveryEmail` | `dyn: {password, recovery_email}` | missing | P1 |  |
| `verifyRecoveryEmail` | `dyn: {password, code}` | missing | P1 | Response status "IsValid" |
| `resendCodeRecoveryEmail` | `{password}` | missing | P1 |  |
| `abortSetRecoveryEmail` | `{password}` | missing | P1 |  |
| `abortTwoStepSetup` | `{}` | missing | P1 |  |
| `requestChangePhoneNumber` | `{new_phone_number}` | missing | P1 |  |
| `verifyChangePhoneNumber` | `{code, hash}` | missing | P1 |  |
| `requestDeleteAccount` | `{}` | missing | P2 |  |

### Settings and privacy

| Method | Input (bundle) | rubigram | Priority | Notes |
|---|---|---|---|---|
| `getPrivacySetting` | `{}` | missing | P0 | Response: privacy_setting |
| `getUserSetting` (sample) | `{}` | missing | P1 | sample recorded |
| `setSetting` | `{settings:{...}, update_parameters:[...]}` | missing | P0 | Privacy and notification settings |
| `getAppearanceSetting` | `{}` | missing | P2 |  |

### Chats and dialogs

| Method | Input (bundle) | rubigram | Priority | Notes |
|---|---|---|---|---|
| `getChats` | `{start_id}` | missing | P0 | Dialog list pagination |
| `getChatsUpdates` (sample) | `{state}` | typed | P0 | Response status "OldState" means the state is stale: the client must reload with getChats; rubigram ignores it |
| `getChatsByID` (sample) | `{object_guids}` | missing | P0 | sample recorded |
| `getAbsObjects` | `{objects_guids: [...50 max]}` | missing | P0 | Abstract objects (title/avatar) for any guid |
| `seenChats` (sample) | `{seen_list: {object_guid: message_id}}` | missing | P0 | sample recorded |
| `setActionChat` | `{object_guid, action, duration?}` | missing | P0 | Mute/Unmute/Pin/Unpin/Archive style actions |
| `setChatUseTime` | `{object_guid, time}` | missing | P2 |  |
| `deleteUserChat` | `{user_guid, last_deleted_message_id}` | missing | P0 |  |
| `deleteChatHistory` (sample) | `{object_guid, last_message_id}` | typed | P0 | sample recorded |
| `deleteBotChat` | `{bot_guid, last_deleted_message_id}` | missing | P1 |  |
| `deleteServiceChat` | `{service_guid, last_deleted_message_id}` | missing | P2 |  |
| `deleteNoAccessGroupChat` | `{group_guid}` | missing | P2 |  |
| `getChatAds` (sample) | `{state}` | missing | P2 | sample recorded |
| `setAskSpamAction` | `dyn: {object_guid, action}` | missing | P1 |  |
| `reportObject` | `dyn: {object_guid, report_type, report_description?}` | missing | P1 |  |
| `getCommonGroups` | `{user_guid}` | missing | P1 | Response: abs_groups |
| `getRelatedObjects` | `{object_guid, start_id}` | missing | P2 |  |
| `clickMessageUrl` | `dyn: {object_guid, message_id, link_url}` | missing | P2 |  |
| `getMessageShareUrl` | `{object_guid, message_id}` | missing | P1 |  |
| `getLinkFromAppUrl` | `{app_url}` | missing | P2 |  |
| `getlinkObject` | `{share_string} (panel.iranlms.ir)` | missing | P2 |  |
| `getBarcodeAction` | `dyn (barcode.iranlms.ir, api_version 0, plain JSON)` | missing | P2 |  |

### Messages

| Method | Input (bundle) | rubigram | Priority | Notes |
|---|---|---|---|---|
| `sendMessage` (sample) | `{object_guid, rnd, text?, reply_to_message_id?, metadata?, file_inline?, sticker?, location?, aux_data?, is_mute?}` | partial | P0 | rubigram lacks sticker/location/aux_data/is_mute; sample recorded |
| `editMessage` | `dyn: {object_guid, message_id, text, metadata?}` | raw | P0 | rubigram omits metadata |
| `deleteMessages` | `dyn: {object_guid, message_ids, type:"Global"\|"Local"}` | wrong | P0 | rubigram calls a non-existent deleteMessage with one message_id |
| `forwardMessages` | `dyn: {from_object_guid, to_object_guid, message_ids, rnd}` | missing | P0 | Response: message_updates list |
| `getMessages` | `{object_guid, max_id\|min_id, sort:"FromMax"\|"FromMin", limit, filter_type?}` | wrong | P0 | rubigram sends offset/limit which the server does not use; response: messages, has_continue |
| `getMessagesByID` | `{object_guid, message_ids}` | missing | P0 |  |
| `getMessagesInterval` (sample) | `{object_guid, middle_message_id, filter_type?}` | missing | P0 | sample recorded |
| `getMessagesUpdates` | `{object_guid, state}` | missing | P0 | Response: status ("OldState" = reset), new_state, updated_messages |
| `setPinMessage` | `dyn: {object_guid, message_id, action:"Pin"\|"Unpin"}` | missing | P0 |  |
| `searchChatMessages` | `dyn: {object_guid, search_text, type:"Text"\|"Hashtag"}` | missing | P0 | Response: message_ids |
| `searchGlobalMessages` | `{search_text, type:"Text"\|"Hashtag", start_id}` | missing | P0 | Response: messages |
| `sendChatActivity` (sample) | `{object_guid, activity:"Typing"\|"Recording"\|"Uploading"} (try_count 0)` | typed | P0 | sample recorded |
| `getGroupMessageReadParticipants` | `{group_guid, message_id}` | missing | P1 |  |
| `transcribeVoice` | `{message_id, object_guid}` | missing | P2 |  |
| `getTranscription` | `{transcription_id, message_id}` | missing | P2 |  |

### Reactions

| Method | Input (bundle) | rubigram | Priority | Notes |
|---|---|---|---|---|
| `actionOnMessageReaction` | `dyn: {object_guid, message_id, reaction_id, action:"Add"\|"Remove"}` | missing | P0 | Response: reactions |
| `getMessageReactions` | `dyn: {object_guid, message_id, reaction_id?, start_id?}` | missing | P1 | Response: user_message_reactions |
| `getChatReaction` | `dyn: {object_guid}` | missing | P1 |  |
| `getAvailableReactions` (sample) | `{}` | typed | P0 | sample recorded |

### Polls

| Method | Input (bundle) | rubigram | Priority | Notes |
|---|---|---|---|---|
| `createPoll` | `dyn: {object_guid, question, options, type, is_anonymous, allows_multiple_answers, correct_option_index?, explanation?, rnd}` | missing | P1 |  |
| `votePoll` | `{poll_id, selection_index}` | missing | P0 |  |
| `getPollStatus` | `{poll_id}` | missing | P0 |  |
| `getPollOptionVoters` | `{poll_id, selection_index, start_id}` | missing | P2 |  |

### Drafts

| Method | Input (bundle) | rubigram | Priority | Notes |
|---|---|---|---|---|
| `getAllDrafts` | `{}` | missing | P1 | Response: draft_messages |
| `clearDrafts` | `{action:"All"\|..., object_guid}` | missing | P1 |  |

### Files, avatars and wallpapers

| Method | Input (bundle) | rubigram | Priority | Notes |
|---|---|---|---|---|
| `requestSendFile` (sample) | `{file_name, size, mime (extension)}` | typed | P0 | sample recorded; upload_url, id, dc_id, access_hash_send |
| `uploadAvatar` | `dyn: {object_guid, thumbnail_file_id, main_file_id}` | wrong | P0 | rubigram calls a non-existent uploadNewGroupAvatar with file_id/dc_id/access_hash_rec |
| `deleteAvatar` | `{object_guid, avatar_id}` | missing | P1 |  |
| `getAvatars` (sample) | `{object_guid}` | typed | P0 | sample recorded |
| `addSetWallpaper` | `{thumbnail_file_id, main_file_id}` | missing | P2 |  |
| `getWallpapers` | `{}` | missing | P2 |  |
| `resetWallpapers` | `{}` | missing | P2 |  |

### Users and contacts

| Method | Input (bundle) | rubigram | Priority | Notes |
|---|---|---|---|---|
| `getUserInfo` (sample) | `{user_guid}` | typed | P0 | sample recorded |
| `getObjectByUsername` (sample) | `{username}` | typed | P0 | sample recorded |
| `updateProfile` | `{first_name?, last_name?, bio?, birth_date?, updated_parameters:[...]}` | missing | P0 | Response: user |
| `updateUsername` | `{username}` | missing | P0 |  |
| `checkUserUsername` | `{username}` | missing | P0 | Response: exist |
| `setBlockUser` | `{user_guid, action:"Block"\|"Unblock"}` | wrong | P0 | rubigram calls non-existent blockUser/unblockUser with object_guid |
| `getBlockedUsers` | `{start_id}` | missing | P1 |  |
| `getContacts` | `{start_id}` | wrong | P0 | rubigram sends offset/limit |
| `getContactsUpdates` (sample) | `{state}` | typed | P0 | sample recorded |
| `getContactsLastOnline` (sample) | `{user_guids}` | typed | P0 | sample recorded |
| `addAddressBook` | `dyn: {phone, first_name, last_name}` | missing | P0 | Response: user |
| `deleteContact` | `{user_guid}` | missing | P1 |  |
| `resetContacts` | `{}` | missing | P2 |  |
| `getProfileLinkItems` | `{object_guid}` | typed | P1 |  |

### Groups

| Method | Input (bundle) | rubigram | Priority | Notes |
|---|---|---|---|---|
| `addGroup` (sample) | `dyn: {title, member_guids}` | typed | P0 | sample recorded |
| `getGroupInfo` (sample) | `{group_guid}` | typed | P0 | sample recorded |
| `editGroupInfo` (sample) | `dyn: {group_guid, updated_parameters, title?, description?, slow_mode?, chat_history_for_new_members?, event_messages?, chat_reaction_setting?}` | partial | P0 | rubigram cannot change title/description; 9 samples recorded |
| `addGroupMembers` | `{group_guid, member_guids}` | raw | P0 |  |
| `getGroupAllMembers` (sample) | `{group_guid, search_text?, start_id?}` | partial | P0 | rubigram has no pagination/search; sample recorded |
| `getGroupAdminMembers` | `{group_guid, start_id?, search_text?}` | missing | P0 |  |
| `getBannedGroupMembers` | `{group_guid, search_text?, start_id?}` | missing | P1 |  |
| `banGroupMember` (sample) | `{group_guid, member_guid, action:"Set"\|"Unset"}` | typed | P0 | sample recorded |
| `setGroupAdmin` (sample) | `dyn: {group_guid, member_guid, action:"SetAdmin"\|"UnsetAdmin", access_list}` | typed | P0 | 3 samples recorded |
| `getGroupAdminAccessList` | `{group_guid, member_guid}` | missing | P1 | Response: access_list |
| `getGroupDefaultAccess` (sample) | `{group_guid}` | typed | P1 | sample recorded |
| `setGroupDefaultAccess` (sample) | `{group_guid, access_list}` | raw | P1 | sample recorded |
| `getGroupLink` (sample) | `{group_guid}` | typed | P1 | sample recorded |
| `setGroupLink` | `{group_guid}` | missing | P1 | Regenerates the join link |
| `getGroupOnlineCount` | `{group_guid}` | missing | P1 |  |
| `getGroupMentionList` | `dyn: {group_guid, search_mention?}` | missing | P1 |  |
| `leaveGroup` | `{group_guid}` | missing | P0 |  |
| `joinGroup` | `{hash_link}` | missing | P0 |  |
| `groupPreviewByJoinLink` | `{hash_link}` | missing | P0 | Response: is_valid, group, ... |
| `removeGroup` (sample) | `{group_guid}` | raw | P1 | sample recorded |
| `requestChangeObjectOwner` (sample) | `dyn: {object_guid, new_owner_user_guid}` | raw | P1 | Response: status; sample recorded |
| `cancelChangeObjectOwner` | `{object_guid}` | missing | P1 |  |
| `replyRequestObjectOwner` | `dyn: {object_guid, action:"Accept"\|"Reject"}` | missing | P1 |  |
| `getPendingObjectOwner` (sample) | `{object_guid}` | typed | P1 | sample recorded |

### Channels

| Method | Input (bundle) | rubigram | Priority | Notes |
|---|---|---|---|---|
| `addChannel` (sample) | `dyn: {title, description?, channel_type, member_guids, thumbnail_file_id?, main_file_id?}` | typed | P0 | rubigram makes the avatar ids mandatory; sample recorded |
| `getChannelInfo` | `{channel_guid}` | typed | P0 |  |
| `editChannelInfo` (sample) | `dyn: {channel_guid, updated_parameters, title?, description?, sign_messages?, chat_reaction_setting?, channel_type?}` | partial | P0 | rubigram supports title/description only; sample recorded |
| `addChannelMembers` (sample) | `{channel_guid, member_guids}` | typed | P0 | sample recorded |
| `getChannelAllMembers` | `{channel_guid, start_id?, search_text?}` | partial | P0 | no pagination in rubigram |
| `getChannelAdminMembers` (sample) | `{channel_guid, start_id?, search_text?}` | partial | P0 | sample recorded |
| `getBannedChannelMembers` (sample) | `{channel_guid, search_text?, start_id?}` | partial | P1 | sample recorded |
| `banChannelMember` | `{channel_guid, member_guid, action:"Set"\|"Unset"}` | missing | P0 |  |
| `setChannelAdmin` (sample) | `dyn: {channel_guid, member_guid, action:"SetAdmin"\|"UnsetAdmin", access_list}` | typed | P0 | samples recorded |
| `getChannelAdminAccessList` | `{channel_guid, member_guid}` | missing | P1 |  |
| `getChannelLink` | `{channel_guid}` | wrong | P1 | rubigram types the result as Empty; the server returns join_link |
| `setChannelLink` | `{channel_guid}` | missing | P1 | Response: join_link |
| `updateChannelUsername` | `{channel_guid, username}` | missing | P1 |  |
| `checkChannelUsername` | `{username}` | missing | P1 |  |
| `joinChannelAction` | `{channel_guid, action:"Join"\|"Leave"\|"Remove"}` | missing | P0 |  |
| `joinChannelByLink` | `{hash_link}` | missing | P0 |  |
| `channelPreviewByJoinLink` | `{hash_link}` | missing | P0 |  |
| `removeChannel` | `{channel_guid}` | missing | P1 |  |

### Join links and join requests

| Method | Input (bundle) | rubigram | Priority | Notes |
|---|---|---|---|---|
| `getJoinLinks` (sample) | `{object_guid, creator_guid?}` | partial | P1 | rubigram omits creator_guid; sample recorded |
| `createJoinLink` (sample) | `dyn: {object_guid, title, request_needed, expire_time, usage_limit}` | typed | P1 | sample recorded |
| `editJoinLink` | `dyn: {object_guid, join_link, title?, request_needed?, expire_time?, usage_limit?}` | missing | P1 |  |
| `revokeJoinLink` | `{object_guid, join_link}` | missing | P1 |  |
| `deleteRevokedJoinLink` | `dyn: {object_guid, join_link}` | missing | P2 |  |
| `getJoinRequests` | `dyn: {object_guid, start_id?}` | missing | P1 |  |
| `actionOnJoinRequest` | `dyn: {object_guid, user_guid, action:"Accept"\|"Reject"}` | missing | P1 | Response: chat_update, group, message_update |
| `getJoinLinkUserJoined` | `dyn: {object_guid, join_link, start_id?}` | missing | P2 |  |

### Chat folders

| Method | Input (bundle) | rubigram | Priority | Notes |
|---|---|---|---|---|
| `getFolders` | `{last_state}` | missing | P0 | Response: folders, new_state |
| `getSuggestedFolders` | `{}` | missing | P2 | Response: suggested_folders |
| `addFolder` | `dyn: {name, include_chat_types?, exclude_chat_types?, include_object_guids?, exclude_object_guids?}` | missing | P1 | chat types: Contacts, NonConatcts (sic), Groups, Channels, Bots, Services |
| `editFolder` | `dyn: {folder_id, updated_parameters, ...same fields}` | missing | P1 |  |
| `deleteFolder` | `{folder_id}` | missing | P1 |  |
| `setPinChatInFolder` | `{folder_id, object_guid, action}` | missing | P1 |  |

### Stickers and GIFs

| Method | Input (bundle) | rubigram | Priority | Notes |
|---|---|---|---|---|
| `getMyStickerSets` | `{}` | missing | P0 | Response: sticker_sets |
| `getStickerSetByID` | `{sticker_set_id}` | missing | P1 |  |
| `getStickersBySetIDs` | `{sticker_set_ids}` | missing | P0 |  |
| `getStickersByEmoji` | `{emoji_character, suggest_by:"All"}` | missing | P1 |  |
| `searchStickers` | `{search_text, start_id}` | missing | P1 |  |
| `getTrendStickerSets` | `{start_id}` | missing | P1 |  |
| `getMyArchivedStickerSets` | `{search_text?, start_id?}` | missing | P2 |  |
| `actionOnStickerSet` | `{sticker_set_id, action:"Add"\|"Remove"}` | missing | P1 |  |
| `getStickerSetting` | `{}` | missing | P2 | Response: sticker_setting |
| `getMyGifSet` | `{}` | missing | P1 | Response: gifs |
| `addToMyGifSet` | `{message_id, object_guid}` | missing | P2 |  |

### Bots

| Method | Input (bundle) | rubigram | Priority | Notes |
|---|---|---|---|---|
| `sendMessageAPICall` | `dyn (dc_type bot)` | missing | P1 | Bot inline-button API calls; response: message_updates |
| `getBotInfo` | `{bot_guid}` | missing | P0 |  |
| `stopBot` | `{bot_guid}` | missing | P1 |  |
| `getSelection` | `{bot_guid, selection_id, start_id}` | missing | P2 |  |
| `searchSelection` | `{bot_guid, selection_id, search_text, limit}` | missing | P2 |  |

### Services and web apps

| Method | Input (bundle) | rubigram | Priority | Notes |
|---|---|---|---|---|
| `getServiceInfo` | `{service_guid}` | missing | P1 |  |
| `getLandingPage` | `dyn (services.iranlms.ir, api_version 0, plain JSON)` | missing | P2 |  |
| `getWebAppFunction` | `{app_id} (webapp1.iranlms.ir, api_version 1, plain JSON)` | missing | P2 |  |
| `getMapView` | `{location}` | missing | P2 |  |

### Rubino

| Method | Input (bundle) | rubigram | Priority | Notes |
|---|---|---|---|---|
| `getProfilePosts` | `{target_profile_id, max_id, min_id, equal:true, limit:1, sort:"FromMax"} (rubino DC, api_version 0)` | typed | P1 | Owner's rescued work |
| `getProfilesStoryList` | `{profile_story_ids:[{story_ids:[...], profile_id}]} (rubino DC, api_version 0)` | missing | P1 |  |
| `sendRubinoPost` | `dyn: {object_guid, rnd, ...post fields}` | missing | P1 |  |

### Wallet and payments

| Method | Input (bundle) | rubigram | Priority | Notes |
|---|---|---|---|---|
| `getWalletTransferMessage` | `dyn: {transfer_id, ...}` | missing | P2 |  |
| `sendWalletTransferMessage` | `dyn: {object_guid, rnd, ...}` | missing | P2 |  |
| `getPaymentInfo` | `{payment_id}` | missing | P2 |  |

### Live

| Method | Input (bundle) | rubigram | Priority | Notes |
|---|---|---|---|---|
| `sendLive` | `dyn: {object_guid, rnd, ...}` | missing | P2 |  |
| `stopLive` | `{live_id}` | missing | P2 |  |
| `getLiveStatus` | `{live_id, access_token}` | missing | P1 | Messages of type Live carry live_data.access_token |
| `getLivePlayUrl` | `{live_id, access_token}` | missing | P1 |  |
| `getLiveViewers` | `{live_id, start_id}` | missing | P2 |  |
| `getLiveComments` | `dyn: {live_id, ...}` | missing | P2 |  |
| `addLiveComment` | `dyn: {live_id, text, rnd}` | missing | P2 |  |
| `setLiveSetting` | `{live_id, allow_comment, updated_parameters}` | missing | P2 |  |

### Group voice chats

| Method | Input (bundle) | rubigram | Priority | Notes |
|---|---|---|---|---|
| `createGroupVoiceChat` | `{chat_guid}` | missing | P2 |  |
| `discardGroupVoiceChat` | `{chat_guid, voice_chat_id}` | missing | P2 |  |
| `getGroupVoiceChat` | `{chat_guid, voice_chat_id}` | missing | P2 |  |
| `getGroupVoiceChatParticipants` | `{chat_guid, voice_chat_id, start_id}` | missing | P2 |  |
| `getGroupVoiceChatParticipantsByObjectGuids` | `{chat_guid, voice_chat_id, object_guids}` | missing | P2 |  |
| `getGroupVoiceChatUpdates` | `{chat_guid, voice_chat_id, state}` | missing | P2 |  |
| `joinGroupVoiceChat` | `dyn: {chat_guid, voice_chat_id, sdp_offer_data, self_object_guid}` | missing | P2 |  |
| `leaveGroupVoiceChat` | `{chat_guid, voice_chat_id}` | missing | P2 |  |
| `sendGroupVoiceChatActivity` | `dyn: {chat_guid, voice_chat_id, activity:"Speaking"} (try_count 0)` | missing | P2 |  |
| `setGroupVoiceChatSetting` | `{chat_guid, voice_chat_id, join_muted?, updated_parameters}` | missing | P2 |  |
| `setGroupVoiceChatState` | `dyn: {chat_guid, voice_chat_id, participant_object_guid, action}` | missing | P2 |  |
| `getDisplayAsInGroupVoiceChat` | `{chat_guid, start_id}` | missing | P2 |  |

### Search

| Method | Input (bundle) | rubigram | Priority | Notes |
|---|---|---|---|---|
| `searchGlobalObjects` (sample) | `{search_text, filter_types?}` | typed | P0 | sample recorded |

## 5. What live observation still has to confirm

Once the owner logs in on the open browser tab, these items will be checked
and this file updated:

- exact request headers on the wire (the `sec-ch-ua*` set and header order);
- real response bodies for the P0 methods without a recording (`getChats`,
  `getMessages`, `getFolders`, `getMySessions`, `getPrivacySetting`,
  `getMyStickerSets`, `getStickersBySetIDs`, `getBotInfo`, `votePoll`,
  `getPollStatus`, `searchGlobalMessages`, `searchChatMessages`,
  `forwardMessages`, `setPinMessage`, `actionOnMessageReaction`);
- the socket frame sequence after `handShake` (pong shape, `show_activities`
  payload, `draft_message_updates`);
- the `getBaseInfo` response (`suggested_urls`, `update`, `start_popup`).

Nothing else in this document depends on a logged-in session.
