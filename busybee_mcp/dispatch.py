"""工具调度层 —— MCP 与 REST 共用同一套实现，保证两条路径行为一字不差。

TOOL_SPECS 同时用于：
  1. REST 的 /mcp/tools 清单（OpenAI function calling 与 Dify/n8n 直接导入）
  2. /mcp/openapi.json（GPT Actions、Zapier、Make 等 OpenAPI 型 agent）
  3. MCP 工具描述（server.py 引用，避免两处漂移）
"""
from __future__ import annotations

from typing import Any

from . import insights, registry
from .client import SIGNUP_URL, BusyBeeError, Client
from .normalize import normalize
from .util import dig

MAX_LIMIT = 50
PLATFORM_ENUM = list(registry.PLATFORMS.keys())

P_PLATFORM = {
    "type": "string",
    "enum": PLATFORM_ENUM,
    "description": "平台：tiktok / instagram / youtube / twitter / douyin / xiaohongshu（国内平台需要国内分组的密钥）",
}
P_LIMIT = {"type": "integer", "minimum": 1, "maximum": MAX_LIMIT, "default": 20}

TOOL_SPECS: dict[str, dict] = {
    "list_platforms": {
        "description": "列出可用的平台、每个平台支持哪些操作、需要哪类密钥。首次使用先调这个。",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    "search_creators": {
        "description": "按关键词搜索社媒账号/达人，返回 id、handle、昵称、粉丝数、简介。",
        "parameters": {
            "type": "object",
            "properties": {"platform": P_PLATFORM,
                           "keyword": {"type": "string", "description": "搜索关键词"},
                           "limit": {**P_LIMIT, "default": 10}},
            "required": ["platform", "keyword"],
        },
    },
    "search_posts": {
        "description": "按关键词搜索内容（帖子/视频），返回统一字段：作者、文案、时间、点赞/评论/播放。",
        "parameters": {
            "type": "object",
            "properties": {"platform": P_PLATFORM,
                           "keyword": {"type": "string", "description": "搜索关键词"},
                           "limit": P_LIMIT},
            "required": ["platform", "keyword"],
        },
    },
    "get_creator": {
        "description": "查单个账号详情：粉丝数、简介、作品数。creator 填 handle（去掉 @）或平台 id。",
        "parameters": {
            "type": "object",
            "properties": {"platform": P_PLATFORM,
                           "creator": {"type": "string", "description": "账号 handle 或平台 id"}},
            "required": ["platform", "creator"],
        },
    },
    "list_creator_posts": {
        "description": "拉某个账号最近发布的作品列表。",
        "parameters": {
            "type": "object",
            "properties": {"platform": P_PLATFORM,
                           "creator": {"type": "string", "description": "账号 handle 或平台 id"},
                           "limit": P_LIMIT},
            "required": ["platform", "creator"],
        },
    },
    "get_post": {
        "description": "查单条内容详情。post_id 填平台的内容 id。",
        "parameters": {
            "type": "object",
            "properties": {"platform": P_PLATFORM,
                           "post_id": {"type": "string", "description": "内容 id"}},
            "required": ["platform", "post_id"],
        },
    },
    "get_comments": {
        "description": "拉某条内容的评论列表，返回统一字段：评论人、内容、点赞、时间。",
        "parameters": {
            "type": "object",
            "properties": {"platform": P_PLATFORM,
                           "post_id": {"type": "string", "description": "内容 id"},
                           "limit": P_LIMIT},
            "required": ["platform", "post_id"],
        },
    },
    "get_trending": {
        "description": "拉平台热搜/热榜（目前支持抖音）。",
        "parameters": {
            "type": "object",
            "properties": {"platform": {**P_PLATFORM, "default": "douyin"}, "limit": P_LIMIT},
            "required": [],
        },
    },
    "get_comment_insights": {
        "description": "评论洞察：拉样本评论后本地聚合，直接给结论——情绪分布、提问占比、高频词、高赞评论。",
        "parameters": {
            "type": "object",
            "properties": {"platform": P_PLATFORM,
                           "post_id": {"type": "string", "description": "内容 id"},
                           "sample": {"type": "integer", "minimum": 5, "maximum": MAX_LIMIT, "default": 60}},
            "required": ["platform", "post_id"],
        },
    },
    "check_balance": {
        "description": "查当前 API 密钥的账户信息与余额（美元）。",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
}


def openai_tools() -> list[dict]:
    """OpenAI function calling / 多数国产 Agent 平台可直接导入的格式。"""
    return [{"type": "function",
             "function": {"name": name, "description": spec["description"],
                          "parameters": spec["parameters"]}}
            for name, spec in TOOL_SPECS.items()]


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


def _platforms_payload() -> dict:
    rows = []
    for pid, meta in registry.PLATFORMS.items():
        rows.append({
            "platform": pid,
            "label": meta["label"],
            "region": "海外" if meta["region"] == "overseas" else "国内",
            "tools": sorted({t for (p, t) in registry.SPEC if p == pid}),
            "key_group": meta["group"],
        })
    return {"ok": True, "count": len(rows), "platforms": rows,
            "note": "国内平台（douyin / xiaohongshu）需要国内分组的密钥；海外平台用海外分组。"}


def _run(platform: str, tool: str, args: dict, limit: int, client: Client) -> dict:
    platform = (platform or "").strip().lower()
    if platform not in registry.PLATFORMS:
        return {"ok": False, "error": "unknown_platform",
                "message": "不认识的平台「%s」。可用：%s" % (platform, "、".join(registry.PLATFORMS)),
                "platforms": {k: v["label"] for k, v in registry.PLATFORMS.items()}}
    try:
        spec = dict(registry.spec_for(platform, tool), platform=platform)
    except KeyError as e:
        return {"ok": False, "error": "unsupported_tool", "message": str(e).strip('"')}

    limit = max(1, min(int(limit or 20), MAX_LIMIT))
    forced = None
    if tool == "get_creator":
        try:
            forced = registry.resolve_creator(platform, str(args.get("creator") or ""))
        except ValueError as e:
            return {"ok": False, "error": "bad_argument", "message": str(e)}

    bal_before = client.balance_usd()
    try:
        params, body = _build_params(spec, {**args, "limit": limit}, forced)
        j = client.call_endpoint(spec["path"], params=params, method=spec.get("method", "GET"), body=body)
    except BusyBeeError as e:
        return e.as_dict()

    items = _extract(j, spec, limit)
    bal_after = client.balance_usd(fresh=True)
    out: dict[str, Any] = {"ok": True, "platform": platform, "tool": tool,
                           "count": len(items), "items": items}
    if bal_before is not None and bal_after is not None:
        out["cost_usd"] = round(max(0.0, bal_before - bal_after), 4)
        out["balance_usd"] = bal_after
    if not items:
        out["note"] = "调用成功但没有取到数据：可能关键词太窄、该账号无公开内容，或该接口需要其它参数。"
    return out


def call_tool(name: str, args: dict | None = None, client: Client | None = None) -> dict:
    """所有入口（MCP / REST）都走这里。"""
    args = dict(args or {})
    client = client or Client()

    if name not in TOOL_SPECS:
        return {"ok": False, "error": "unknown_tool",
                "message": "没有这个工具「%s」。" % name,
                "tools": list(TOOL_SPECS)}

    if name == "list_platforms":
        return _platforms_payload()

    if name == "check_balance":
        try:
            data = client.me()
        except BusyBeeError as e:
            return e.as_dict()
        keep = ("username", "quota_usd", "used_usd", "quota_exact_usd", "group", "group_zh", "is_admin")
        return {"ok": True, **{k: data.get(k) for k in keep if k in data}}

    if name == "get_comment_insights":
        platform = args.get("platform", "")
        post_id = str(args.get("post_id") or "")
        sample = max(5, min(int(args.get("sample") or 60), MAX_LIMIT))
        base = _run(platform, "get_comments", {"post_id": post_id}, sample, client)
        if not base.get("ok"):
            return base
        result = insights.analyze(base.get("items", []),
                                  {"platform": platform, "id": post_id, "stats": {}})
        result.update({"ok": True, "platform": platform, "tool": name,
                       "sampled": len(base.get("items", []))})
        for k in ("cost_usd", "balance_usd"):
            if k in base:
                result[k] = base[k]
        return result

    platform = args.pop("platform", "douyin" if name == "get_trending" else "")
    limit = args.pop("limit", 20)
    return _run(platform, name, args, limit, client)
