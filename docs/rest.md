# Plain HTTP — curl, Python, Node, Go, anything

MCP is optional. Everything below is ordinary HTTPS + JSON, so it works from any language, any cron job, any spreadsheet script.

## Auth

Three equivalent forms:

```bash
-H "Authorization: Bearer sk-YOUR_KEY"     # preferred
-H "X-API-Key: sk-YOUR_KEY"
?api_key=sk-YOUR_KEY                        # query string, GET only
```

Requests without a key get `401` and a `no_api_key` body — including on the MCP transport endpoints, so monitoring tools can tell "up" from "reachable but unauthenticated".

## Call a tool

```bash
curl -s -X POST https://lucydomi.com/mcp/v1/search_creators \
  -H "Authorization: Bearer sk-YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"platform":"tiktok","keyword":"coffee","limit":5}'
```

Or, when all you have is a browser/`<img>`/`fetch` with no headers:

```bash
curl -s "https://lucydomi.com/mcp/v1/search_creators?platform=tiktok&keyword=coffee&limit=5&api_key=sk-YOUR_KEY"
```

Same tool, `GET`, everything in the query string.

## Python

```python
import requests

KEY = "sk-YOUR_KEY"
BASE = "https://lucydomi.com/mcp/v1"

def call(tool: str, **args):
    r = requests.post(f"{BASE}/{tool}", json=args,
                      headers={"Authorization": f"Bearer {KEY}"}, timeout=60)
    r.raise_for_status()
    data = r.json()
    if not data.get("ok"):
        raise RuntimeError(data)
    return data

creators = call("search_creators", platform="tiktok", keyword="coffee", limit=10)
for it in creators["items"]:          # search_creators items are flat
    print(it["handle"], it["followers"])

insight = call("get_comment_insights", platform="tiktok",
               post_id=creators["items"][0]["id"], sample=60)
print(insight["sentiment"]["positive"], insight["top_phrases"][:5])
```

## Node / TypeScript

```ts
const res = await fetch("https://lucydomi.com/mcp/v1/search_posts", {
  method: "POST",
  headers: {
    Authorization: `Bearer ${process.env.BUSYBEE_API_KEY}`,
    "Content-Type": "application/json",
  },
  body: JSON.stringify({ platform: "youtube", keyword: "espresso machine", limit: 10 }),
});
const data = await res.json();
if (!data.ok) throw new Error(JSON.stringify(data));
console.log(data.count, data.items[0]?.author?.handle);
```

## Go

```go
body := strings.NewReader(`{"platform":"tiktok","keyword":"coffee","limit":5}`)
req, _ := http.NewRequest("POST", "https://lucydomi.com/mcp/v1/search_creators", body)
req.Header.Set("Authorization", "Bearer "+os.Getenv("BUSYBEE_API_KEY"))
req.Header.Set("Content-Type", "application/json")
resp, err := (&http.Client{Timeout: 60 * time.Second}).Do(req)
```

## Response contract

Every successful call:

```json
{
  "ok": true,
  "platform": "tiktok",
  "tool": "search_posts",
  "count": 1,
  "items": [
    {
      "platform": "tiktok",
      "id": "7690199760430566669",
      "url": "https://www.tiktok.com/@laceyglasley/video/7690199760430566669",
      "author": { "id": "7066058701889012782", "handle": "laceyglasley", "name": "Lacey" },
      "text": "One for me, one for you — Salted Honey Spanish Latte",
      "created_at": 1750000000,
      "stats": { "likes": 1200, "comments": 45, "shares": 12, "views": 32000, "collects": 88 },
      "cover": "https://..."
    }
  ],
  "cost_usd": 0.003,
  "balance_usd": 3.92
}
```

Field nesting differs by tool — worth checking once per tool rather than assuming:

- `search_posts` / `list_creator_posts` / `get_post` → items carry nested `author` and `stats`
- `search_creators` / `get_creator` → items are **flat**: `handle`, `name`, `followers`, `following`, `posts`, `verified`, `bio`, `avatar`, `url`
- `get_comment_insights` → not `items` at all, but `total`, `sentiment{positive,negative,neutral}`, `questions{count,ratio}`, `engagement`, `top_phrases[{phrase,count}]`, `top_liked`, `summary`, `sampled`

Every failure is still JSON, with `ok: false` plus `error` / `message`, and a matching HTTP status:

| HTTP | `error` | Meaning |
|---|---|---|
| 401 | `no_api_key` | no key on the request |
| 400 | `unauthorized` | key invalid or deleted |
| 400 | `forbidden` | key's plan doesn't include that platform |
| 400 | `unknown_tool` | unknown tool name (the body lists the valid ones) |
| 400 | anything else | upstream/platform rejected the query — `message` says why |

`balance_usd` is your remaining credit after the call — no separate billing API to poll.

## Machine-readable discovery

| URL | What it gives you |
|---|---|
| `/mcp/info` | transports, auth header format, tool inventory |
| `/mcp/tools` | tool schemas (JSON Schema) |
| `/mcp/tools?format=openai` | the same as OpenAI function-calling definitions |
| `/mcp/openapi.json` | full OpenAPI spec (`?spec=3.0` for older importers) |
| `/healthz` | liveness, no auth needed |

## Retries

Don't blind-retry. A retry is a second billed call. Two exceptions that are safe:

- `5xx` from the gateway (our side failed before reaching upstream)
- `message` containing "Please retry" — that's an upstream hiccup, one retry usually clears it

Cap retries at 1 and back off 2 s.

Get a key: https://lucydomi.com/sign-up · Try without signing up: https://lucydomi.com/demo
