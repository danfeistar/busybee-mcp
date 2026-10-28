# BusyBee MCP

[![PyPI](https://img.shields.io/pypi/v/busybee-mcp.svg)](https://pypi.org/project/busybee-mcp/)
[![Python](https://img.shields.io/pypi/pyversions/busybee-mcp.svg)](https://pypi.org/project/busybee-mcp/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Glama score](https://glama.ai/mcp/servers/danfeistar/busybee-mcp/badges/score.svg)](https://glama.ai/mcp/servers/danfeistar/busybee-mcp)
[![BusyBee MCP score on AI Agents Listing](https://aiagentslisting.com/busybee-mcp/badge.svg?variant=score)](https://aiagentslisting.com/mcp/busybee-mcp)
[![MCP Registry](https://img.shields.io/badge/MCP%20Registry-active-6f42c1.svg)](https://registry.modelcontextprotocol.io/v0.1/servers/io.github.danfeistar%2Fbusybee/versions/latest)

**Public social media data for AI agents.** Ten business-level tools, one schema — TikTok, Instagram, YouTube, X (Twitter), Douyin and Xiaohongshu.

Ask your agent *"who are the fastest-growing coffee creators on TikTok right now, and what do their comment sections complain about?"* — it answers with real data, in one conversation.

```
Endpoint    https://lucydomi.com/mcp
Protocols   MCP Streamable HTTP · MCP SSE (legacy) · REST/JSON · stdio
Tools       10
Billing     pay per call; every response returns cost_usd + balance_usd
```

> **Try it in 30 seconds — no signup:** open **https://lucydomi.com/demo**, type a keyword, see the real response shape (6 free calls per device per day, 3 of them on Douyin/Xiaohongshu). When you want unlimited calls, grab a key at https://lucydomi.com/sign-up.

---

## Connect your agent

Step-by-step guides, each with a config file you can copy verbatim:

- [Claude Desktop / Claude Code](docs/claude-desktop.md) — local stdio via `uvx`
- [Cursor / Cline / Windsurf / VS Code](docs/editors.md) — remote HTTP with a bearer header
- [Dify / n8n / Coze / FastGPT](docs/lowcode.md) — import the OpenAPI spec, no code
- [Plain HTTP / curl / any language](docs/rest.md) — REST endpoints and the tools JSON

---

## Works with every kind of agent

Most "social data for AI" products ship one transport and hope your client speaks it. This server speaks four, on the same host, with the same 10 tools behind all of them.

| Your agent | What it supports | How to connect |
|---|---|---|
| **Claude Code** | Streamable HTTP | `claude mcp add busybee --transport http https://lucydomi.com/mcp --header "Authorization: Bearer sk-..."` |
| **Cursor / Cline / Windsurf / VS Code** | Streamable HTTP | add to `mcp.json` (see below) |
| **Claude Desktop** | stdio | `uvx busybee-mcp` with `BUSYBEE_API_KEY` |
| **Older MCP clients (2024-11 era)** | SSE only | `https://lucydomi.com/sse` + `https://lucydomi.com/messages/` |
| **Dify / n8n / Coze / FastGPT** | OpenAPI / plain HTTP | import `https://lucydomi.com/mcp/openapi.json` (3.1), or `?spec=3.0` for older importers |
| **LangChain / LlamaIndex / custom code** | tools JSON or HTTP | `https://lucydomi.com/mcp/tools?format=openai`, or call REST directly |
| **GPT Actions / Zapier / Make** | OpenAPI 3.x | same spec URL, bearer auth |
| **Anything that can only GET a URL** | query string | `https://lucydomi.com/mcp/v1/search_creators?platform=tiktok&keyword=coffee&api_key=sk-...` |

Discovery document (machine-readable, tells an agent what's available): `https://lucydomi.com/mcp/info`

---

## The 10 tools

| Tool | What it answers |
|---|---|
| `list_platforms` | Which platforms exist, which tools each supports, which key group you need |
| `search_creators` | "Find me mid-size coffee creators on TikTok" |
| `search_posts` | "What is being posted about cold brew this week?" |
| `get_creator` | "How big is this account, what's their bio?" |
| `list_creator_posts` | "What has this account posted recently?" |
| `get_post` | "Give me the details of this one video" |
| `get_comments` | "What are people saying under this post?" |
| `get_trending` | "What's trending on Douyin right now?" |
| `get_comment_insights` | "Summarize the comment section: sentiment, questions, complaints" |
| `check_balance` | "How much credit do I have left?" |

`get_comment_insights` is the one people keep open: it samples comments, then returns sentiment split, question ratio, high-frequency phrases and top-liked comments — so the agent answers *"what do users actually want"* instead of dumping fifty raw rows.

---

## Docs by platform, by tool, by client

Each page carries a real captured response and copy-paste code, so you can skip the README once you know what you need:

| Platform | | Tool deep-dive | | Client setup |
|---|---|---|---|---|
| [TikTok](https://lucydomi.com/data/tiktok) | [YouTube](https://lucydomi.com/data/youtube) | [Search posts](https://lucydomi.com/tools/search-posts) | | [Claude Desktop](https://lucydomi.com/use-cases/claude-desktop) |
| [X (Twitter)](https://lucydomi.com/data/twitter) | [Instagram](https://lucydomi.com/data/instagram) | [Comment insights](https://lucydomi.com/tools/comment-insights) | | [Cursor](https://lucydomi.com/use-cases/cursor) |
| [Douyin](https://lucydomi.com/data/douyin) | [Xiaohongshu](https://lucydomi.com/data/xiaohongshu) | [Creator discovery](https://lucydomi.com/tools/creator-discovery) | | [Cline](https://lucydomi.com/use-cases/cline) · [Gemini CLI](https://lucydomi.com/use-cases/gemini-cli) · [Windsurf](https://lucydomi.com/use-cases/windsurf) · [VS Code](https://lucydomi.com/use-cases/vscode) · [Dify](https://lucydomi.com/use-cases/dify) · [n8n](https://lucydomi.com/use-cases/n8n) |

**Tutorials** — end-to-end workflows with real numbers: [mine demand from comments](https://lucydomi.com/guides/comment-research) · [build a creator database](https://lucydomi.com/guides/creator-database) · [cross-platform topic check](https://lucydomi.com/guides/content-calendar) · [competitor monitoring](https://lucydomi.com/guides/competitor-monitor)

All 21 in one index: **https://lucydomi.com/resources** · machine index: **https://lucydomi.com/llms.txt** · everything in one file for LLMs: **https://lucydomi.com/llms-full.txt**

---

## Cookbook — three scripts you can run right now

Stdlib only, no dependencies. Each was run against the live API before being committed; the output below is real.

| Script | Question it answers |
|---|---|
| [`examples/cookbook_comment_insights.py`](examples/cookbook_comment_insights.py) | What is the comment section actually asking? (search → hottest post → insights) |
| [`examples/cookbook_creator_report.py`](examples/cookbook_creator_report.py) | Who are the creators in this niche? (creator search → recent posts → Markdown table) |
| [`examples/cookbook_cross_platform.py`](examples/cookbook_cross_platform.py) | Which platform owns this topic? (one keyword, six platforms, same fields) |

```bash
export BUSYBEE_API_KEY=sk-...
python examples/cookbook_cross_platform.py coffee
```

```
平台          条数    最高互动      文案
tiktok      10    9325976   ASMR SATISFACTION 🤎✨ Nothing beats puck …
youtube     10    235306    The Espresso Revolution is Already Happe…
twitter     10    20988483  NEW: Bikini barista takes out a hammer o…
instagram   -     -         (该平台没有关键词搜内容)
douyin      10    75063     coffee time.#海氏C9Pro咖啡机…
xiaohongshu 10    14623     谁发明的这样喝咖啡？…
```

Note the Instagram row: it reports the gap instead of silently returning nothing — `list_platforms` tells your agent which tools each platform actually supports, so cross-platform jobs degrade instead of breaking.

---

## One schema, every platform

Same field names whether the item came from TikTok, Instagram, YouTube, X, Douyin or Xiaohongshu:

```json
{
  "ok": true, "platform": "tiktok", "tool": "search_posts", "count": 6,
  "items": [
    {
      "platform": "tiktok",
      "id": "7690199760430566669",
      "url": "https://www.tiktok.com/@laceyglasley/video/7690199760430566669",
      "author": { "id": "7066058701889012782", "handle": "laceyglasley", "name": "Lacey" },
      "text": "Salted Honey Spanish Latte … #coffeetok #spanishlatte",
      "created_at": "2026-09-27T13:03:24+00:00",
      "stats": { "likes": 68357, "comments": 165, "shares": 7691, "views": 1009685, "collects": 17806 },
      "cover": "https://…"
    }
  ],
  "cost_usd": 0.003, "balance_usd": 3.93
}
```

**This is a real response, not a mock-up** — captured from a live call, only the share URL query string and the caption were trimmed. Two full raw responses are checked in:
[`examples/1_tiktok_coffee.json`](examples/1_tiktok_coffee.json) (search_posts) and
[`examples/2_youtube_insights.json`](examples/2_youtube_insights.json) (comment insights on 20 comments).

Every response carries `cost_usd` and `balance_usd`, so the agent can budget itself and you can see what a task actually cost.

---

## Setup per client

Need a key first: register at [lucydomi.com](https://lucydomi.com) → *Console → API Keys → New key* (`sk-…`). Overseas and China platforms use different key groups.

### Claude Code
```bash
claude mcp add busybee --transport http https://lucydomi.com/mcp \
  --header "Authorization: Bearer sk-YOUR_KEY"
```

### Cursor / Cline / Windsurf / VS Code (`~/.cursor/mcp.json`)
```json
{
  "mcpServers": {
    "busybee": {
      "url": "https://lucydomi.com/mcp",
      "headers": { "Authorization": "Bearer sk-YOUR_KEY" }
    }
  }
}
```

### Claude Desktop (local stdio)
```json
{
  "mcpServers": {
    "busybee": {
      "command": "uvx",
      "args": ["busybee-mcp"],
      "args": ["busybee-mcp"],
      "env": { "BUSYBEE_API_KEY": "sk-YOUR_KEY" }
    }
  }
}
```

### Legacy SSE clients
```
SSE URL      https://lucydomi.com/sse
Messages URL https://lucydomi.com/messages/?session_id=<from the SSE event>
Header       Authorization: Bearer sk-YOUR_KEY
```

### Dify / n8n / Coze / GPT Actions

Import the OpenAPI schema, set auth to Bearer `sk-YOUR_KEY`. If the importer rejects 3.1, use the 3.0 view.

| Platform | Where to paste | URL |
|---|---|---|
| Dify | Tools → Custom → Add OpenAPI tool | `https://lucydomi.com/mcp/openapi.json?spec=3.0` |
| n8n | HTTP Request node, or import as a credential-protected API | `https://lucydomi.com/mcp/openapi.json` |
| Coze | Plugin → Import from OpenAPI | `https://lucydomi.com/mcp/openapi.json?spec=3.0` |
| OpenAI GPT Actions | Actions → Import from URL | `https://lucydomi.com/mcp/openapi.json` |

Server-side endpoints derive automatically from the schema; each operation maps 1:1 to a tool name, so `search_posts` in the schema is `POST https://lucydomi.com/mcp/v1/search_posts`.

### LangChain / custom Python (no MCP needed)
```python
import json, urllib.request
req = urllib.request.Request(
    "https://lucydomi.com/mcp/v1/search_creators",
    data=json.dumps({"platform": "tiktok", "keyword": "coffee", "limit": 3}).encode(),
    headers={"Content-Type": "application/json", "Authorization": "Bearer sk-YOUR_KEY"},
)
print(json.load(urllib.request.urlopen(req)))
```
Tool schemas for function calling: `GET https://lucydomi.com/mcp/tools?format=openai`

### Local package
```bash
pip install busybee-mcp
BUSYBEE_API_KEY=sk-YOUR_KEY busybee-mcp          # stdio
BUSYBEE_API_KEY=sk-YOUR_KEY busybee-mcp http     # serve all transports on :3013
```

---

## Design decisions worth knowing

- **Ten tools, not a thousand.** Call a business intent, not an endpoint. The more tools a model sees, the more often it picks wrong and burns money.
- **Normalized fields.** `author / text / created_at / stats` mean the same thing on every platform.
- **One implementation behind every protocol.** MCP, SSE and REST share the same dispatch layer, so behavior can't drift between clients.
- **Pay per call, priced per endpoint.** Cheap calls cost fractions of a cent. Price is visible in your console.
- **Cost transparency inside the result.** `cost_usd` + `balance_usd` on every response.
- **Failures are not billed.**
- **Clean errors.** No stack traces, no third-party vendor names, no upstream documentation links leaking into your agent's context.
- **CORS enabled**, so browser-based agents and web widgets can call it directly.

## Errors

| `error` | Meaning | What to do |
|---|---|---|
| `no_api_key` | No key supplied | Add `Authorization: Bearer sk-...`, `X-API-Key`, or `?api_key=` |
| `unauthorized` | Key invalid or deleted | Issue a new key in the console |
| `insufficient_balance` | Out of credit | Top up |
| `forbidden` | Key group doesn't cover that platform | Create a key in the right group |
| `rate_limited` | Too many requests | Back off and retry |
| `unsupported_tool` | That platform doesn't expose the tool | Call `list_platforms` to see the matrix |
| `upstream_error` | Temporary provider failure | Retry once; not billed |

## Scope and compliance

BusyBee serves **public** social media data only, and only to users **outside mainland China**. Do not use it to profile private individuals, scrape private accounts, manipulate engagement, or train models on personal data without a lawful basis. See the [data policy](https://lucydomi.com/data-policy).

## License

MIT — see [LICENSE](LICENSE). This repository is the client-side MCP server; the hosted service is metered separately.

---

## 中文速览

**BusyBee MCP** 把 TikTok、Instagram、YouTube、X、抖音、小红书六个平台的公开数据，压成 **10 个业务级工具 + 一套统一字段**，**同一台服务器支持四种接入方式**：

| 你的 AI 工具 | 接入地址 |
|---|---|
| Claude Code / Cursor / Cline（MCP 新版） | `https://lucydomi.com/mcp` |
| 只认旧版 SSE 的客户端 | `https://lucydomi.com/sse` |
| Dify / n8n / Coze / GPT Actions（OpenAPI） | `https://lucydomi.com/mcp/openapi.json` |
| 任何能发 HTTP 的程序 | `https://lucydomi.com/mcp/v1/<工具名>` |

- 密钥：注册后在控制台建 `sk-` 开头的串
- 计费：按次，每次返回都带本次花费与余额；失败不扣费
- 报错是干净中文/英文，不暴露任何上游信息
