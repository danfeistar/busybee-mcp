"""工具调度层 —— MCP 与 REST 共用同一套实现，保证两条路径行为一字不差。

TOOL_SPECS 同时用于：
  1. REST 的 /mcp/tools 清单（OpenAI function calling 与 Dify/n8n 直接导入）
  2. /mcp/openapi.json（GPT Actions、Zapier、Make 等 OpenAPI 型 agent）
  3. MCP 工具描述（server.py 引用，避免两处漂移）
"""
from __future__ import annotations

import json

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
        "description": "拉某个账号最近发布的作品列表。creator 同 get_creator（handle / id / 主页链接皆可）。",
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
        "description": "拉某条内容的评论列表，返回统一字段：评论人、内容、点赞、时间。post_id 可传 id 或链接。",
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
        # 只给真有这些字段的接口补默认值：pgy 系是严格校验（多一个字段就 422），
        # 全局硬塞 cursor/search_id 会把它们全打挂
        for k, v in (spec.get("body_defaults") or {}).items():
            body.setdefault(k, v)
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
        if isinstance(obj, str):  # 有些接口把真实对象塞成 JSON 字符串
            try:
                obj = json.loads(obj)
            except ValueError:
                obj = {}
            if isinstance(obj, dict) and isinstance(obj.get("user_info"), dict):
                obj = obj["user_info"]  # 抖音 user_list[].dynamic_patch.raw_data
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


def _lookup_creator_id(client: Client, platform: str, creator: str) -> str:
    """把 handle 解析成接口要的平台 id。客户拿到 handle 就传 handle 是常态，
    不解析就会直接把 handle 当 id 发出去，上游回 400。"""
    import re as _re

    c = str(creator or "").strip().lstrip("@")
    if not c:
        return c
    try:
        if platform == "xiaohongshu":
            if _re.fullmatch(r"[0-9a-f]{24}", c):
                return c
            spec = registry.spec_for("xiaohongshu", "search_creators")
            j = client.call_endpoint(spec["path"], params={"keyword": c, "page": 1},
                                    method=spec.get("method", "GET"))
            users = dig(j, "data.data.users", default=[]) or []
            for u in users:
                if str(u.get("red_id") or "").lower() == c.lower() and u.get("id"):
                    return str(u["id"])
            if users and users[0].get("id"):
                return str(users[0]["id"])
        elif platform == "douyin":
            if c.startswith("MS4wLjAB"):
                return c
            spec = registry.spec_for("douyin", "search_creators")
            j = client.call_endpoint(spec["path"], params={}, method="POST",
                                    body={"keyword": c, "cursor": 0})
            for el in dig(j, "data.user_list", default=[]) or []:
                raw = dig(el, "dynamic_patch.raw_data")
                ui = {}
                if isinstance(raw, str):
                    try:
                        ui = (json.loads(raw) or {}).get("user_info") or {}
                    except ValueError:
                        ui = {}
                if str(ui.get("unique_id") or "").lower() == c.lower() and ui.get("sec_uid"):
                    return str(ui["sec_uid"])
    except Exception:
        return c
    return c


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

    limit = max(1, min(int(limit or 20), MAX_LIMIT, int(spec.get("limit_max") or MAX_LIMIT)))
    forced = None
    if tool in ("get_creator", "list_creator_posts") and platform in ("xiaohongshu", "douyin") and args.get("creator"):
        args = {**args, "creator": _lookup_creator_id(client, platform, str(args["creator"]))}
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


def _from_url(value: str) -> str:
    """从内容链接里抠出内容 id —— 很多 agent 手上只有 url，直接丢 url 过来。"""
    import re
    v = value.strip()
    pats = (
        r"tiktok\.com/@[^/]+/video/(\d+)",
        r"douyin\.com/video/(\d+)",
        r"(?:youtube\.com/(?:watch\?v=|shorts/|embed/)|youtu\.be/)([A-Za-z0-9_-]{6,})",
        r"(?:twitter|x)\.com/[^/]+/status/(\d+)",
        r"instagram\.com/(?:p|reel|tv)/([A-Za-z0-9_-]+)",
        r"xiaohongshu\.com/(?:explore|discovery/item)/([A-Za-z0-9]+)",
    )
    for p in pats:
        m = re.search(p, v)
        if m:
            return m.group(1)
    return v.rstrip("/").rsplit("/", 1)[-1].split("?")[0]


PLATFORM_ALIASES = {
    "tiktok": "tiktok", "tt": "tiktok", "抖音国际版": "tiktok",
    "instagram": "instagram", "ig": "instagram", "ins": "instagram", "instagramreels": "instagram",
    "youtube": "youtube", "yt": "youtube", "油管": "youtube",
    "twitter": "twitter", "x": "twitter", "xcom": "twitter", "推特": "twitter",
    "douyin": "douyin", "dy": "douyin", "抖音": "douyin",
    "xiaohongshu": "xiaohongshu", "xhs": "xiaohongshu", "red": "xiaohongshu",
    "rednote": "xiaohongshu", "小红书": "xiaohongshu",
}
_CREATOR_KEYS = ("creator", "id", "handle", "username", "user", "user_id",
                 "creator_id", "unique_id", "sec_user_id", "account", "url")
_POST_KEYS = ("post_id", "id", "post", "video_id", "note_id", "item_id",
              "aweme_id", "content_id", "url", "link")
_KEYWORD_KEYS = ("keyword", "q", "query", "search", "text", "term", "keywords")


def _normalize_args(name: str, args: dict) -> dict:
    """容忍各类 agent 的写法：id / handle / url / 中文平台名 / q 都认。
    LLM 看到我们返回里字段叫 id，就会顺手传 id，这里必须接得住。"""
    a = dict(args or {})

    raw_platform = str(a.get("platform") or a.get("source") or "").strip().lower()
    picked = PLATFORM_ALIASES.get(raw_platform, PLATFORM_ALIASES.get(raw_platform.replace(" ", ""), raw_platform))
    if picked:
        a["platform"] = picked

    if name in ("get_creator", "list_creator_posts"):
        if not a.get("creator"):
            for k in _CREATOR_KEYS:
                if a.get(k):
                    v = str(a[k]).strip()
                    a["creator"] = _from_url(v) if "http" in v else v.lstrip("@")
                    break
    elif name in ("get_post", "get_comments", "get_comment_insights"):
        if not a.get("post_id"):
            for k in _POST_KEYS:
                if a.get(k):
                    v = str(a[k]).strip()
                    a["post_id"] = _from_url(v) if "/" in v else v
                    break
    if name in ("search_creators", "search_posts"):
        if not a.get("keyword"):
            for k in _KEYWORD_KEYS:
                if a.get(k):
                    a["keyword"] = str(a[k]).strip()
                    break
    return a


def call_tool(name: str, args: dict | None = None, client: Client | None = None) -> dict:
    """所有入口（MCP / REST）都走这里。"""
    args = _normalize_args(name, dict(args or {}))
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

    # 平台必须显式给：静默默认抖音会让海外密钥用户收到「无权限」，很坑
    platform = args.pop("platform", "")
    limit = args.pop("limit", 20)
    return _run(platform, name, args, limit, client)
