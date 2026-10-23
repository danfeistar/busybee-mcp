"""多协议接入层 —— 一个服务，四种接法，覆盖所有类型的 AI Agent。

    1. POST /mcp                    MCP Streamable HTTP（Claude Code / Cursor / Cline / 新版 SDK）
    2. GET  /sse + POST /messages/  MCP 旧版 HTTP+SSE（只支持 SSE 的老客户端、自研 agent）
    3. POST /mcp/v1/<tool>          REST + JSON（Dify / n8n / Coze / LangChain / GPT Actions / 任何能发 HTTP 的程序）
    4. stdio                        本地 `busybee-mcp`（Claude Desktop、本机 agent）

    辅助端点：
      GET /mcp/tools                工具清单（?format=openai 直接给 function calling 用）
      GET /mcp/openapi.json         OpenAPI 3.1 描述（GPT Actions / Zapier / Make 导入）
      GET /mcp/info                 发现文档：告诉 agent 这里有哪几种接法
      GET /healthz                  健康检查

鉴权（三种任选，看客户端能力）：
      Authorization: Bearer sk-xxx  |  X-API-Key: sk-xxx  |  ?api_key=sk-xxx（仅 REST）
"""
from __future__ import annotations

import json
import os
import urllib.parse
from contextlib import AsyncExitStack, asynccontextmanager

from . import dispatch
from .client import SIGNUP_URL, Client
from .server import api_key_ctx, server

HOST = os.environ.get("BUSYBEE_HOST", "127.0.0.1")
PORT = int(os.environ.get("BUSYBEE_PORT", "3013"))
MCP_PATH = os.environ.get("BUSYBEE_MCP_PATH", "/mcp")
SSE_PATH = os.environ.get("BUSYBEE_SSE_PATH", "/sse")
MESSAGE_PATH = os.environ.get("BUSYBEE_MESSAGE_PATH", "/messages/")
PUBLIC_BASE = os.environ.get("BUSYBEE_PUBLIC_BASE", "https://lucydomi.com").rstrip("/")
VERSION = "0.2.0"

ALLOWED_HOSTS = [h.strip() for h in os.environ.get(
    "BUSYBEE_ALLOWED_HOSTS",
    "lucydomi.com,www.lucydomi.com,127.0.0.1,127.0.0.1:3013,localhost,localhost:3013",
).split(",") if h.strip()]

CORS_HEADERS = [
    (b"access-control-allow-origin", b"*"),
    (b"access-control-allow-methods", b"GET, POST, DELETE, OPTIONS"),
    (b"access-control-allow-headers",
     b"Authorization, Content-Type, Accept, X-API-Key, api-key, x-busybee-key, "
     b"Mcp-Session-Id, Last-Event-ID, MCP-Protocol-Version"),
    (b"access-control-expose-headers", b"Mcp-Session-Id, MCP-Protocol-Version"),
    (b"access-control-max-age", b"86400"),
]


# ------------------------------------------------------------------ 小工具
def _pick_token(scope) -> str | None:
    headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope.get("headers", [])}
    for name in ("authorization", "x-api-key", "api-key", "x-busybee-key", "x-auth-token"):
        val = (headers.get(name) or "").strip()
        if not val:
            continue
        if val.lower().startswith("bearer "):
            val = val[7:].strip()
        if val:
            return val
    qs = urllib.parse.parse_qs(scope.get("query_string", b"").decode("latin-1"))
    for name in ("api_key", "key", "token"):
        if qs.get(name):
            return qs[name][0].strip()
    return None


def _query(scope) -> dict:
    qs = urllib.parse.parse_qs(scope.get("query_string", b"").decode("latin-1"))
    return {k: v[0] for k, v in qs.items()}


async def _read_json(receive) -> dict:
    body = b""
    while True:
        msg = await receive()
        if msg["type"] == "http.disconnect":
            break
        body += msg.get("body", b"")
        if not msg.get("more_body"):
            break
    if not body:
        return {}
    try:
        data = json.loads(body)
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {"value": data}


async def _json(send, status: int, payload, extra_headers=None):
    body = json.dumps(payload, ensure_ascii=False).encode()
    headers = [(b"content-type", b"application/json; charset=utf-8"),
               (b"content-length", str(len(body)).encode()),
               (b"cache-control", b"no-store")] + list(CORS_HEADERS) + list(extra_headers or [])
    await send({"type": "http.response.start", "status": status, "headers": headers})
    await send({"type": "http.response.body", "body": body})


# ------------------------------------------------------------------ 文档
def _openapi(v3_0: bool = False) -> dict:
    paths = {}
    for name, spec in dispatch.TOOL_SPECS.items():
        props = spec["parameters"].get("properties", {})
        qparams = [{"name": k, "in": "query", "required": False, "schema": v}
                   for k, v in props.items() if v.get("type") in ("string", "integer")]
        paths[f"/mcp/v1/{name}"] = {
            "post": {
                "operationId": name,
                "summary": spec["description"].split("。")[0][:60],
                "description": spec["description"],
                "requestBody": {"required": bool(spec["parameters"].get("required")),
                                "content": {"application/json": {"schema": spec["parameters"]}}},
                "responses": {"200": {"description": "统一字段结果",
                                      "content": {"application/json": {"schema": {"type": "object"}}}}},
            },
            "get": {
                "operationId": name + "Get",
                "summary": spec["description"].split("。")[0][:60],
                "description": spec["description"] + "（GET 版，仅适合参数简单的调用）",
                "parameters": qparams,
                "responses": {"200": {"description": "统一字段结果"}},
            },
        }
    return {
        # 部分导入器（老版 Dify / n8n 节点）只认 3.0.x，用 ?spec=3.0 取 3.0.3 版
        "openapi": "3.0.3" if v3_0 else "3.1.0",
        "info": {"title": "BusyBee Data", "version": VERSION,
                 "description": "Public social media data for AI agents: one normalized schema across "
                                "TikTok, Instagram, YouTube, X, Douyin and Xiaohongshu. Pay per call; "
                                "every response reports cost_usd and balance_usd."},
        "servers": [{"url": PUBLIC_BASE}],
        "components": {"securitySchemes": {
            "bearerAuth": {"type": "http", "scheme": "bearer", "description": "sk- 开头的 API Key"},
            "apiKeyQuery": {"type": "api_key", "in": "query", "name": "api_key"}}},
        "security": [{"bearerAuth": []}, {"apiKeyQuery": []}],
        "paths": paths,
    }


def _info() -> dict:
    return {
        "name": "BusyBee Data",
        "version": VERSION,
        "description": "Public social media data for AI agents — TikTok, Instagram, YouTube, X, Douyin, Xiaohongshu.",
        "transports": {
            "streamable_http": {"url": PUBLIC_BASE + MCP_PATH,
                                "clients": "Claude Code / Cursor / Cline / 支持 MCP 2025-06-18 的 SDK"},
            "sse": {"sse_url": PUBLIC_BASE + SSE_PATH, "message_url": PUBLIC_BASE + MESSAGE_PATH,
                    "clients": "只支持旧版 HTTP+SSE 的 MCP 客户端"},
            "rest": {"url": PUBLIC_BASE + MCP_PATH + "/v1/{tool}",
                     "spec": PUBLIC_BASE + MCP_PATH + "/openapi.json",
                     "clients": "Dify / n8n / Coze / LangChain / GPT Actions / 任何能发 HTTP 的程序"},
            "stdio": {"command": "busybee-mcp", "install": "pip install busybee-mcp",
                      "env": {"BUSYBEE_API_KEY": "sk-..."}, "clients": "Claude Desktop 等本地客户端"},
        },
        "auth": ["Authorization: Bearer sk-...", "X-API-Key: sk-...", "?api_key=sk-...（仅 REST）"],
        "key_page": SIGNUP_URL,
        "tools": [{"name": n, "description": s["description"]} for n, s in dispatch.TOOL_SPECS.items()],
    }


# ------------------------------------------------------------------ 主 ASGI
def build_app():
    from mcp.server.transport_security import TransportSecuritySettings

    # 反向代理后 Host 是我们的域名：放行自己的域名，仍拒绝任意 Host（防 DNS rebinding）
    security = TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=ALLOWED_HOSTS,
        allowed_origins=["https://" + h for h in ALLOWED_HOSTS] + ["http://" + h for h in ALLOWED_HOSTS],
    )
    mcp_app = server.streamable_http_app(streamable_http_path=MCP_PATH, stateless_http=True,
                                        transport_security=security)
    sse_app = server.sse_app(sse_path=SSE_PATH, message_path=MESSAGE_PATH,
                             transport_security=security, host=HOST)

    @asynccontextmanager
    async def lifespan():
        async with AsyncExitStack() as stack:
            # 两套传输各有独立会话管理，启动/关闭都要走到，否则 SSE 侧拿不到 session manager
            await stack.enter_async_context(mcp_app.router.lifespan_context(mcp_app))
            await stack.enter_async_context(sse_app.router.lifespan_context(sse_app))
            yield

    async def app(scope, receive, send):
        if scope["type"] == "lifespan":
            async with lifespan():
                while True:
                    msg = await receive()
                    if msg["type"] == "lifespan.startup":
                        await send({"type": "lifespan.startup.complete"})
                    elif msg["type"] == "lifespan.shutdown":
                        await send({"type": "lifespan.shutdown.complete"})
                        return
            return

        if scope["type"] != "http":
            return

        path, method = scope["path"], scope["method"].upper()

        if method == "OPTIONS":                       # 浏览器型 agent / Web 前端的预检
            await send({"type": "http.response.start", "status": 204, "headers": list(CORS_HEADERS)})
            await send({"type": "http.response.body", "body": b""})
            return

        if path in ("/healthz", "/health"):
            await _json(send, 200, {"ok": True, "service": "busybee-mcp", "version": VERSION,
                                    "transports": ["streamable-http", "sse", "rest", "stdio"],
                                    "tools": len(dispatch.TOOL_SPECS)})
            return

        if path == MCP_PATH + "/info":
            await _json(send, 200, _info())
            return

        if path == MCP_PATH + "/openapi.json":
            want30 = (_query(scope).get("spec") or _query(scope).get("version") or "").startswith("3.0")
            await _json(send, 200, _openapi(v3_0=want30))
            return

        if path == MCP_PATH + "/tools":
            if _query(scope).get("format") in ("openai", "function", "functions"):
                await _json(send, 200, {"tools": dispatch.openai_tools()})
            else:
                await _json(send, 200, {"count": len(dispatch.TOOL_SPECS), "tools": [
                    {"name": n, "description": s["description"], "parameters": s["parameters"]}
                    for n, s in dispatch.TOOL_SPECS.items()]})
            return

        # ---- REST：原生 HTTP+JSON，给不认 MCP 的 agent
        if path.startswith(MCP_PATH + "/v1/"):
            name = path[len(MCP_PATH) + 4:].strip("/")
            token = _pick_token(scope)
            if not token:
                await _json(send, 401, {"ok": False, "error": "no_api_key",
                                        "message": "缺少 API Key：加请求头 Authorization: Bearer sk-...，"
                                                   "或查询串带 ?api_key=sk-...。",
                                        "signup": SIGNUP_URL})
                return
            if method == "POST":
                args = await _read_json(receive)
            elif method == "GET":
                args = _query(scope)
                for k in ("api_key", "key", "token"):
                    args.pop(k, None)
                for k, v in list(args.items()):
                    if isinstance(v, str) and v.isdigit():
                        args[k] = int(v)
            else:
                await _json(send, 405, {"ok": False, "error": "method_not_allowed",
                                        "message": "该端点只支持 GET / POST。"})
                return
            result = dispatch.call_tool(name, args, Client(api_key=token))
            await _json(send, 200 if result.get("ok") else 400, result)
            return

        # ---- 旧版 SSE 传输
        if path.rstrip("/") == SSE_PATH.rstrip("/") or path.startswith(MESSAGE_PATH):
            cvar = api_key_ctx.set(_pick_token(scope) or "")
            try:
                await sse_app(scope, receive, send)
            finally:
                api_key_ctx.reset(cvar)
            return

        # ---- MCP Streamable HTTP（默认）
        if path == MCP_PATH or path.startswith(MCP_PATH + "/"):
            cvar = api_key_ctx.set(_pick_token(scope) or "")
            try:
                await mcp_app(scope, receive, send)
            finally:
                api_key_ctx.reset(cvar)
            return

        await _json(send, 404, {"ok": False, "error": "not_found",
                                "message": "未知路径。可用：%s、%s、%s/v1/<tool>、%s/openapi.json"
                                           % (MCP_PATH, SSE_PATH, MCP_PATH, MCP_PATH)})

    return app


def main() -> None:
    import uvicorn
    uvicorn.run(build_app(), host=HOST, port=PORT,
                log_level=os.environ.get("BUSYBEE_LOG", "warning"))


if __name__ == "__main__":
    main()
