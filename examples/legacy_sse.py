#!/usr/bin/env python3
"""只支持旧版 HTTP+SSE 的 MCP 客户端怎么接（无需 SDK，纯标准库）。"""
import http.client, json, threading, time, urllib.request

BASE = "https://lucydomi.com"
KEY = "sk-YOUR_KEY"

conn = http.client.HTTPSConnection("lucydomi.com", timeout=60)
conn.request("GET", "/sse", headers={"Accept": "text/event-stream",
                                     "Authorization": "Bearer " + KEY})
resp = conn.getresponse()

endpoint, replies = {}, {}

def reader():
    event = None
    while True:
        line = resp.readline()
        if not line:
            break
        line = line.decode("utf-8", "ignore").strip()
        if line.startswith("event:"):
            event = line.split(":", 1)[1].strip()
        elif line.startswith("data:"):
            data = line[5:].strip()
            if event == "endpoint":
                endpoint["url"] = data
            elif event == "message":
                msg = json.loads(data)
                replies[msg.get("id")] = msg

threading.Thread(target=reader, daemon=True).start()
while "url" not in endpoint:
    time.sleep(0.05)

def send(payload):
    req = urllib.request.Request(BASE + endpoint["url"], data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Bearer " + KEY}, method="POST")
    urllib.request.urlopen(req, timeout=30).read()

send({"jsonrpc": "2.0", "id": 1, "method": "initialize",
      "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                 "clientInfo": {"name": "legacy", "version": "1"}}})
time.sleep(1)
send({"jsonrpc": "2.0", "method": "notifications/initialized"})
send({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
      "params": {"name": "search_creators",
                 "arguments": {"platform": "tiktok", "keyword": "coffee", "limit": 2}}})
time.sleep(3)
print(json.loads(replies[2]["result"]["content"][0]["text"]))
