# Claude Desktop / Claude Code

Two ways in. Pick the one that matches how you use Claude.

## Claude Code (CLI) — remote HTTP, one command

```bash
claude mcp add busybee --transport http https://lucydomi.com/mcp \
  --header "Authorization: Bearer sk-YOUR_KEY"
```

Then ask: *"use busybee to find coffee creators on TikTok with the most engagement"*.

Check it registered:

```bash
claude mcp list
```

## Claude Desktop — local stdio, no key in any URL

Claude Desktop launches a local process, which is the more reliable option on desktop.

Edit `claude_desktop_config.json`:

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "busybee": {
      "command": "uvx",
      "args": ["busybee-mcp"],
      "env": {
        "BUSYBEE_API_KEY": "sk-YOUR_KEY"
      }
    }
  }
}
```

`uvx` ships with [uv](https://docs.astral.sh/uv/). No `uvx`? Use `pip install busybee-mcp` and set `"command": "busybee-mcp"` instead.

Fully quit and reopen Claude Desktop — it only reads this file at startup. The hammer icon in the input box should list 10 busybee tools.

## Verify before you wire it in

```bash
BUSYBEE_API_KEY=sk-YOUR_KEY uvx busybee-mcp --version    # 0.2.3
BUSYBEE_API_KEY=sk-YOUR_KEY uvx busybee-mcp              # speaks stdio, Ctrl-C to exit
```

## What the tools are called

| Tool | Arguments | Answers |
|---|---|---|
| `list_platforms` | — | which platforms your key can reach |
| `search_creators` | `platform`, `keyword`, `limit` | accounts matching a keyword, with follower counts |
| `search_posts` | `platform`, `keyword`, `limit` | posts/videos matching a keyword, with engagement |
| `get_creator` | `platform`, `creator` | one account's profile |
| `list_creator_posts` | `platform`, `creator`, `limit` | an account's recent posts |
| `get_post` | `platform`, `post_id` | one post's detail |
| `get_comments` | `platform`, `post_id`, `limit` | comment list |
| `get_comment_insights` | `platform`, `post_id`, `sample` | sentiment, questions, top phrases from comments |
| `get_trending` | `platform`, `limit` | trending board |
| `check_balance` | — | remaining credit |

Platform values: `tiktok`, `instagram`, `youtube`, `twitter`, `douyin`, `xiaohongshu`.

## Troubleshooting

| Symptom | Cause |
|---|---|
| `401` / `no_api_key` | key missing, or not starting with `sk-` |
| `forbidden — 该分组不含此平台` | your key's plan doesn't include that platform (try `list_platforms`) |
| Tools appear but every call fails | key revoked or out of credit — `check_balance` |
| Desktop shows no tools | config file not valid JSON, or Claude wasn't fully restarted |

Get a key: https://lucydomi.com/sign-up · Try without signing up: https://lucydomi.com/demo
