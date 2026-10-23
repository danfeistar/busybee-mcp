#!/usr/bin/env bash
# 不装 MCP、不装 SDK —— 直接 HTTP 调（Dify / n8n / 自研程序同款路径）
set -euo pipefail
KEY="${BUSYBEE_API_KEY:?请先 export BUSYBEE_API_KEY=sk-...}"

# 1) 查余额
curl -s https://lucydomi.com/mcp/v1/check_balance -X POST \
  -H "Authorization: Bearer $KEY" -H 'Content-Type: application/json' -d '{}'

# 2) 搜达人（POST + JSON）
curl -s https://lucydomi.com/mcp/v1/search_creators -X POST \
  -H "Authorization: Bearer $KEY" -H 'Content-Type: application/json' \
  -d '{"platform":"tiktok","keyword":"coffee","limit":3}'

# 3) 最受限的场景：只有 GET + 查询串
curl -s "https://lucydomi.com/mcp/v1/search_posts?platform=youtube&keyword=coffee&limit=2&api_key=$KEY"

# 4) 工具清单（OpenAI function calling 格式）
curl -s "https://lucydomi.com/mcp/tools?format=openai"
