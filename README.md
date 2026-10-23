# BusyBee MCP

**Public social media data for AI agents.** One MCP server, ten business-level tools, one schema — for TikTok, Instagram, YouTube, X (Twitter), Douyin and Xiaohongshu.

Ask your agent *"who are the fastest-growing coffee creators on TikTok right now, and what do their comment sections complain about?"* and it can actually answer, with real data, in one conversation.

```
Platforms   TikTok · Instagram · YouTube · X (Twitter) · Douyin · Xiaohongshu
Transport   MCP Streamable HTTP (remote)  |  stdio (local)
Tools       10
Billing     pay per call, price returned with every response
Endpoint    https://lucydomi.com/mcp
```

---

## Why this exists

Most "social data" APIs hand you 1,000+ raw endpoints and let the model guess. Models pick tools probabilistically: the more tools you expose, the more often they pick wrong, burn calls, and blame the product.

BusyBee exposes **ten tools that match what a person actually wants to know**, and it normalizes every platform into one field set. Your agent doesn't need to learn six different JSON dialects — and you don't pay for its guesses.

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

`get_comment_insights` is the one people keep open: it samples the comments, then returns sentiment split, question ratio, high-frequency phrases and top-liked comments — so the agent can answer *"what do users actually want"* instead of dumping fifty raw rows.

---

## One schema, every platform

```json
{
  "platform": "tiktok",
  "id": "7690199760430566669",
  "url": "https://www.tiktok.com/@creator/video/7690199760430566669",
  "author": { "id": "6948174171005158405", "handle": "goldenbrown.coffee", "name": "Golden Brown Coffee" },
  "text": "Spanish latte, but make it iced",
  "created_at": "2026-10-18T09:12:00Z",
  "stats": { "likes": 41200, "comments": 812, "shares": 2331, "views": 918000, "collects": 5120 },
  "cover": "https://..."
}
```

Every response also carries `cost_usd` and `balance_usd`, so the agent can budget itself and you can see what a task actually cost.

---

## Use it from any MCP client

You need an API key: register at [lucydomi.com](https://lucydomi.com), then *Console → API Keys → New key* (`sk-…`). Overseas platforms and China platforms use different key groups.

### Claude Code

```bash
claude mcp add busybee --transport http https://lucydomi.com/mcp \
  --header "Authorization: Bearer sk-YOUR_KEY"
```

### Cursor / Cline / any client with an MCP JSON config

`~/.cursor/mcp.json`

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

### Claude Desktop (stdio via uvx / pip)

```json
{
  "mcpServers": {
    "busybee": {
      "command": "uvx",
      "args": ["busybee-mcp"],
      "env": { "BUSYBEE_API_KEY": "sk-YOUR_KEY" }
    }
  }
}
```

### Local Python

```bash
pip install busybee-mcp
BUSYBEE_API_KEY=sk-YOUR_KEY busybee-mcp          # stdio
BUSYBEE_API_KEY=sk-YOUR_KEY busybee-mcp http     # streamable-http on :3013
```

---

## Try it without a client

```bash
curl -s https://lucydomi.com/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Authorization: Bearer sk-YOUR_KEY" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call",
       "params":{"name":"search_creators",
                 "arguments":{"platform":"tiktok","keyword":"coffee","limit":3}}}'
```

Python example: [`examples/quickstart.py`](examples/quickstart.py)

---

## Design decisions worth knowing

- **Ten tools, not a thousand.** Call a business intent, not an endpoint.
- **Normalized fields.** `author / text / created_at / stats` mean the same thing on every platform.
- **Pay per call, priced per endpoint.** Cheap calls cost fractions of a cent; heavy ones cost more. The price for each call is visible in your console.
- **Cost transparency inside the tool result.** `cost_usd` + `balance_usd` on every response.
- **Failures are not billed.** A failed upstream call returns an error and costs nothing.
- **Clean errors.** No stack traces, no third-party names, no vendor documentation links leaking into your agent's context.

## Errors you may see

| `error` | Meaning | What to do |
|---|---|---|
| `no_api_key` | No key configured | Set `BUSYBEE_API_KEY` / the `Authorization` header |
| `unauthorized` | Key invalid or deleted | Issue a new key in the console |
| `insufficient_balance` | Out of credit | Top up |
| `forbidden` | Key group doesn't cover that platform | Create a key in the right group |
| `rate_limited` | Too many requests | Back off and retry |
| `upstream_error` | Temporary provider failure | Retry once; not billed |

## Scope and compliance

BusyBee serves **public** social media data only, and only to users **outside mainland China**. Do not use it to build profiles of private individuals, to scrape private accounts, to manipulate engagement, or to train models on personal data without a lawful basis. See the [data policy](https://lucydomi.com/data-policy).

## License

MIT — see [LICENSE](LICENSE). The service itself is hosted and metered; this repository contains the client-side MCP server.

---

## 中文速览

**BusyBee MCP** 把 TikTok、Instagram、YouTube、X、抖音、小红书六个平台的公开数据，压成 **10 个业务级工具 + 一套统一字段**，任何支持 MCP 的 AI 客户端（Claude Code / Cursor / Cline / Claude Desktop）装上就能用。

- 服务地址：`https://lucydomi.com/mcp`（远程，无需本地安装）
- 也可以本地装：`pip install busybee-mcp`
- 计费：按次，每次返回都带本次花费与余额
- 失败不扣费；报错是干净中文/英文，不暴露任何上游信息

注册后在控制台建 `sk-` 开头的密钥即可。
