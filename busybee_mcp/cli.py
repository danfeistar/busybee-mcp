"""命令行入口：默认 stdio；`busybee-mcp http` 起远程服务。"""
from __future__ import annotations

import sys


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "stdio"
    if mode in ("http", "serve", "streamable-http"):
        from .http_app import main as http_main

        http_main()
        return
    from .server import serve

    serve("stdio")


if __name__ == "__main__":
    main()
