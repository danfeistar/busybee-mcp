#!/usr/bin/env python3
"""BusyBee cookbook #3 — 跨平台同题对比（一个关键词，六个平台一起看）

同一个选题在不同平台的表达方式差得很远。这个脚本把六个平台的搜索结果并排拉出来，
按互动量排序，输出「哪个平台在讨论、谁的互动最高、文案长什么样」的一页摘要。

用法：
    BUSYBEE_API_KEY=sk-... python examples/cookbook_cross_platform.py "coffee"
    BUSYBEE_API_KEY=sk-... python examples/cookbook_cross_platform.py "real estate"

注：国内平台（抖音/小红书）需要账号累计充值满 $30 解锁，未解锁会返回 forbidden，
脚本会跳过并提示，不会让整批任务失败。
"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://lucydomi.com/mcp/v1"
KEY = os.environ.get("BUSYBEE_API_KEY", "")
PLATFORMS = ["tiktok", "youtube", "twitter", "instagram", "douyin", "xiaohongshu"]


def call(tool, **params):
    url = f"{BASE}/{tool}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {KEY}"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.load(r)


def heat(it):
    s = it.get("stats") or {}
    return sum(int(s.get(k) or 0) for k in ("likes", "comments", "shares", "views", "plays"))


def main():
    if not KEY:
        sys.exit("先设置 BUSYBEE_API_KEY")
    keyword = sys.argv[1] if len(sys.argv) > 1 else "coffee"

    # 先问服务端每个平台支持哪些工具，不支持的直接跳过（比如 Instagram 没有关键词搜内容）
    caps = {p["platform"]: p.get("tools", []) for p in call("list_platforms").get("platforms", [])}

    print(f"关键词「{keyword}」六平台横评\n")
    print(f"{'平台':<12}{'条数':<6}{'最高互动':<10}文案")
    print("-" * 78)
    for p in PLATFORMS:
        if "search_posts" not in caps.get(p, []):
            print(f"{p:<12}{'-':<6}{'-':<10}(该平台没有关键词搜内容)")
            continue
        try:
            res = call("search_posts", platform=p, keyword=keyword, limit=10)
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")[:80]
            print(f"{p:<12}{'-':<6}{'-':<10}跳过：HTTP {e.code} {detail}")
            continue
        except Exception as e:
            print(f"{p:<12}{'-':<6}{'-':<10}跳过：{e}")
            continue
        items = res.get("items") or []
        if not items:
            print(f"{p:<12}{0:<6}{'-':<10}(没搜到)")
            continue
        best = max(items, key=heat)
        text = (best.get("text") or "").replace("\n", " ")[:40]
        print(f"{p:<12}{len(items):<6}{heat(best):<10}{text}")

    print("\n提示：跨平台对比时字段是统一的，直接按 items[].stats 排序即可，不用为每个平台写适配。")


if __name__ == "__main__":
    main()
