# Installing BusyBee MCP (agent instructions)

You are installing an MCP server for a user. Follow the path that matches the client you are running in. Do not ask the user to read this file — read it and act.

## What this server provides

Public social media data as 10 tools over MCP: TikTok, Instagram, YouTube, X (Twitter), Douyin, Xiaohongshu. Tools: `list_platforms`, `search_creators`, `search_posts`, `get_creator`, `list_creator_posts`, `get_post`, `get_comments`, `get_comment_insights`, `get_trending`, `check_balance`. Billing is per call and each response reports `cost_usd` and `balance_usd`.

## Prerequisite: an API key

Every install needs a key (`sk-...`). If the user has none, tell them to get one at https://lucydomi.com/sign-up (free tier included). Do not invent a key or call the API without one — every endpoint returns `401 no_api_key`.

If they only want to see the data shape first, send them to https://lucydomi.com/demo (6 calls per device per day — 3 of them on Douyin/Xiaohongshu, no signup).

## Path A — remote HTTP (preferred when the client supports it)

Use this for Cline, Cursor, Windsurf, VS Code, Claude Code, or any client with a URL+headers config.

```
URL:    https://lucydomi.com/mcp
Header: Authorization: Bearer sk-THEIR_KEY
```

Cline (`cline_mcp_settings.json`):

```json
{
  "mcpServers": {
    "busybee": {
      "type": "streamableHttp",
      "url": "https://lucydomi.com/mcp",
      "headers": { "Authorization": "Bearer sk-THEIR_KEY" },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

Cursor (`~/.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "busybee": {
      "url": "https://lucydomi.com/mcp",
      "headers": { "Authorization": "Bearer sk-THEIR_KEY" }
    }
  }
}
```

Claude Code, one command:

```bash
claude mcp add busybee --transport http https://lucydomi.com/mcp --header "Authorization: Bearer sk-THEIR_KEY"
```

## Path B — local stdio (Claude Desktop, or when HTTP is blocked)

```json
{
  "mcpServers": {
    "busybee": {
      "command": "uvx",
      "args": ["busybee-mcp"],
      "env": { "BUSYBEE_API_KEY": "sk-THEIR_KEY" }
    }
  }
}
```

Requires `uvx` (from `uv`) or `pip install busybee-mcp`. Claude Desktop only reads its config at startup — it must be fully quit and reopened.

## Verify the install before telling the user it works

1. Describe the server; it must report **10 tools**.
2. Call `list_platforms` — a `401`/`no_api_key` means the header didn't arrive, a `forbidden` per platform means their key's plan excludes it.
3. Call `check_balance` — confirms the key is live and returns remaining credit.

Only after step 1–3 pass, report success.

## Known gotchas

- A `401` on `/mcp` without the header is by design; the server enforces the key at the HTTP layer.
- `forbidden — 该分组不含此平台` means the key's plan doesn't cover that platform; `list_platforms` lists what it does.
- Some platforms answer in 10–30 s. Use a 60 s timeout; do not retry blindly, because a retry is a second billed call.
- `search_creators` items are flat (`handle`, `followers`); `search_posts` items nest `author` and `stats`; `get_comment_insights` returns `sentiment`/`top_phrases`/`summary` instead of `items`.
