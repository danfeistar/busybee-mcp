# Cursor / Cline / Windsurf / VS Code / any MCP client

All of these speak **MCP Streamable HTTP**, so they need two things: our URL and a bearer header.

```
URL     https://lucydomi.com/mcp
Header  Authorization: Bearer sk-YOUR_KEY
```

## Cursor

`~/.cursor/mcp.json` (global) or `.cursor/mcp.json` (per project):

```json
{
  "mcpServers": {
    "busybee": {
      "url": "https://lucydomi.com/mcp",
      "headers": {
        "Authorization": "Bearer sk-YOUR_KEY"
      }
    }
  }
}
```

Restart Cursor, then in chat: *"list busybee tools"*.

## Cline (VS Code extension)

Cline stores servers in its own panel: **MCP Servers → Installed → Configure MCP Servers**, which opens `cline_mcp_settings.json`:

```json
{
  "mcpServers": {
    "busybee": {
      "type": "streamableHttp",
      "url": "https://lucydomi.com/mcp",
      "headers": { "Authorization": "Bearer sk-YOUR_KEY" },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

## Windsurf

`~/.codeium/windsurf/mcp_config.json`:

```json
{
  "mcpServers": {
    "busybee": {
      "serverUrl": "https://lucydomi.com/mcp",
      "headers": { "Authorization": "Bearer sk-YOUR_KEY" }
    }
  }
}
```

## VS Code (native MCP support)

`.vscode/mcp.json` in the workspace:

```json
{
  "servers": {
    "busybee": {
      "type": "http",
      "url": "https://lucydomi.com/mcp",
      "headers": { "Authorization": "Bearer sk-YOUR_KEY" }
    }
  }
}
```

## Anything else that takes a URL + header

Same two values. If the client only supports **SSE** (2024-11 era protocol):

```
SSE       https://lucydomi.com/sse
Messages  https://lucydomi.com/messages/
Header    Authorization: Bearer sk-YOUR_KEY
```

## Checking a client is really connected

```bash
curl -s https://lucydomi.com/mcp/info | head -40
```

That document lists every transport URL, the auth header format and the tool inventory — useful when a client's UI says "connected" but no tools show up.

Quick auth smoke test with your own key:

```bash
curl -s -X POST https://lucydomi.com/mcp \
  -H "Authorization: Bearer sk-YOUR_KEY" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"curl","version":"1"}}}'
```

`200` + a `capabilities` payload means the key works. `401 no_api_key` means the header didn't arrive.

Get a key: https://lucydomi.com/sign-up · Try without signing up: https://lucydomi.com/demo
