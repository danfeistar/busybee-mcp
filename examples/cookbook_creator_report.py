#!/usr/bin/env python3
"""BusyBee cookbook #2 — 竞品/达人档案批量建库

给一个关键词和平台，拉一批账号（粉丝数、简介、认证情况），再逐个拉最近作品，
最后输出一张 Markdown 表格，可以直接贴进周报或 Notion。

用法：
    BUSYBEE_API_KEY=sk-... python examples/cookbook_creator_report.py tiktok coffee 5
    BUSYBEE_API_KEY=sk-... python examples/cookbook_creator_report.py xiaohongshu "昆明 买房" 5

每个账号会消耗一次 get_creator + 一次 list_creator_posts，注意按次计费。
"""
import json
import os
import sys
import urllib.parse
import urllib.request

BASE = "https://lucydomi.com/mcp/v1"
KEY = os.environ.get("BUSYBEE_API_KEY", "")


def call(tool, **params):
    url = f"{BASE}/{tool}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {KEY}"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.load(r)


def fmt(n):
    n = int(n or 0)
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(n)


def main():
    if not KEY:
        sys.exit("先设置 BUSYBEE_API_KEY")
    platform = sys.argv[1] if len(sys.argv) > 1 else "tiktok"
    keyword = sys.argv[2] if len(sys.argv) > 2 else "coffee"
    limit = int(sys.argv[3]) if len(sys.argv) > 3 else 5

    res = call("search_creators", platform=platform, keyword=keyword, limit=limit)
    creators = res.get("items") or []
    if not creators:
        sys.exit(f"「{keyword}」在 {platform} 上没搜到达人")

    rows = []
    for c in creators:
        handle = c.get("handle") or c.get("name")
        try:
            posts = call("list_creator_posts", platform=platform, creator=handle, limit=5)
            items = posts.get("items") or []
        except Exception as e:  # 单个账号失败不影响整表
            items = []
            print(f"  ! {handle} 拉作品失败：{e}", file=sys.stderr)
        def heat(it):
            s = it.get("stats") or {}
            return sum(int(s.get(k) or 0) for k in ("likes", "comments", "shares", "views", "plays"))
        best = max(items, key=heat) if items else {}
        rows.append({
            "handle": handle,
            "name": c.get("name") or "",
            "followers": fmt(c.get("followers")),
            "verified": "✅" if c.get("verified") else "",
            "posts": len(items),
            "top_engagement": fmt(heat(best)) if best else "-",
            "top_text": (best.get("text") or "")[:46].replace("|", "/").replace("\n", " "),
        })

    print(f"\n### {platform} · 关键词「{keyword}」达人档案（{len(rows)} 个）\n")
    print("| 账号 | 昵称 | 粉丝 | 认证 | 近 5 条最高互动 | 代表作 |")
    print("|---|---|---|---|---|---|")
    for r in rows:
        print(f"| {r['handle']} | {r['name'][:18]} | {r['followers']} | {r['verified']} "
              f"| {r['top_engagement']} | {r['top_text']} |")


if __name__ == "__main__":
    main()
