"""BusyBee MCP 服务 —— 9 个业务级工具，统一字段，按次计费。

设计要点：
1. 不把底层上千个接口直接暴露给 AI：工具越少，AI 选对的概率越高。
2. 所有返回都是同一套字段（见 normalize.py），AI 不需要学平台差异。
3. 每次调用回报本次花费与余额，方便 AI 自己控制预算。
"""
from __future__ import annotations

import contextvars
import os
from typing import Any

from mcp.server import MCPServer

from . import insights, registry
from .client import SIGNUP_URL, BusyBeeError, Client
from .normalize import normalize
from .util import dig

VERSION = "0.1.0"
MAX_LIMIT = 50

# 远程模式：HTTP 头里的 API Key 通过 contextvar 传进来
api_key_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar("busybee_api_key", default=None)

server = MCPServer(
    name="busybee",
    title="BusyBee Data",
    version=VERSION,
    description="Public social media data for AI agents: TikTok, Instagram, YouTube, X, Douyin, Xiaohongshu.",
    instructions=(
        "BusyBee Data gives you one normalized way to read public social media data.\n"
        "Pick a platform first (tiktok / instagram / youtube / twitter / douyin / xiaohongshu), "
        "then use search_creators to find accounts, search_posts to find content, "
        "get_comments + get_comment_insights to understand what audiences say.\n"
        "All money is pay-per-call; each response reports cost_usd and balance_usd. "
        "If you get code=insufficient_balance, tell the user to top up at " + SIGNUP_URL + "."
    ),
)


def _client() -> Client:
    return Client(api_key=api_key_ctx.get() or os.environ.get("BUSYBEE_API_KEY")
                  or os.environ.get("XMF_API_KEY"))


def _build_params(spec: dict, args: dict, forced: dict | None = None) -> tuple[dict, dict | None]:
    params, body = {}, {}
    for k, v in (forced or {}).items():
        if v not in (None, ""):
            (body if spec.get("body") else params)[k] = v
    for arg_name, api_name in spec.get("params", {}).items():
        if api_name is None:
            continue
        val = args.get(arg_name)
        if val in (None, ""):
            continue
        (body if spec.get("body") else params)[api_name] = val
    if spec.get("body"):
        body.setdefault("cursor", 0)
        body.setdefault("search_id", "")
        return params, body
    return params, None


def _extract(j: dict, spec: dict, limit: int) -> list[dict]:
    list_path, item_path, kind = spec.get("list"), spec.get("item"), spec["kind"]
    platform = spec["platform"]
    if list_path is None:
        obj = dig(j, item_path or "data", default={}) or {}
        return [normalize(platform, kind, obj)] if isinstance(obj, dict) and obj else []
    arr = dig(j, list_path, default=[]) or []
    if isinstance(arr, dict):
        arr = list(arr.values())
    out = []
    for i, el in enumerate(arr[:limit]):
        obj = dig(el, item_path, default=el) if item_path else el
        if isinstance(obj, dict) and obj:
            out.append(normalize(platform, kind, obj, index=i))
    return out


def _run(platform: str, tool: str, args: dict, limit: int = 20) -> dict:
    platform = (platform or "").strip().lower()
    if platform not in registry.PLATFORMS:
        return {"ok": False, "error": "unknown_platform",
                "message": "不认识的平台「%s」。可用：%s" % (platform, "、".join(registry.PLATFORMS)),
                "platforms": {k: v["label"] for k, v in registry.PLATFORMS.items()}}
    try:
        spec = registry.spec_for(platform, tool)
    except KeyError as e:
        return {"ok": False, "error": "unsupported_tool", "message": str(e).strip('"')}
    spec = dict(spec, platform=platform)
    limit = max(1, min(int(limit or 20), MAX_LIMIT))
    args = {**args, "limit": limit}

    forced = None
    if tool == "get_creator":
        try:
            forced = registry.resolve_creator(platform, str(args.get("creator") or ""))
        except ValueError as e:
            return {"ok": False, "error": "bad_argument", "message": str(e)}

    client = _client()
    bal_before = client.balance_usd()
    try:
        params, body = _build_params(spec, args, forced)
        j = client.call_endpoint(spec["path"], params=params, method=spec.get("method", "GET"), body=body)
    except BusyBeeError as e:
        return e.as_dict()

    items = _extract(j, spec, limit)
    bal_after = client.balance_usd(fresh=True)
    cost = None
    if bal_before is not None and bal_after is not None:
        cost = round(max(0.0, bal_before - bal_after), 4)

    out: dict[str, Any] = {
        "ok": True,
        "platform": platform,
        "tool": tool,
        "count": len(items),
        "items": items,
    }
    if cost is not None:
        out["cost_usd"] = cost
        out["balance_usd"] = bal_after
    if not items:
        out["note"] = "调用成功但没有取到数据：可能是关键词太窄、该账号无公开内容，或该接口需要其它参数。"
    return out


# ------------------------------------------------------------------ 工具
@server.tool(description="列出可用的平台、每个平台支持哪些操作，以及该怎么选。首次使用先调这个。")
def list_platforms() -> dict:
    rows = []
    for pid, meta in registry.PLATFORMS.items():
        tools = sorted({t for (p, t) in registry.SPEC if p == pid})
        rows.append({
            "platform": pid,
            "label": meta["label"],
            "region": "海外" if meta["region"] == "overseas" else "国内",
            "tools": tools,
            "key_group": meta["group"],
        })
    return {"ok": True, "count": len(rows), "platforms": rows,
            "note": "国内平台（douyin / xiaohongshu）需要用国内分组的 API Key；海外平台用海外分组。"}


@server.tool(description="按关键词搜索社媒账号/达人。返回 id、handle、昵称、粉丝数、简介——拿到 handle 或 id 后再用 get_creator / list_creator_posts 深入。")
def search_creators(platform: str, keyword: str, limit: int = 10) -> dict:
    return _run(platform, "search_creators", {"keyword": keyword}, limit)


@server.tool(description="搜索内容：给关键词，返回帖子/视频列表（统一字段：作者、文案、时间、点赞/评论/播放）。适合“某个话题最近在火什么”。")
def search_posts(platform: str, keyword: str, limit: int = 20) -> dict:
    return _run(platform, "search_posts", {"keyword": keyword}, limit)


@server.tool(description="查单个账号的详情（粉丝数、简介、作品数）。creator 填 handle（如 @nasa 去掉@）或平台 id。")
def get_creator(platform: str, creator: str) -> dict:
    return _run(platform, "get_creator", {"creator": str(creator).lstrip("@")}, 1)


@server.tool(description="拉某个账号最近发布的作品列表。creator 填 handle 或平台 id。")
def list_creator_posts(platform: str, creator: str, limit: int = 20) -> dict:
    return _run(platform, "list_creator_posts", {"creator": str(creator).lstrip("@")}, limit)


@server.tool(description="查单条内容的详情。post_id 填平台的内容 id；TikTok/抖音也可传视频链接里的数字 id。")
def get_post(platform: str, post_id: str) -> dict:
    return _run(platform, "get_post", {"post_id": str(post_id)}, 1)


@server.tool(description="拉某条内容的评论列表（统一字段：评论人、内容、点赞、时间）。拿到评论后用 get_comment_insights 出结论。")
def get_comments(platform: str, post_id: str, limit: int = 20) -> dict:
    return _run(platform, "get_comments", {"post_id": str(post_id)}, limit)


@server.tool(description="拉平台热搜/热榜（目前支持抖音）。适合做选题和热点追踪。")
def get_trending(platform: str = "douyin", limit: int = 20) -> dict:
    return _run(platform, "get_trending", {}, limit)


@server.tool(description="评论洞察：先拉样本评论再本地聚合，直接给结论——情绪分布、提问占比、高频词、高赞评论。比原始评论更适合回答“用户到底在说什么”。")
def get_comment_insights(platform: str, post_id: str, sample: int = 60) -> dict:
    base = _run(platform, "get_comments", {"post_id": str(post_id)}, sample)
    if not base.get("ok"):
        return base
    raw_comments = base.get("items", [])
    post = None
    if base.get("items"):
        post = {"platform": platform, "id": str(post_id), "stats": {}}
    result = insights.analyze(raw_comments, post)
    result.update({"ok": True, "platform": platform, "sampled": len(raw_comments)})
    if "cost_usd" in base:
        result["cost_usd"] = base["cost_usd"]
        result["balance_usd"] = base.get("balance_usd")
    return result


@server.tool(description="查当前 API Key 的账户信息与余额（美元）。调用前可以先看一眼，避免跑到一半余额不足。")
def check_balance() -> dict:
    client = _client()
    try:
        data = client.me()
    except BusyBeeError as e:
        return e.as_dict()
    keep = ("username", "quota_usd", "used_usd", "group_zh", "is_admin")
    return {"ok": True, **{k: data.get(k) for k in keep if k in data}}


def serve(transport: str = "stdio") -> None:
    """stdio：本地安装；streamable-http：远程连接。"""
    if transport == "stdio":
        server.run("stdio")
        return
    server.settings.host = os.environ.get("BUSYBEE_HOST", "127.0.0.1")
    server.settings.port = int(os.environ.get("BUSYBEE_PORT", "3013"))
    server.run("streamable-http")
