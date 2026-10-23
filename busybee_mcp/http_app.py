"""远程接入入口：Streamable HTTP（MCP 规范）+ Bearer API Key。

部署为独立进程，监听 127.0.0.1:3013，由反向代理对外暴露 /mcp。
"""
from __future__ import annotations

import json
import os

from .server import api_key_ctx, server

MCP_PATH = os.environ.get("BUSYBEE_MCP_PATH", "/mcp")
ALLOWED_HOSTS = [h.strip() for h in os.environ.get(
    "BUSYBEE_ALLOWED_HOSTS",
    "lucydomi.com,www.lucydomi.com,127.0.0.1,127.0.0.1:3013,localhost,localhost:3013",
).split(",") if h.strip()]


def _pick_token(headers: dict[str, str]) -> str | None:
    auth = headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        tok = auth[7:].strip()
        if tok:
            return tok
    for name in ("x-api-key", "api-key", "x-busybee-key"):
        v = (headers.get(name) or "").strip()
        if v:
            return v
    return None


async def _send_json(send, status: int, payload: dict) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode()
    await send({"type": "http.response.start", "status": status,
                "headers": [(b"content-type", b"application/json; charset=utf-8"),
                            (b"content-length", str(len(body)).encode())]})
    await send({"type": "http.response.body", "body": body})


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

    async def app(scope, receive, send):
        if scope["type"] == "lifespan":
            await mcp_app(scope, receive, send)
            return
        if scope["type"] != "http":
            await mcp_app(scope, receive, send)
            return
        path = scope.get("path", "")
        if path in ("/healthz", "/__busybee/health"):
            await _send_json(send, 200, {"ok": True, "service": "busybee-mcp", "path": MCP_PATH})
            return
        headers = {k.decode().lower(): v.decode() for k, v in (scope.get("headers") or [])}
        token = api_key_ctx.set(_pick_token(headers))
        try:
            await mcp_app(scope, receive, send)
        finally:
            api_key_ctx.reset(token)

    return app


def main() -> None:
    import uvicorn

    host = os.environ.get("BUSYBEE_HOST", "127.0.0.1")
    port = int(os.environ.get("BUSYBEE_PORT", "3013"))
    uvicorn.run(build_app(), host=host, port=port, log_level=os.environ.get("BUSYBEE_LOG", "info"))


if __name__ == "__main__":
    main()
