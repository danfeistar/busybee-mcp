# BusyBee MCP — agent context

This extension connects you to **BusyBee MCP**: public social media data for TikTok, Instagram, YouTube, X (Twitter), Douyin and Xiaohongshu, exposed as 10 MCP tools.

## Setup

`BUSYBEE_API_KEY` must be exported in the environment before starting Gemini CLI:

```bash
export BUSYBEE_API_KEY=sk-YOUR_KEY     # get one at https://lucydomi.com/sign-up
```

Without a key every call returns `401 no_api_key`. Want to see the data shape first? https://lucydomi.com/demo needs no signup.

## Tools

| Tool | Use it for |
|---|---|
| `list_platforms` | what this key can reach |
| `search_creators` | find accounts by keyword (flat items: `handle`, `followers`, …) |
| `search_posts` | find posts/videos by keyword (nested `author`, `stats`) |
| `get_creator` / `list_creator_posts` | one account, its recent posts |
| `get_post` / `get_comments` | one post, its comments |
| `get_comment_insights` | sentiment, question ratio, top phrases, one-line summary |
| `get_trending` | trending board |
| `check_balance` | remaining credit |

Platform values: `tiktok`, `instagram`, `youtube`, `twitter`, `douyin`, `xiaohongshu`.

## Habits that save money

- Billing is per call, including calls that return zero results. Set `limit` deliberately.
- Do not retry blindly; a retry is a second billed call. Only retry on `5xx` or a `Please retry` message, once.
- Call `list_platforms` once per session rather than guessing which platforms the key covers.
- `check_balance` is cheap and the right way to confirm credit is left before a bulk run.
