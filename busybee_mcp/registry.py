"""平台与端点登记表 —— 每个工具在每个平台上对应哪个接口、传什么参数。

字段说明：
  path    相对 API 根的业务路径
  method  GET / POST
  params  统一入参名 -> 该接口的真实参数名（None 表示不映射）
  body    True 表示参数放 JSON body（否则走 query string）
  list    列表在返回 JSON 中的位置
  item    列表元素里真正的内容所在（如 tiktok 的 user_info）
  kind    归一化类型：user / post / comment / trend
"""
from __future__ import annotations

PLATFORMS = {
    "tiktok": {"label": "TikTok", "region": "overseas", "group": "海外视频（ov_video）"},
    "instagram": {"label": "Instagram", "region": "overseas", "group": "海外社媒（ov_social）"},
    "youtube": {"label": "YouTube", "region": "overseas", "group": "海外视频（ov_video）"},
    "twitter": {"label": "X / Twitter", "region": "overseas", "group": "海外社媒（ov_social）"},
    "douyin": {"label": "抖音", "region": "cn", "group": "国内视频（cn_video）"},
    "xiaohongshu": {"label": "小红书", "region": "cn", "group": "国内图文（cn_content）"},
}

TT = "/api/v1/tiktok/app/v3"
DY = "/api/v1/douyin/app/v3"
DY_SEARCH = "/api/v1/douyin/search"
XHS = "/api/v1/xiaohongshu/app_v2"
IG = "/api/v1/instagram"
YT = "/api/v1/youtube"
TW = "/api/v1/twitter/web"

SPEC: dict[tuple[str, str], dict] = {
    # ---------------- TikTok ----------------
    ("tiktok", "search_creators"): {
        "path": TT + "/fetch_user_search_result", "method": "GET",
        "params": {"keyword": "keyword", "limit": "count"},
        "list": "data.user_list", "item": "user_info", "kind": "user",
    },
    ("tiktok", "search_posts"): {
        "path": TT + "/fetch_video_search_result", "method": "GET",
        "params": {"keyword": "keyword", "limit": "count", "cursor": "offset"},
        "list": "data.search_item_list", "item": "aweme_info", "kind": "post",
    },
    ("tiktok", "get_creator"): {
        "path": TT + "/handler_user_profile", "method": "GET",
        "params": {"creator": None},
        "list": None, "item": "data.user", "kind": "user",
    },
    ("tiktok", "list_creator_posts"): {
        "path": TT + "/fetch_user_post_videos", "method": "GET",
        "params": {"creator": "unique_id", "limit": "count", "cursor": "max_cursor"},
        "list": "data.aweme_list", "item": None, "kind": "post",
    },
    ("tiktok", "get_post"): {
        "path": TT + "/fetch_one_video", "method": "GET",
        "params": {"post_id": "aweme_id"},
        "list": None, "item": "data.aweme_detail", "kind": "post",
    },
    ("tiktok", "get_comments"): {
        "path": TT + "/fetch_video_comments", "method": "GET",
        "params": {"post_id": "aweme_id", "limit": "count", "cursor": "cursor"},
        "list": "data.comments", "item": None, "kind": "comment",
    },
    # ---------------- 抖音 ----------------
    ("douyin", "search_creators"): {
        "path": DY_SEARCH + "/fetch_user_search", "method": "POST", "body": True,
        "params": {"keyword": "keyword", "cursor": "cursor", "search_id": "search_id"},
        "list": "data.user_list", "item": "user_info", "kind": "user",
    },
    ("douyin", "search_posts"): {
        "path": DY_SEARCH + "/fetch_video_search_v5", "method": "POST", "body": True,
        "params": {"keyword": "keyword", "cursor": "cursor", "search_id": "search_id"},
        "list": "data.data", "item": None, "kind": "post",
    },
    ("douyin", "get_creator"): {
        "path": DY + "/handler_user_profile", "method": "GET",
        "params": {"creator": None},
        "list": None, "item": "data.user", "kind": "user",
    },
    ("douyin", "list_creator_posts"): {
        "path": DY + "/fetch_user_post_videos", "method": "GET",
        "params": {"creator": "sec_user_id", "limit": "count", "cursor": "max_cursor"},
        "list": "data.aweme_list", "item": None, "kind": "post",
    },
    ("douyin", "get_post"): {
        "path": DY + "/fetch_one_video", "method": "GET",
        "params": {"post_id": "aweme_id"},
        "list": None, "item": "data.aweme_detail", "kind": "post",
    },
    ("douyin", "get_comments"): {
        "path": DY + "/fetch_video_comments", "method": "GET",
        "params": {"post_id": "aweme_id", "limit": "count", "cursor": "cursor"},
        "list": "data.comments", "item": None, "kind": "comment",
    },
    ("douyin", "get_trending"): {
        "path": DY + "/fetch_hot_search_list", "method": "GET",
        "params": {"limit": "count"},
        "list": "data.data.word_list", "item": None, "kind": "trend",
    },
    # ---------------- 小红书 ----------------
    ("xiaohongshu", "search_creators"): {
        "path": XHS + "/search_users", "method": "GET",
        "params": {"keyword": "keyword", "cursor": "page"},
        "list": "data.data.users", "item": None, "kind": "user",
    },
    ("xiaohongshu", "search_posts"): {
        "path": XHS + "/search_notes", "method": "GET",
        "params": {"keyword": "keyword", "cursor": "page"},
        "list": "data.data.items", "item": "note", "kind": "post",
    },
    ("xiaohongshu", "get_creator"): {
        "path": XHS + "/get_user_info", "method": "GET",
        "params": {"creator": None},
        "list": None, "item": "data.data", "kind": "user",
    },
    ("xiaohongshu", "list_creator_posts"): {
        "path": XHS + "/get_user_posted_notes", "method": "GET",
        "params": {"creator": "user_id", "cursor": "cursor"},
        "list": "data.data.notes", "item": None, "kind": "post",
    },
    ("xiaohongshu", "get_comments"): {
        "path": XHS + "/get_note_comments", "method": "GET",
        "params": {"post_id": "note_id", "limit": "page"},
        "list": "data.data.comments", "item": None, "kind": "comment",
    },
    # ---------------- Instagram ----------------
    ("instagram", "search_creators"): {
        "path": IG + "/v2/search_users", "method": "GET",
        "params": {"keyword": "keyword"},
        "list": "data.data.items", "item": None, "kind": "user",
    },
    ("instagram", "get_creator"): {
        "path": IG + "/v1/fetch_user_info_by_username", "method": "GET",
        "params": {"creator": None},
        "list": None, "item": "data.data.user", "kind": "user",
    },
    ("instagram", "list_creator_posts"): {
        "path": IG + "/v2/fetch_user_posts", "method": "GET",
        "params": {"creator": "username", "cursor": "pagination_token"},
        "list": "data.data.items", "item": None, "kind": "post",
    },
    ("instagram", "get_comments"): {
        "path": IG + "/v2/fetch_post_comments", "method": "GET",
        "params": {"post_id": "code_or_url", "cursor": "pagination_token"},
        "list": "data.data.comments", "item": None, "kind": "comment",
    },
    # ---------------- YouTube ----------------
    ("youtube", "search_posts"): {
        "path": YT + "/web/search_video", "method": "GET",
        "params": {"keyword": "search_query", "cursor": "continuation_token"},
        "list": "data.videos", "item": None, "kind": "post",
    },
    ("youtube", "get_creator"): {
        "path": YT + "/web/get_channel_info", "method": "GET",
        "params": {"creator": None},
        "list": None, "item": "data", "kind": "user",
    },
    ("youtube", "list_creator_posts"): {
        "path": YT + "/web_v2/get_channel_videos", "method": "GET",
        "params": {"creator": "channel_id", "cursor": "continuation_token"},
        "list": "data.videos", "item": None, "kind": "post",
    },
    ("youtube", "get_post"): {
        "path": YT + "/web_v2/get_video_info", "method": "GET",
        "params": {"post_id": "video_id"},
        "list": None, "item": "data", "kind": "post",
    },
    ("youtube", "get_comments"): {
        "path": YT + "/web_v2/get_video_comments", "method": "GET",
        "params": {"post_id": "video_id", "cursor": "continuation_token", "limit": "sort_by"},
        "list": "data.comments", "item": None, "kind": "comment",
    },
    # ---------------- X / Twitter ----------------
    ("twitter", "search_posts"): {
        "path": TW + "/fetch_search_timeline", "method": "GET",
        "params": {"keyword": "keyword", "cursor": "cursor"},
        "list": "data.timeline", "item": None, "kind": "post",
    },
    ("twitter", "get_creator"): {
        "path": TW + "/fetch_user_profile", "method": "GET",
        "params": {"creator": None},
        "list": None, "item": "data", "kind": "user",
    },
    ("twitter", "list_creator_posts"): {
        "path": TW + "/fetch_user_post_tweet", "method": "GET",
        "params": {"creator": "screen_name", "cursor": "cursor"},
        "list": "data.timeline", "item": None, "kind": "post",
    },
    ("twitter", "get_comments"): {
        "path": TW + "/fetch_post_comments", "method": "GET",
        "params": {"post_id": "tweet_id", "cursor": "cursor"},
        "list": "data", "item": None, "kind": "comment",
    },
}

TOOL_LABELS = {
    "search_creators": "按关键词搜达人/账号",
    "search_posts": "按关键词搜内容",
    "get_creator": "查账号详情",
    "list_creator_posts": "拉账号作品列表",
    "get_post": "查单条内容详情",
    "get_comments": "拉内容评论",
    "get_trending": "拉热搜/榜单",
}


def supports(tool: str) -> list[str]:
    """返回支持该工具的平台。"""
    return sorted({p for (p, t) in SPEC if t == tool})


def spec_for(platform: str, tool: str) -> dict:
    key = (platform, tool)
    if key not in SPEC:
        raise KeyError(
            "平台 %s 暂不支持「%s」。支持该工具的平台：%s"
            % (platform, TOOL_LABELS.get(tool, tool), "、".join(supports(tool)) or "暂无")
        )
    return SPEC[key]


def resolve_creator(platform: str, creator: str) -> dict:
    """把用户给的 handle / 链接 / id 解析成该平台接口真实需要的参数名。"""
    c = (creator or "").strip().lstrip("@")
    if not c:
        raise ValueError("creator 不能为空：填账号 handle 或平台 id")
    if platform == "tiktok":
        if c.startswith("MS4wLjAB"):
            return {"sec_user_id": c}
        if c.isdigit():
            return {"user_id": c}
        return {"unique_id": c}
    if platform == "douyin":
        return {"sec_user_id": c}
    if platform == "xiaohongshu":
        return {"user_id": c}
    if platform == "instagram":
        return {"username": c}
    if platform == "youtube":
        return {"channel_id": c}
    if platform == "twitter":
        return {"screen_name": c}
    return {"creator": c}
