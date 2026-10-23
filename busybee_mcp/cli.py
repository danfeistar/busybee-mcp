"""命令行入口：默认 stdio；`busybee-mcp http` 起远程服务。"""
from __future__ import annotations

import sys

USAGE = """BusyBee MCP — public social media data for AI agents.

用法:
  busybee-mcp                启动 stdio 服务（给 Claude Desktop / Cline / Continue 等客户端用）
  busybee-mcp http           启动 HTTP 服务（streamable-http，默认 0.0.0.0:8080）
  busybee-mcp --help, -h     显示本帮助
  busybee-mcp --version, -V  显示版本号

环境变量:
  BUSYBEE_API_KEY    必填，形如 sk-xxxxxxxx（在 https://lucydomi.com/sign-up 注册后获取）
  BUSYBEE_BASE_URL   可选，默认 https://lucydomi.com/mcp

客户端配置示例（Claude Desktop）:
  {
    "mcpServers": {
      "busybee": {
        "command": "uvx",
        "args": ["busybee-mcp"],
        "env": { "BUSYBEE_API_KEY": "sk-xxxxxxxx" }
      }
    }
  }

文档: https://lucydomi.com/mcp-guide
"""


def main() -> None:
    args = sys.argv[1:]

    if args and args[0] in ("--help", "-h", "help"):
        print(USAGE)
        return
    if args and args[0] in ("--version", "-V", "-v", "version"):
        from . import __version__

        print(f"busybee-mcp {__version__}")
        return

    mode = args[0] if args else "stdio"
    if mode in ("http", "serve", "streamable-http"):
        from .http_app import main as http_main

        http_main()
        return
    if mode != "stdio":
        print(f"未知子命令: {mode}\n", file=sys.stderr)
        print(USAGE, file=sys.stderr)
        raise SystemExit(2)

    from .server import serve

    serve("stdio")


if __name__ == "__main__":
    main()
