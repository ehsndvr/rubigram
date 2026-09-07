# Phase 1 — sanitized request/response samples

Generated from the owner's `examples.json` recordings (web client, early 2026). All GUIDs are replaced by `<prefix>EXAMPLE<index>` placeholders, phone numbers by `989120000000`, names, texts, links, hashes and tokens by fixed placeholders. The full sanitized pairs live in `tests/fixtures/rubika/<method>.json` and are meant to become unit-test fixtures for the typed result models.

## `addChannel`

Request `input`:

```json
{
  "title": "Sample title",
  "description": "Sample description",
  "channel_type": "Private",
  "member_guids": [
    "u0EXAMPLE00000000000000000000001"
  ],
  "thumbnail_file_id": "88602634217110",
  "main_file_id": "88602629903555"
}
```

Response (`status` OK / `status_det` OK), `data`:

```json
{
  "channel": {
    "channel_guid": "c0EXAMPLE00000000000000000000003",
    "channel_title": "Sample channel",
    "avatar_thumbnail": {
      "file_id": "88602634217110",
      "mime": "jpg",
      "dc_id": "846",
      "access_hash_rec": "ACCESS_HASH_REMOVED"
    },
    "count_members": 2,
    "description": "Sample description",
    "is_deleted": false,
    "is_verified": false,
    "channel_type": "Private",
    "sign_messages": false,
    "chat_reaction_setting": {
      "reaction_type": "Disabled"
    },
    "is_restricted_content": false
  },
  "chat_update": {
    "object_guid": "c0EXAMPLE00000000000000000000003",
    "action": "New",
    "chat": {
      "object_guid": "c0EXAMPLE00000000000000000000003",
      "access": [
        "ChangeInfo",
        "ViewMembers",
        "ViewAdmins",
        "PinMessages",
        "SendMessages",
        "EditAllMessages",
        "DeleteGlobalAllMessages",
        "AddMember",
        "SetAdmin",
        "SetJoinLink",
        "SuperAdmin",
        "RemoveObject",
        "ViewInfo",
        "ViewMessages"
      ],
      "count_unseen": 1,
      "is_mute": false,
      "is_pinned": false,
      "time_string": "177424007100001571706695825913",
      "last_message": {
        "message_id": "1571706695825913",
        "type": "Other",
        "text": "sample text",
        "is_mine": false
      },
      "last_seen_my_mid": "0",
      "last_seen_peer_mid": "0",
      "status": "Active",
      "time": 1774240071,
      "abs_object": {
        "object_guid": "c0EXAMPLE00000000000000000000003",
        "type": "Channel",
        "title": "Sample title",
... (44 more lines in tests/fixtures/rubika/addChannel.json)
```

## `addChannelMembers`

Request `input`:

```json
{
  "channel_guid": "c0EXAMPLE00000000000000000000003",
  "member_guids": [
    "u0EXAMPLE00000000000000000000001"
  ]
}
```

Response (`status` OK / `status_det` OK), `data`:

```json
{
  "added_in_chat_members": [
    {
      "member_type": "User",
      "member_guid": "u0EXAMPLE00000000000000000000001",
      "first_name": "Sample",
      "last_name": "User",
      "is_verified": false,
      "is_deleted": false,
      "last_online": 1774211400,
      "join_type": "Member",
      "username": "sample_user",
      "online_time": {
        "type": "Approximate",
        "approximate_period": "Recently"
      }
    }
  ],
  "timestamp": "1774284632",
  "channel": {
    "channel_guid": "c0EXAMPLE00000000000000000000003",
    "channel_title": "Sample channel",
    "avatar_thumbnail": {
      "file_id": "88602634217110",
      "mime": "jpg",
      "dc_id": "846",
      "access_hash_rec": "ACCESS_HASH_REMOVED"
    },
    "count_members": 2,
    "description": "Sample description",
    "is_deleted": false,
    "is_verified": false,
    "channel_type": "Private",
    "sign_messages": false,
    "chat_reaction_setting": {
      "reaction_type": "Selected",
      "selected_reactions": [
        "3",
        "2"
      ]
    },
    "is_restricted_content": false
  }
}
```

## `addGroup`

Request `input`:

```json
{
  "title": "Sample title",
  "member_guids": [
    "b0EXAMPLE00000000000000000000005"
  ]
}
```

Response (`status` OK / `status_det` OK), `data`:

```json
{
  "group": {
    "group_guid": "g0EXAMPLE00000000000000000000007",
    "group_title": "Sample group",
    "count_members": 2,
    "is_deleted": false,
    "is_verified": false,
    "slow_mode": 0,
    "chat_history_for_new_members": "Visible",
    "event_messages": true,
    "chat_reaction_setting": {
      "reaction_type": "All"
    },
    "is_restricted_content": false
  },
  "chat_update": {
    "object_guid": "g0EXAMPLE00000000000000000000007",
    "action": "New",
    "chat": {
      "object_guid": "g0EXAMPLE00000000000000000000007",
      "access": [
        "ChangeInfo",
        "PinMessages",
        "DeleteGlobalAllMessages",
        "BanMember",
        "SetAdmin",
        "SetJoinLink",
        "SetMemberAccess",
        "ViewMembers",
        "ViewAdmins",
        "SendMessages",
        "AddMember",
        "SuperAdmin",
        "RemoveObject",
        "ViewInfo",
        "ViewMessages",
        "DeleteLocalMessages",
        "EditMyMessages",
        "DeleteGlobalMyMessages"
      ],
      "count_unseen": 0,
      "is_mute": false,
      "is_pinned": false,
      "time_string": "177423711600000000000000000000",
      "last_message": {
        "message_id": "0",
        "type": "NotMessage",
        "text": "sample text"
      },
      "last_seen_my_mid": "0",
      "last_seen_peer_mid": "0",
      "status": "Active",
      "time": 1774237116,
      "abs_object": {
        "object_guid": "g0EXAMPLE00000000000000000000007",
        "type": "Group",
        "title": "Sample title",
        "is_verified": false,
        "is_deleted": false
      },
... (39 more lines in tests/fixtures/rubika/addGroup.json)
```

## `banGroupMember`

Request `input`:

```json
{
  "group_guid": "g0EXAMPLE00000000000000000000007",
  "member_guid": "b0EXAMPLE00000000000000000000005",
  "action": "Set"
}
```

Response (`status` OK / `status_det` OK), `data`:

```json
{
  "timestamp": "1774239170",
  "group": {
    "group_guid": "g0EXAMPLE00000000000000000000007",
    "group_title": "Sample group",
    "count_members": 1,
    "is_deleted": false,
    "is_verified": false,
    "slow_mode": 0,
    "chat_history_for_new_members": "Hidden",
    "event_messages": false,
    "chat_reaction_setting": {
      "reaction_type": "All"
    },
    "is_restricted_content": true
  }
}
```

## `chat_updates`

A decrypted socket frame (`type: messenger`) as pushed by the server.

```json
{
  "chat_updates": [
    {
      "object_guid": "u0EXAMPLE00000000000000000000001",
      "action": "Edit",
      "chat": {
        "count_unseen": 1,
        "time_string": "177359569100001556351220500832",
        "last_message": {
          "message_id": "1556351220500832",
          "type": "Text",
          "text": "sample text",
          "author_object_guid": "u0EXAMPLE00000000000000000000001",
          "is_mine": false,
          "author_type": "User"
        },
        "last_seen_peer_mid": "1556351220500832",
        "status": "Active",
        "time": 1773595691,
        "last_message_id": "1556351220500832"
      },
      "updated_parameters": [
        "last_message_id",
        "last_message",
        "status",
        "time_string",
        "count_unseen",
        "last_seen_peer_mid",
        "time"
      ],
      "timestamp": "1773595691",
      "type": "User"
    }
  ],
  "message_updates": [
    {
      "message_id": "1556351220500832",
      "action": "New",
      "message": {
        "message_id": "1556351220500832",
        "text": "sample text",
        "time": "1773595691",
        "is_edited": false,
        "type": "Text",
        "author_type": "User",
        "author_object_guid": "u0EXAMPLE00000000000000000000001",
        "allow_transcription": false
      },
      "updated_parameters": [],
      "timestamp": "1773595691",
      "prev_message_id": "248215745402832",
      "object_guid": "u0EXAMPLE00000000000000000000001",
      "type": "User",
      "state": "1773595631",
      "is_scheduled": false
    }
  ],
  "show_notifications": [
    {
      "notification_id": "n_u0Crz5308d9ca919827a835fac44dbae1556351220500832",
... (12 more lines in tests/fixtures/rubika/socket_update.json)
```

## `createJoinLink`

Request `input`:

```json
{
  "object_guid": "g0EXAMPLE00000000000000000000007",
  "title": "Sample title",
  "request_needed": false,
  "expire_time": 86400,
  "usage_limit": 10
}
```

Response (`status` OK / `status_det` OK), `data`:

```json
{
  "join_link": {
    "object_guid": {
      "type": "Group",
      "object_guid": "g0EXAMPLE00000000000000000000007"
    },
    "join_link": "https://rubika.ir/joing/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
    "creator_guid": "u0EXAMPLE00000000000000000000002",
    "create_time": 1774238631,
    "request_pending_count": 0,
    "request_needed": false,
    "usage_limit": 10,
    "title": "Sample title",
    "expire_time": 86400,
    "expire_at": 1774325031
  }
}
```

## `deleteChatHistory`

Request `input`:

```json
{
  "object_guid": "u0EXAMPLE00000000000000000000001",
  "last_message_id": "1557045568911832"
}
```

Response (`status` OK / `status_det` OK), `data`:

```json
{
  "chat_update": {
    "object_guid": "u0EXAMPLE00000000000000000000001",
    "action": "Edit",
    "chat": {
      "count_unseen": 0,
      "last_message": {
        "message_id": "0",
        "type": "NotMessage",
        "text": "sample text"
      },
      "last_message_id": "0",
      "last_deleted_mid": "1557045568911832"
    },
    "updated_parameters": [
      "last_message",
      "last_message_id",
      "count_unseen",
      "last_deleted_mid"
    ],
    "timestamp": "1774236945",
    "type": "User"
  }
}
```

## `editChannelInfo`

Request `input`:

```json
{
  "channel_guid": "c0EXAMPLE00000000000000000000003",
  "title": "Sample title",
  "description": "Sample description",
  "updated_parameters": [
    "title",
    "description"
  ]
}
```

Response (`status` OK / `status_det` OK), `data`:

```json
{
  "channel": {
    "channel_guid": "c0EXAMPLE00000000000000000000003",
    "channel_title": "Sample channel",
    "avatar_thumbnail": {
      "file_id": "88602634217110",
      "mime": "jpg",
      "dc_id": "846",
      "access_hash_rec": "ACCESS_HASH_REMOVED"
    },
    "count_members": 2,
    "description": "Sample description",
    "is_deleted": false,
    "is_verified": false,
    "channel_type": "Private",
    "sign_messages": false,
    "chat_reaction_setting": {
      "reaction_type": "Selected",
      "selected_reactions": [
        "3",
        "2"
      ]
    },
    "is_restricted_content": false
  },
  "chat_update": {
    "object_guid": "c0EXAMPLE00000000000000000000003",
    "action": "Edit",
    "chat": {
      "abs_object": {
        "object_guid": "c0EXAMPLE00000000000000000000003",
        "type": "Channel",
        "title": "Sample title",
        "avatar_thumbnail": {
          "file_id": "88602634217110",
          "mime": "jpg",
          "dc_id": "846",
          "access_hash_rec": "ACCESS_HASH_REMOVED"
        },
        "is_verified": false,
        "is_deleted": false
      }
    },
    "updated_parameters": [
      "abs_object"
    ],
    "timestamp": "1774284150",
    "type": "Channel"
  },
  "timestamp": "1774284150"
}
```

## `editGroupInfo`

Request `input`:

```json
{
  "group_guid": "g0EXAMPLE00000000000000000000007",
  "slow_mode": 30,
  "updated_parameters": [
    "slow_mode"
  ]
}
```

Response (`status` OK / `status_det` OK), `data`:

```json
{
  "group": {
    "group_guid": "g0EXAMPLE00000000000000000000007",
    "group_title": "Sample group",
    "count_members": 2,
    "is_deleted": false,
    "is_verified": false,
    "slow_mode": 0,
    "chat_history_for_new_members": "Visible",
    "event_messages": true,
    "chat_reaction_setting": {
      "reaction_type": "All"
    },
    "is_restricted_content": false
  },
  "timestamp": "1774238754"
}
```

(9 recorded variants; only the first request/response pair is shown.)

## `getAvailableReactions`

Request `input`:

```json
{}
```

Response (`status` OK / `status_det` OK), `data`:

```json
{
  "reactions": [
    {
      "reaction_id": "1",
      "emoji_char": "❤",
      "name": "Red Heart"
    },
    {
      "reaction_id": "2",
      "emoji_char": "👍",
      "name": "Thumbs Up"
    },
    {
      "reaction_id": "74",
      "emoji_char": "🇮🇷",
      "name": "Iran"
    }
  ]
}
```

## `getAvatars`

Request `input`:

```json
{
  "object_guid": "u0EXAMPLE00000000000000000000012"
}
```

Response (`status` OK / `status_det` OK), `data`:

```json
{
  "avatars": [
    {
      "avatar_id": "68761b439692781e8a713cde",
      "thumbnail": {
        "file_id": "70751777394204",
        "mime": "jpg",
        "dc_id": "930",
        "access_hash_rec": "ACCESS_HASH_REMOVED"
      },
      "main": {
        "file_id": "70751782662863",
        "mime": "jpg",
        "dc_id": "845",
        "access_hash_rec": "ACCESS_HASH_REMOVED"
      },
      "create_time": 1752570691
    },
    {
      "avatar_id": "68578e68829a00497df4e530",
      "thumbnail": {
        "file_id": "68868888499612",
        "mime": "jpg",
        "dc_id": "924",
        "access_hash_rec": "ACCESS_HASH_REMOVED"
      },
      "main": {
        "file_id": "68868891395818",
        "mime": "jpg",
        "dc_id": "915",
        "access_hash_rec": "ACCESS_HASH_REMOVED"
      },
      "create_time": 1750568552
    }
  ]
}
```

## `getBannedChannelMembers`

Request `input`:

```json
{
  "channel_guid": "c0EXAMPLE00000000000000000000003"
}
```

Response (`status` OK / `status_det` OK), `data`:

```json
{
  "in_chat_members": [],
  "has_continue": false,
  "timestamp": "1774284380"
}
```

## `getChannelAdminMembers`

Request `input`:

```json
{
  "channel_guid": "c0EXAMPLE00000000000000000000003"
}
```

Response (`status` OK / `status_det` OK), `data`:

```json
{
  "in_chat_members": [
    {
      "member_type": "User",
      "member_guid": "u0EXAMPLE00000000000000000000002",
      "first_name": "Sample",
      "is_verified": false,
      "is_deleted": false,
      "last_online": 1774284227,
      "join_type": "Creator",
      "username": "sample_user",
      "online_time": {
        "type": "Exact",
        "exact_time": 1774284227
      }
    }
  ],
  "next_start_id": "69c0c1472b7c9ba33d9d6f7b",
  "has_continue": false,
  "timestamp": "1774284227"
}
```

## `getChatAds`

Request `input`:

```json
{
  "state": 1773592237
}
```

Response (`status` OK / `status_det` OK), `data`:

```json
{
  "chat_ads": [
    {
      "chat_ads_id": "pro_634bfbae7c7c2887da23cf7d",
      "link": {
        "type": "joinchannel",
        "joinchannel_data": {
          "username": "sample_user",
          "ask_join": "true"
        }
      },
      "title": "Sample title",
      "text": "sample text",
      "image": {
        "file_id": "87924012924119",
        "mime": "jpg",
        "dc_id": "32",
        "access_hash_rec": "ACCESS_HASH_REMOVED",
        "cdn_tag": "PR18"
      },
      "notice_text": "",
      "notice_color": {
        "red": 113,
        "blue": 120,
        "green": 117,
        "alpha": 255
      },
      "has_action": true,
      "action_text": "ورود",
      "action_background_color": {
        "red": 0,
        "blue": 145,
        "green": 212,
        "alpha": 255
      },
      "force_show": true
    }
  ],
  "new_state": 1773595459,
  "apply_ads": true,
  "next_call_period": 90
}
```

## `getChatsByID`

Request `input`:

```json
{
  "object_guids": [
    "u0EXAMPLE00000000000000000000001"
  ]
}
```

Response (`status` OK / `status_det` OK), `data`:

```json
{
  "chats": [
    {
      "object_guid": "u0EXAMPLE00000000000000000000001",
      "access": [
        "ViewInfo",
        "ViewMessages",
        "DeleteLocalMessages",
        "EditMyMessages",
        "DeleteGlobalMyMessages",
        "SendMessages",
        "PinMessages"
      ],
      "count_unseen": 1,
      "is_mute": false,
      "is_pinned": false,
      "time_string": "177359569100001556351220500832",
      "last_message": {
        "message_id": "1556351220500832",
        "type": "Text",
        "text": "sample text",
        "author_object_guid": "u0EXAMPLE00000000000000000000001",
        "is_mine": false,
        "author_type": "User"
      },
      "last_seen_my_mid": "248215745402832",
      "last_seen_peer_mid": "1556351220500832",
      "status": "Active",
      "time": 1773595691,
      "abs_object": {
        "object_guid": "u0EXAMPLE00000000000000000000001",
        "type": "User",
        "first_name": "Sample",
        "last_name": "User",
        "is_verified": false,
        "is_deleted": false
      },
      "is_blocked": false,
      "last_message_id": "1556351220500832",
      "last_deleted_mid": "0",
      "is_in_contact": true,
      "show_ask_spam": false,
      "auto_delete": "Off"
    }
  ],
  "timestamp": "1773595691"
}
```

## `getChatsUpdates`

Request `input`:

```json
{
  "state": 1773595399
}
```

Response (`status` OK / `status_det` OK), `data`:

```json
{
  "chats": [],
  "new_state": 1773595460,
  "status": "OK",
  "timestamp": "1773595520"
}
```

## `getContactsLastOnline`

Request `input`:

```json
{
  "user_guids": [
    "u0EXAMPLE00000000000000000000009",
    "u0EXAMPLE00000000000000000000010",
    "u0EXAMPLE00000000000000000000011"
  ]
}
```

Response (`status` OK / `status_det` OK), `data`:

```json
{
  "users": [
    {
      "user_guid": "u0EXAMPLE00000000000000000000009",
      "last_online": 1714941000,
      "online_time": {
        "type": "Approximate",
        "approximate_period": "LongAgo"
      }
    },
    {
      "user_guid": "u0EXAMPLE00000000000000000000010",
      "last_online": 1714768200,
      "online_time": {
        "type": "Approximate",
        "approximate_period": "LongAgo"
      }
    },
    {
      "user_guid": "u0EXAMPLE00000000000000000000011",
      "last_online": 1714681800,
      "online_time": {
        "type": "Approximate",
        "approximate_period": "LongAgo"
      }
    }
  ]
}
```

## `getContactsUpdates`

Request `input`:

```json
{
  "state": 1774239888
}
```

Response (`status` OK / `status_det` OK), `data`:

```json
{
  "users": [],
  "deleted_users": [],
  "new_state": 1774284426,
  "status": "OK",
  "timestamp": "1774284486"
}
```

## `getGroupAllMembers`

Request `input`:

```json
{
  "group_guid": "g0EXAMPLE00000000000000000000007"
}
```

Response (`status` OK / `status_det` OK), `data`:

```json
{
  "in_chat_members": [
    {
      "member_type": "Bot",
      "member_guid": "b0EXAMPLE00000000000000000000005",
      "title": "Sample title",
      "is_verified": false,
      "is_deleted": false,
      "join_type": "Member",
      "username": "sample_user"
    },
    {
      "member_type": "User",
      "member_guid": "u0EXAMPLE00000000000000000000002",
      "first_name": "Sample",
      "is_verified": false,
      "is_deleted": false,
      "last_online": 1774237744,
      "join_type": "Creator",
      "username": "sample_user",
      "online_time": {
        "type": "Exact",
        "exact_time": 1774237744
      }
    }
  ],
  "has_continue": false,
  "timestamp": "1774237744"
}
```

## `getGroupDefaultAccess`

Request `input`:

```json
{
  "group_guid": "g0EXAMPLE00000000000000000000007"
}
```

Response (`status` OK / `status_det` OK), `data`:

```json
{
  "access_list": [
    "ViewMembers",
    "ViewAdmins",
    "SendMessages"
  ]
}
```

## `getGroupInfo`

Request `input`:

```json
{
  "group_guid": "g0EXAMPLE00000000000000000000007"
}
```

Response (`status` OK / `status_det` OK), `data`:

```json
{
  "group": {
    "group_guid": "g0EXAMPLE00000000000000000000007",
    "group_title": "Sample group",
    "count_members": 2,
    "is_deleted": false,
    "is_verified": false,
    "slow_mode": 0,
    "chat_history_for_new_members": "Visible",
    "event_messages": true,
    "chat_reaction_setting": {
      "reaction_type": "All"
    },
    "is_restricted_content": false
  },
  "chat": {
    "object_guid": "g0EXAMPLE00000000000000000000007",
    "access": [
      "ChangeInfo",
      "PinMessages",
      "DeleteGlobalAllMessages",
      "BanMember",
      "SetAdmin",
      "SetJoinLink",
      "SetMemberAccess",
      "ViewMembers",
      "ViewAdmins",
      "SendMessages",
      "AddMember",
      "SuperAdmin",
      "RemoveObject",
      "ViewInfo",
      "ViewMessages",
      "DeleteLocalMessages",
      "EditMyMessages",
      "DeleteGlobalMyMessages"
    ],
    "count_unseen": 1,
    "is_mute": false,
    "is_pinned": false,
    "time_string": "177423711600001571692526621380",
    "last_message": {
      "message_id": "1571692526621380",
      "type": "Other",
      "text": "sample text",
      "is_mine": false
    },
    "last_seen_my_mid": "0",
    "last_seen_peer_mid": "0",
    "status": "Active",
    "time": 1774237116,
    "abs_object": {
      "object_guid": "g0EXAMPLE00000000000000000000007",
      "type": "Group",
      "title": "Sample title",
      "is_verified": false,
      "is_deleted": false
    },
    "is_blocked": false,
    "last_message_id": "1571692526621380",
... (7 more lines in tests/fixtures/rubika/getGroupInfo.json)
```

## `getGroupLink`

Request `input`:

```json
{
  "group_guid": "g0EXAMPLE00000000000000000000007"
}
```

Response (`status` OK / `status_det` OK), `data`:

```json
{
  "join_link": "https://rubika.ir/joing/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
}
```

## `getJoinLinks`

Request `input`:

```json
{
  "object_guid": "g0EXAMPLE00000000000000000000007"
}
```

Response (`status` OK / `status_det` OK), `data`:

```json
{
  "join_links": []
}
```

## `getMessagesInterval`

Request `input`:

```json
{
  "object_guid": "u0EXAMPLE00000000000000000000001",
  "middle_message_id": 248215745402832
}
```

Response (`status` OK / `status_det` OK), `data`:

```json
{
  "messages": [
    {
      "message_id": "216032502242832",
      "text": "sample text",
      "time": "1646209776",
      "is_edited": false,
      "type": "Text",
      "author_type": "User",
      "author_object_guid": "u0EXAMPLE00000000000000000000002",
      "allow_transcription": false
    },
    {
      "message_id": "216357682495832",
      "text": "sample text",
      "time": "1646283895",
      "is_edited": false,
      "type": "Text",
      "author_type": "User",
      "author_object_guid": "u0EXAMPLE00000000000000000000001",
      "allow_transcription": false
    },
    {
      "message_id": "248215745402832",
      "text": "sample text",
      "time": "1654678430",
      "is_edited": false,
      "type": "Text",
      "author_type": "User",
      "author_object_guid": "u0EXAMPLE00000000000000000000002",
      "allow_transcription": false
    }
  ],
  "state": "1773596092",
  "new_has_continue": true,
  "old_has_continue": true,
  "new_min_id": 248215745402833,
  "old_max_id": 216032502242831,
  "timestamp": "1773596152"
}
```

## `getObjectByUsername`

Request `input`:

```json
{
  "username": "sample_user"
}
```

Response (`status` OK / `status_det` OK), `data`:

```json
{
  "exist": true,
  "type": "User",
  "user": {
    "user_guid": "u0EXAMPLE00000000000000000000001",
    "first_name": "Sample",
    "last_name": "User",
    "phone": "989120000000",
    "username": "sample_user",
    "last_online": 1773174600,
    "is_deleted": false,
    "is_verified": false,
    "online_time": {
      "type": "Approximate",
      "approximate_period": "Recently"
    }
  },
  "chat": {
    "object_guid": "u0EXAMPLE00000000000000000000001",
    "access": [
      "ViewInfo",
      "ViewMessages",
      "DeleteLocalMessages",
      "EditMyMessages",
      "DeleteGlobalMyMessages",
      "SendMessages",
      "PinMessages"
    ],
    "count_unseen": 0,
    "is_mute": false,
    "is_pinned": false,
    "time_string": "165467843000000248215745402832",
    "last_message": {
      "message_id": "248215745402832",
      "type": "Text",
      "text": "sample text",
      "author_object_guid": "u0EXAMPLE00000000000000000000002",
      "is_mine": true,
      "author_title": "شما",
      "author_type": "User"
    },
    "last_seen_my_mid": "248215745402832",
    "last_seen_peer_mid": "248215745402832",
    "status": "Active",
    "time": 1654678430,
    "abs_object": {
      "object_guid": "u0EXAMPLE00000000000000000000001",
      "type": "User",
      "first_name": "Sample",
      "last_name": "User",
      "is_verified": false,
      "is_deleted": false
    },
    "is_blocked": false,
    "last_message_id": "248215745402832",
    "last_deleted_mid": "0",
    "is_in_contact": true,
    "show_ask_spam": false,
    "auto_delete": "Off"
  },
... (3 more lines in tests/fixtures/rubika/getObjectByUsername.json)
```

## `getPendingObjectOwner`

Request `input`:

```json
{
  "object_guid": "g0EXAMPLE00000000000000000000007"
}
```

Response (`status` OK / `status_det` OK), `data`:

```json
{
  "exist_pending_owner": false
}
```

## `getUserInfo`

Request `input`:

```json
{
  "user_guid": "u0EXAMPLE00000000000000000000008"
}
```

Response (`status` OK / `status_det` OK), `data`:

```json
{
  "user": {
    "user_guid": "u0EXAMPLE00000000000000000000008",
    "first_name": "Sample",
    "last_name": "User",
    "phone": "989120000000",
    "last_online": 1773174600,
    "is_deleted": false,
    "is_verified": false,
    "online_time": {
      "type": "Approximate",
      "approximate_period": "Recently"
    }
  },
  "chat": {
    "object_guid": "u0EXAMPLE00000000000000000000008",
    "access": [
      "ViewInfo",
      "ViewMessages",
      "DeleteLocalMessages",
      "EditMyMessages",
      "DeleteGlobalMyMessages",
      "SendMessages",
      "PinMessages"
    ],
    "count_unseen": 0,
    "is_mute": false,
    "is_pinned": false,
    "time_string": "177308817800000000000000000000",
    "last_message": {
      "message_id": "0",
      "type": "NotMessage",
      "text": "sample text"
    },
    "last_seen_my_mid": "0",
    "last_seen_peer_mid": "0",
    "status": "Active",
    "time": 1773088178,
    "abs_object": {
      "object_guid": "u0EXAMPLE00000000000000000000008",
      "type": "User",
      "first_name": "Sample",
      "last_name": "User",
      "is_verified": false,
      "is_deleted": false
    },
    "is_blocked": false,
    "last_message_id": "0",
    "last_deleted_mid": "0",
    "is_in_contact": true,
    "show_ask_spam": false,
    "auto_delete": "Off"
  },
  "timestamp": "1773234771",
  "is_in_contact": true,
  "can_receive_call": true,
  "can_video_call": true,
  "user_additional_info": {
    "is_in_contact": true,
    "can_receive_call": true,
... (3 more lines in tests/fixtures/rubika/getUserInfo.json)
```

## `getUserSetting`

Request `input`:

```json
{}
```

Response (`status` OK / `status_det` OK), `data`:

```json
{
  "privacy_setting": {
    "count_blocked_user": 0,
    "count_active_sessions": 11,
    "sign_in_type": "Simple",
    "show_my_phone_number": "MyContacts",
    "show_my_profile_photo": "MyContacts",
    "can_join_chat_by": "Everybody",
    "link_forward_message": "Nobody",
    "can_called_by": "Nobody",
    "delete_account_not_active_months": 24,
    "show_my_last_online": "Nobody",
    "exceptions": [],
    "show_my_birth_date": "MyContacts",
    "auto_delete": "Off"
  },
  "access_list": [
    "SetTwoStep",
    "AddGroup",
    "AddChannel",
    "AllowTransfer",
    "RemoveGroup",
    "SetGroupJoinLink"
  ]
}
```

## `removeGroup`

Request `input`:

```json
{
  "group_guid": "g0EXAMPLE00000000000000000000007"
}
```

Response (`status` ERROR_GENERIC / `status_det` INVALID_AUTH), `data`:

```json
{
  "status": "ERROR_GENERIC",
  "status_det": "INVALID_AUTH",
  "client_show_message": {
    "link": {
      "type": "alert",
      "alert_data": {
        "message": "از زمان ورود شما بایستی 3 روز گذشته باشد."
      }
    }
  }
}
```

## `requestChangeObjectOwner`

Request `input`:

```json
{
  "object_guid": "g0EXAMPLE00000000000000000000007",
  "new_owner_user_guid": "u0EXAMPLE00000000000000000000001"
}
```

Response (`status` ERROR_GENERIC / `status_det` INVALID_AUTH), `data`:

```json
{
  "status": "ERROR_GENERIC",
  "status_det": "INVALID_AUTH",
  "client_show_message": {
    "link": {
      "type": "alert",
      "alert_data": {
        "message": "از زمان ورود شما بایستی 3 روز گذشته باشد."
      }
    }
  }
}
```

## `requestSendFile`

Request `input`:

```json
{
  "file_name": "2026-03-15T18:26:04.799Z.ogg",
  "size": 1654,
  "mime": "ogg"
}
```

Response (`status` OK / `status_det` OK), `data`:

```json
{
  "id": "87998036915657",
  "dc_id": "491",
  "access_hash_send": "ACCESS_HASH_REMOVED",
  "upload_url": "https://upmessenger491.iranlms.ir/UploadFile.ashx"
}
```

## `searchGlobalObjects`

Request `input`:

```json
{
  "search_text": "sample",
  "filter_types": [
    "Bot"
  ]
}
```

Response (`status` OK / `status_det` OK), `data`:

```json
{
  "objects": [
    {
      "object_guid": "b0EXAMPLE00000000000000000000004",
      "type": "Bot",
      "title": "Sample title",
      "is_verified": false,
      "is_deleted": false,
      "username": "sample_user",
      "track_id": "searchBackend*1"
    },
    {
      "object_guid": "b0EXAMPLE00000000000000000000005",
      "type": "Bot",
      "title": "Sample title",
      "is_verified": false,
      "is_deleted": false,
      "username": "sample_user",
      "track_id": "searchBackend*2"
    },
    {
      "object_guid": "c0EXAMPLE00000000000000000000006",
      "type": "Channel",
      "title": "Sample title",
      "avatar_thumbnail": {
        "file_id": "38362377284747",
        "mime": "jpg",
        "dc_id": "865",
        "access_hash_rec": "ACCESS_HASH_REMOVED"
      },
      "is_verified": true,
      "is_deleted": false,
      "count_members": 9175,
      "username": "sample_user",
      "track_id": "{'l': 'messenger', 'svc': 'search_channel', 'm': 'search', 's': 'Ehsan', 'r': 0, 'ref': '26839627'}"
    }
  ],
  "has_continue": false,
  "timestamp": "1774284489"
}
```

## `seenChats`

Request `input`:

```json
{
  "seen_list": {
    "u0EXAMPLE00000000000000000000001": "1556351220500832"
  }
}
```

Response (`status` OK / `status_det` OK), `data`:

```json
{
  "chat_updates": [
    {
      "object_guid": "u0EXAMPLE00000000000000000000001",
      "action": "Edit",
      "chat": {
        "count_unseen": 0,
        "last_seen_my_mid": "1556351220500832"
      },
      "updated_parameters": [
        "last_seen_my_mid",
        "count_unseen"
      ],
      "timestamp": "1773596166",
      "type": "User"
    }
  ]
}
```

## `sendChatActivity`

Request `input`:

```json
{
  "object_guid": "u0EXAMPLE00000000000000000000001",
  "activity": "Recording"
}
```

Response (`status` OK / `status_det` OK), `data`:

```json
{}
```

## `sendMessage`

Request `input`:

```json
{
  "object_guid": "u0EXAMPLE00000000000000000000002",
  "rnd": "678093",
  "text": "sample text"
}
```

Response (`status` OK / `status_det` OK), `data`:

```json
{
  "message_update": {
    "message_id": "1547993674553407",
    "action": "New",
    "message": {
      "message_id": "1547993674553407",
      "text": "sample text",
      "time": "1773247473",
      "is_edited": false,
      "type": "Text",
      "author_type": "User",
      "author_object_guid": "u0EXAMPLE00000000000000000000002",
      "allow_transcription": false
    },
    "updated_parameters": [],
    "timestamp": "1773247473",
    "prev_message_id": "1546719046885407",
    "object_guid": "u0EXAMPLE00000000000000000000002",
    "type": "User",
    "state": "1773247413",
    "is_scheduled": false
  },
  "status": "OK",
  "chat_update": {
    "object_guid": "u0EXAMPLE00000000000000000000002",
    "action": "Edit",
    "chat": {
      "time_string": "177324747300001547993674553407",
      "last_message": {
        "message_id": "1547993674553407",
        "type": "Text",
        "text": "sample text",
        "author_object_guid": "u0EXAMPLE00000000000000000000002",
        "is_mine": true,
        "author_title": "شما",
        "author_type": "User"
      },
      "last_seen_my_mid": "1547993674553407",
      "last_seen_peer_mid": "0",
      "status": "Active",
      "time": 1773247473,
      "last_message_id": "1547993674553407"
    },
    "updated_parameters": [
      "last_message_id",
      "last_message",
      "status",
      "time_string",
      "last_seen_peer_mid",
      "last_seen_my_mid",
      "time"
    ],
    "timestamp": "1773247473",
    "type": "User"
  }
}
```

## `setChannelAdmin`

Request `input`:

```json
{
  "channel_guid": "c0EXAMPLE00000000000000000000003",
  "member_guid": "u0EXAMPLE00000000000000000000001",
  "action": "SetAdmin",
  "access_list": [
    "ChangeInfo",
    "ViewMembers",
    "ViewAdmins",
    "PinMessages",
    "SendMessages",
    "EditAllMessages",
    "DeleteGlobalAllMessages",
    "AddMember",
    "SetJoinLink",
    "SetAdmin"
  ]
}
```

Response (`status` OK / `status_det` OK), `data`:

```json
{
  "in_chat_member": {
    "member_type": "User",
    "member_guid": "u0EXAMPLE00000000000000000000001",
    "first_name": "Sample",
    "last_name": "User",
    "is_verified": false,
    "is_deleted": false,
    "promoted_by_object_guid": "u0EXAMPLE00000000000000000000002",
    "promoted_by_object_type": "User",
    "join_type": "Admin",
    "username": "sample_user",
    "online_time": {
      "type": "Approximate",
      "approximate_period": "Recently"
    }
  },
  "timestamp": "1774284282"
}
```

## `setGroupAdmin`

Request `input`:

```json
{
  "group_guid": "g0EXAMPLE00000000000000000000007",
  "member_guid": "u0EXAMPLE00000000000000000000001",
  "action": "SetAdmin",
  "access_list": [
    "ChangeInfo",
    "PinMessages",
    "DeleteGlobalAllMessages",
    "BanMember",
    "SetJoinLink",
    "SetAdmin",
    "SetMemberAccess"
  ]
}
```

Response (`status` OK / `status_det` OK), `data`:

```json
{
  "in_chat_member": {
    "member_type": "User",
    "member_guid": "u0EXAMPLE00000000000000000000001",
    "first_name": "Sample",
    "last_name": "User",
    "is_verified": false,
    "is_deleted": false,
    "promoted_by_object_guid": "u0EXAMPLE00000000000000000000002",
    "promoted_by_object_type": "User",
    "join_type": "Admin",
    "username": "sample_user",
    "online_time": {
      "type": "Approximate",
      "approximate_period": "Recently"
    }
  },
  "timestamp": "1774239448"
}
```

(3 recorded variants; only the first request/response pair is shown.)

## `setGroupDefaultAccess`

Request `input`:

```json
{
  "group_guid": "g0EXAMPLE00000000000000000000007",
  "access_list": [
    "ViewMembers",
    "AddMember",
    "SendMessages",
    "ViewAdmins"
  ]
}
```

## `unbanGroupMember`

Request `input`:

```json
{
  "group_guid": "g0EXAMPLE00000000000000000000007",
  "member_guid": "b0EXAMPLE00000000000000000000005",
  "action": "Unset"
}
```

Response (`status` OK / `status_det` OK), `data`:

```json
{
  "timestamp": "1774239304",
  "group": {
    "group_guid": "g0EXAMPLE00000000000000000000007",
    "group_title": "Sample group",
    "count_members": 1,
    "is_deleted": false,
    "is_verified": false,
    "slow_mode": 0,
    "description": "Sample description",
    "chat_history_for_new_members": "Hidden",
    "event_messages": false,
    "chat_reaction_setting": {
      "reaction_type": "All"
    },
    "is_restricted_content": true
  }
}
```

## `unsetChannelAdmin`

Request `input`:

```json
{
  "channel_guid": "c0EXAMPLE00000000000000000000003",
  "member_guid": "u0EXAMPLE00000000000000000000001",
  "action": "UnsetAdmin"
}
```

Response (`status` OK / `status_det` OK), `data`:

```json
{
  "in_chat_member": {
    "member_type": "User",
    "member_guid": "u0EXAMPLE00000000000000000000001",
    "first_name": "Sample",
    "last_name": "User",
    "is_verified": false,
    "is_deleted": false,
    "join_type": "Member",
    "username": "sample_user",
    "online_time": {
      "type": "Approximate",
      "approximate_period": "Recently"
    }
  },
  "timestamp": "1774284708"
}
```

## `unsetGroupAdmin`

Request `input`:

```json
{
  "group_guid": "g0EXAMPLE00000000000000000000007",
  "member_guid": "u0EXAMPLE00000000000000000000001",
  "action": "UnsetAdmin"
}
```
