# Rubino

Rubino is Rubika's built-in social network. Posts and stories shared into a
chat arrive as messages of type `RubinoPost` with a `rubino_post_data` block;
the Rubino API itself is a plain-JSON service on the host that `getBaseInfo`
suggests (`suggested_rubino`), called with the session `auth` and the PWA
client block.

```python
from rubigram import Client, filters

app = Client("my_account")

@app.on_message(filters.rubino)
async def on_post(client, message):
    result = await client.get_rubino_post(rubino_post_data=message.rubino_post_data)
    post = result.post
    print(post.caption, post.share_url, post.file_type)
    path = await post.download()                 # <post_id>.<ext>
    thumb = await post.download(kind="thumbnail", in_memory=True)

async def main():
    async with app:
        result = await app.get_rubino_post(post_id="…", post_profile_id="…")
        stories = await app.get_rubino_stories(story_id="…", story_profile_id="…")
        await app.send_rubino_post("u0…", post_id="…", post_profile_id="…", text="look")
```

## Methods

| Method | Rubika call | Notes |
|---|---|---|
| `get_base_info()` | `getBaseInfo` on `servicesbase.iranlms.ir` | refreshed automatically after login; stores the suggested Rubino/wallet hosts |
| `get_rubino_post(post_id, post_profile_id)` or `get_rubino_post(rubino_post_data=…)` | `getProfilePosts` (`max_id == min_id == post_id`, `equal: true`) | returns `RubinoPostsResult`; `.post` is the first post |
| `get_rubino_stories(story_id, story_profile_id)` | `getProfilesStoryList` | `RubinoStoriesResult.stories` |
| `send_rubino_post(object_guid, post_id, post_profile_id, text=)` | `sendRubinoPost` | shares a post into a chat |

## Types

`RubinoPost` carries `id`, `profile_id`, `caption`, `share_url`, `file_type`,
`width`, `height`, `duration`, counters and three downloadable `UrlFile`
objects: `file`, `thumbnail` and `snapshot` (built from `full_file_url`,
`full_thumbnail_url` and `full_snapshot_url`). `download()` on any of them
streams the public URL through the download transport (no `auth` is sent).
Multi-file posts expose every item in `file_list`.

## Limits

The Rubino payload shapes were taken from the web client source and from the
owner's earlier recordings; fields that were not observed are kept in
`.extra` rather than typed. Liking, commenting and posting to Rubino are not
implemented.
