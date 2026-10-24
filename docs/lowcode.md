# Dify / n8n / Coze / FastGPT — no code

These platforms don't speak MCP. They import an **OpenAPI spec** and turn each endpoint into a tool you can drop into a workflow.

## The spec URL

```
https://lucydomi.com/mcp/openapi.json          # OpenAPI 3.1
https://lucydomi.com/mcp/openapi.json?spec=3.0 # OpenAPI 3.0, for older importers
```

All 20 endpoints carry an `operationId` (10 tools × GET/POST), which is what makes them import cleanly as named tools. Auth is `Authorization: Bearer sk-YOUR_KEY`.

## Dify

1. **Tools → Custom → Create Custom Tool**
2. Schema: **Import from URL** → paste `https://lucydomi.com/mcp/openapi.json?spec=3.0`
   (3.0 is the safer choice — Dify's importer is picky about 3.1)
3. Auth: **API Key → Bearer**, value `sk-YOUR_KEY`
4. Test one operation (`searchCreators`), then Save

In a workflow: **Add Node → Tool → your busybee tool**. Wire a Start variable into `keyword` and read `items` out of the result.

Typical flow: `Start(keyword) → search_posts(tiktok) → LLM summarize → End`.

## n8n

1. **Credentials → New → Header Auth**
   - Name: `Authorization`
   - Value: `Bearer sk-YOUR_KEY`
2. **HTTP Request** node, or install the OpenAPI node:
   - Method: `POST`
   - URL: `https://lucydomi.com/mcp/v1/search_creators`
   - Authentication: Generic → Header Auth → the credential above
   - Body (JSON): `{"platform":"tiktok","keyword":"{{ $json.keyword }}","limit":10}`

Keep `limit` small while building the flow — you're billed per call.

## Coze / FastGPT

Both take an OpenAPI URL in their plugin/tool editors. Same spec URL, same bearer token. If an importer chokes on 3.1, use `?spec=3.0`.

## Tool naming after import

| Endpoint | operationId | Chinese label |
|---|---|---|
| `POST /mcp/v1/search_creators` | `searchCreators` | 搜索达人 |
| `POST /mcp/v1/search_posts` | `searchPosts` | 搜索内容 |
| `POST /mcp/v1/get_creator` | `getCreator` | 达人详情 |
| `POST /mcp/v1/list_creator_posts` | `listCreatorPosts` | 达人作品 |
| `POST /mcp/v1/get_post` | `getPost` | 内容详情 |
| `POST /mcp/v1/get_comments` | `getComments` | 评论列表 |
| `POST /mcp/v1/get_comment_insights` | `getCommentInsights` | 评论洞察 |
| `POST /mcp/v1/get_trending` | `getTrending` | 热榜 |
| `POST /mcp/v1/list_platforms` | `listPlatforms` | 平台清单 |
| `POST /mcp/v1/check_balance` | `checkBalance` | 余额 |

## Response shape (real, not a mock)

`search_posts` returns nested `author` / `stats`:

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

`search_creators` returns **flat** items instead — `handle`, `name`, `followers`, `following`, `posts`, `verified`, `bio`, `avatar`, `url`. So in a workflow, pull `items[0].author.handle` from a post but `items[0].handle` from a creator search.

`get_comment_insights` has no `items` at all; it returns `sentiment{positive,negative,neutral}`, `questions{count,ratio}`, `engagement`, `top_phrases[{phrase,count}]`, `top_liked`, plus a ready-to-paste `summary` string like *"共分析 40 条评论；其中 12 条（30%）是提问，说明购买意图明确；情绪正面为主（正面 8 条 / 负面 0 条）"* — mapping `summary` straight into your LLM node is often enough.

In Dify/n8n the field you usually want is `items` (or `summary` for insights) — map it to your LLM node's context, then ask the model to rank or summarise.

## Gotchas

- **Platform must match your key's plan.** `list_platforms` tells you what your key can reach; calling a platform outside it returns `forbidden — 该分组不含此平台`.
- **Billing is per call**, including a call that returns zero results (the upstream was still queried). Set `limit` deliberately.
- **Long-running calls**: some platforms take 10–30 s. Raise the node timeout to 60 s in n8n / Dify rather than retrying — a retry is a second billed call.

Get a key: https://lucydomi.com/sign-up · Try without signing up: https://lucydomi.com/demo
