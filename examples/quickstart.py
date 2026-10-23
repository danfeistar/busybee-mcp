#!/usr/bin/env python3
"""BusyBee MCP quickstart — no dependencies beyond the stdlib.

Usage:
    BUSYBEE_API_KEY=sk-... python examples/quickstart.py
"""
import json
import os
import urllib.request

URL = "https://lucydomi.com/mcp"
KEY = os.environ["BUSYBEE_API_KEY"]
HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
    "Authorization": "Bearer " + KEY,
}
_id = 0


def rpc(method, params=None):
    global _id
    _id += 1
    body = {"jsonrpc": "2.0", "id": _id, "method": method, "params": params or {}}
    req = urllib.request.Request(URL, data=json.dumps(body).encode(), headers=HEADERS, method="POST")
    with urllib.request.urlopen(req, timeout=90) as r:
        raw = r.read().decode()
    for line in raw.splitlines():          # streamable HTTP replies as SSE
        if line.startswith("data:"):
            return json.loads(line[5:])
    return json.loads(raw)


def call(tool, **arguments):
    res = rpc("tools/call", {"name": tool, "arguments": arguments})
    return json.loads(res["result"]["content"][0]["text"])


if __name__ == "__main__":
    print(call("check_balance"))

    creators = call("search_creators", platform="tiktok", keyword="coffee", limit=3)
    for c in creators["items"]:
        print(f'{c["handle"]:<28} {c["followers"]:>10,} followers')
    print("cost:", creators.get("cost_usd"), "balance:", creators.get("balance_usd"))

    # pick the first post of the first creator, then read its comment section
    posts = call("list_creator_posts", platform="tiktok", creator=creators["items"][0]["handle"], limit=1)
    if posts["items"]:
        insight = call("get_comment_insights", platform="tiktok", post_id=posts["items"][0]["id"])
        print("\n", insight["summary"])
        print(" top phrases:", ", ".join(p["phrase"] for p in insight["top_phrases"][:5]))
