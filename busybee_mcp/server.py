"""BusyBee MCP 服务 —— 10 个业务级工具，统一字段，按次计费。

设计要点：
1. 不把底层上千个接口直接暴露给 AI：工具越少，AI 选对的概率越高。
2. 所有返回都是同一套字段（见 normalize.py），AI 不需要学平台差异。
3. 每次调用回报本次花费与余额，方便 AI 自己控制预算。
4. 工具实现在 dispatch.py —— MCP / REST / SSE 三条入口共用，行为不会漂移。
"""
from __future__ import annotations

import contextvars
import os

from mcp.server import MCPServer

from . import dispatch
from .client import SIGNUP_URL, Client

VERSION = "0.2.4"
MAX_LIMIT = dispatch.MAX_LIMIT

# 远程模式：HTTP 头 / 查询参数里的 API Key 通过 contextvar 传进来
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


def _call(name: str, args: dict) -> dict:
    return dispatch.call_tool(name, args, _client())


@server.tool(description="列出可用的平台、每个平台支持哪些操作，以及该怎么选。首次使用先调这个。")
def list_platforms() -> dict:
    return _call("list_platforms", {})


@server.tool(description="按关键词搜索社媒账号/达人。返回 id、handle、昵称、粉丝数、简介——拿到 handle 或 id 后再用 get_creator / list_creator_posts 深入。")
def search_creators(platform: str, keyword: str, limit: int = 10) -> dict:
    return _call("search_creators", {"platform": platform, "keyword": keyword, "limit": limit})


@server.tool(description="搜索内容：给关键词，返回帖子/视频列表（统一字段：作者、文案、时间、点赞/评论/播放）。适合“某个话题最近在火什么”。")
def search_posts(platform: str, keyword: str, limit: int = 20) -> dict:
    return _call("search_posts", {"platform": platform, "keyword": keyword, "limit": limit})


@server.tool(description="查单个账号的详情（粉丝数、简介、作品数）。creator 填 handle（如 @nasa 去掉@）或平台 id。")
def get_creator(platform: str, creator: str) -> dict:
    return _call("get_creator", {"platform": platform, "creator": str(creator).lstrip("@")})


@server.tool(description="拉某个账号最近发布的作品列表。creator 填 handle 或平台 id。")
def list_creator_posts(platform: str, creator: str, limit: int = 20) -> dict:
    return _call("list_creator_posts", {"platform": platform,
                                        "creator": str(creator).lstrip("@"), "limit": limit})


@server.tool(description="查单条内容的详情。post_id 填平台的内容 id；TikTok/抖音也可传视频链接里的数字 id。")
def get_post(platform: str, post_id: str) -> dict:
    return _call("get_post", {"platform": platform, "post_id": str(post_id)})


@server.tool(description="拉某条内容的评论列表（统一字段：评论人、内容、点赞、时间）。拿到评论后用 get_comment_insights 出结论。")
def get_comments(platform: str, post_id: str, limit: int = 20) -> dict:
    return _call("get_comments", {"platform": platform, "post_id": str(post_id), "limit": limit})


@server.tool(description="拉平台热搜/热榜（目前支持抖音）。适合做选题和热点追踪。")
def get_trending(platform: str = "douyin", limit: int = 20) -> dict:
    return _call("get_trending", {"platform": platform, "limit": limit})


@server.tool(description="评论洞察：先拉样本评论再本地聚合，直接给结论——情绪分布、提问占比、高频词、高赞评论。比原始评论更适合回答“用户到底在说什么”。")
def get_comment_insights(platform: str, post_id: str, sample: int = 60) -> dict:
    return _call("get_comment_insights", {"platform": platform, "post_id": str(post_id), "sample": sample})


@server.tool(description="查当前 API Key 的账户信息与余额（美元）。调用前可以先看一眼，避免跑到一半余额不足。")
def check_balance() -> dict:
    return _call("check_balance", {})


def serve(transport: str = "stdio") -> None:
    """stdio：本地安装；streamable-http：远程连接。"""
    if transport == "stdio":
        server.run("stdio")
        return
    server.settings.host = os.environ.get("BUSYBEE_HOST", "127.0.0.1")
    server.settings.port = int(os.environ.get("BUSYBEE_PORT", "3013"))
    server.run("streamable-http")
