#!/usr/bin/env python3
"""BusyBee cookbook #1 — 评论区到底在问什么（选题调研最常用的一步）

做选题时真正值钱的不是"有多少点赞"，而是评论区在问什么、在抱怨什么。
这个脚本一条命令跑完：搜关键词 → 取互动最高的一条 → 拉评论洞察 → 打印结论。

用法：
    BUSYBEE_API_KEY=sk-... python examples/cookbook_comment_insights.py "coffee" tiktok
    BUSYBEE_API_KEY=sk-... python examples/cookbook_comment_insights.py "昆明 楼盘" douyin

只用标准库，不装任何依赖。
"""
import json
import os
import sys
import urllib.parse
import urllib.request

BASE = "https://lucydomi.com/mcp/v1"
KEY = os.environ.get("BUSYBEE_API_KEY", "")


def call(tool, **params):
    """GET 形式调用：参数放 query string，返回 dict。"""
    url = f"{BASE}/{tool}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {KEY}"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.load(r)


def main():
    if not KEY:
        sys.exit("先设置 BUSYBEE_API_KEY（在 https://lucydomi.com/pricing 注册后创建令牌）")
    keyword = sys.argv[1] if len(sys.argv) > 1 else "coffee"
    platform = sys.argv[2] if len(sys.argv) > 2 else "tiktok"

    found = call("search_posts", platform=platform, keyword=keyword, limit=10)
    items = found.get("items") or []
    if not items:
        sys.exit(f"「{keyword}」在 {platform} 上没搜到内容，换个词试试")
    print(f"关键词「{keyword}」在 {platform} 上搜到 {found.get('count')} 条\n")

    # 按互动量排序，取最热的一条去挖评论
    def heat(it):
        s = it.get("stats") or {}
        return sum(int(s.get(k) or 0) for k in ("likes", "comments", "shares", "views", "plays"))

    top = max(items, key=heat)
    st = top.get("stats") or {}
    print("最热一条：")
    print(f"  作者  {((top.get('author') or {}).get('name'))}")
    print(f"  文案  {(top.get('text') or '')[:80]}")
    print(f"  互动  {st}")
    print(f"  链接  {top.get('url')}\n")

    ins = call("get_comment_insights", platform=platform, post_id=top["id"], sample=30)
    print("评论洞察：")
    print("  总结     ", ins.get("summary"))
    print("  情绪分布 ", ins.get("sentiment"))
    print("  提问占比 ", ins.get("questions"))
    print("  高频词   ", ins.get("top_phrases"))
    likes = (ins.get("top_liked") or [])[:3]
    if likes:
        print("  高赞评论：")
        for c in likes:
            txt = c.get("text") if isinstance(c, dict) else str(c)
            print("    ·", (txt or "")[:90])


if __name__ == "__main__":
    main()
