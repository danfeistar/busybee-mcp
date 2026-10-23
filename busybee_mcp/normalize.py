"""归一化层 —— 把各平台千奇百怪的返回压成同一套字段。

统一后的结构（所有工具都返回这个形状，AI 不需要学平台差异）：
  账号   {platform, id, handle, name, bio, followers, following, posts, verified, avatar, url}
  内容   {platform, id, url, author{id,handle,name}, text, created_at,
          stats{likes,comments,shares,views,collects}, cover}
  评论   {platform, id, post_id, author{id,handle,name}, text, likes, replies, created_at}
  热搜   {platform, rank, title, hot_value}
"""
from __future__ import annotations

import re
from typing import Any

from .util import dig, first, to_int, truncate, unix_to_iso


def _avatar(obj: Any) -> str | None:
    return first(
        dig(obj, "avatar_thumb.url_list.0"),
        dig(obj, "avatar_medium.url_list.0"),
        dig(obj, "avatar_larger.url_list.0"),
        dig(obj, "avatar", "url"),
        dig(obj, "avatar"),
        dig(obj, "profile_pic_url"),
        dig(obj, "image"),
        dig(obj, "avatar_url"),
        default=None,
    )


def _num_group(text: str | None) -> int:
    """从 'Fans 96.5k' 这类文案里取数。"""
    if not text:
        return 0
    m = re.search(r"([\d.]+)\s*([kKmMbB万]?)", str(text))
    if not m:
        return 0
    return to_int(m.group(1) + m.group(2))


# ---------------------------------------------------------------- TikTok
def tiktok_user(u: dict) -> dict:
    uid = first(dig(u, "uid"), dig(u, "id"), dig(u, "user_id"))
    handle = first(dig(u, "unique_id"), dig(u, "uniqueId"))
    return {
        "platform": "tiktok",
        "id": str(uid or ""),
        "handle": handle,
        "name": first(dig(u, "nickname"), handle),
        "bio": truncate(first(dig(u, "signature"), dig(u, "desc")), 400),
        "followers": to_int(dig(u, "follower_count")),
        "following": to_int(dig(u, "following_count")),
        "posts": to_int(dig(u, "aweme_count")),
        "verified": bool(first(dig(u, "custom_verify"), dig(u, "enterprise_verify_reason"), default="")),
        "avatar": _avatar(u),
        "url": ("https://www.tiktok.com/@%s" % handle) if handle else None,
    }


def tiktok_post(a: dict) -> dict:
    aid = first(dig(a, "aweme_id"), dig(a, "id"))
    st = dig(a, "statistics", default={}) or {}
    handle = dig(a, "author.unique_id")
    return {
        "platform": "tiktok",
        "id": str(aid or ""),
        "url": first(dig(a, "share_url"), ("https://www.tiktok.com/@%s/video/%s" % (handle, aid)) if handle and aid else None),
        "author": {
            "id": str(first(dig(a, "author.uid"), dig(a, "author_user_id"), default="")),
            "handle": handle,
            "name": dig(a, "author.nickname"),
        },
        "text": truncate(first(dig(a, "desc"), dig(a, "content_desc")), 1200),
        "created_at": unix_to_iso(dig(a, "create_time")),
        "stats": {
            "likes": to_int(dig(st, "digg_count")),
            "comments": to_int(dig(st, "comment_count")),
            "shares": to_int(dig(st, "share_count")),
            "views": to_int(dig(st, "play_count")),
            "collects": to_int(dig(st, "collect_count")),
        },
        "cover": dig(a, "video.cover.url_list.0"),
    }


def tiktok_comment(c: dict) -> dict:
    return {
        "platform": "tiktok",
        "id": str(first(dig(c, "cid"), dig(c, "comment_id"), default="")),
        "post_id": str(first(dig(c, "aweme_id"), default="")),
        "author": {
            "id": str(first(dig(c, "user.uid"), default="")),
            "handle": dig(c, "user.unique_id"),
            "name": dig(c, "user.nickname"),
        },
        "text": truncate(first(dig(c, "text"), dig(c, "content")), 1000),
        "likes": to_int(first(dig(c, "digg_count"), dig(c, "like_count"), default=0)),
        "replies": to_int(first(dig(c, "reply_comment_total"), default=0)),
        "created_at": unix_to_iso(dig(c, "create_time")),
    }


# ---------------------------------------------------------------- 抖音
def douyin_user(u: dict) -> dict:
    uid = first(dig(u, "uid"), dig(u, "sec_uid"))
    handle = first(dig(u, "unique_id"), dig(u, "short_id"), dig(u, "sec_uid"))
    return {
        "platform": "douyin",
        "id": str(uid or ""),
        "handle": handle,
        "name": first(dig(u, "nickname"), handle),
        "bio": truncate(first(dig(u, "signature"), dig(u, "desc")), 400),
        "followers": to_int(first(dig(u, "follower_count"), dig(u, "mplatform_followers_count"), default=0)),
        "following": to_int(dig(u, "following_count")),
        "posts": to_int(first(dig(u, "aweme_count"), default=0)),
        "verified": bool(first(dig(u, "custom_verify"), dig(u, "enterprise_verify_reason"), default="")),
        "avatar": _avatar(u),
        "url": ("https://www.douyin.com/user/%s" % dig(u, "sec_uid")) if dig(u, "sec_uid") else None,
    }


def douyin_post(a: dict) -> dict:
    aid = first(dig(a, "aweme_id"), dig(a, "id"))
    st = dig(a, "statistics", default={}) or {}
    return {
        "platform": "douyin",
        "id": str(aid or ""),
        "url": first(dig(a, "share_info.share_url"), ("https://www.douyin.com/video/%s" % aid) if aid else None),
        "author": {
            "id": str(first(dig(a, "author.uid"), default="")),
            "handle": first(dig(a, "author.unique_id"), dig(a, "author.sec_uid")),
            "name": dig(a, "author.nickname"),
        },
        "text": truncate(first(dig(a, "desc"), dig(a, "preview_title")), 1200),
        "created_at": unix_to_iso(dig(a, "create_time")),
        "stats": {
            "likes": to_int(dig(st, "digg_count")),
            "comments": to_int(dig(st, "comment_count")),
            "shares": to_int(dig(st, "share_count")),
            "views": to_int(dig(st, "play_count")),
            "collects": to_int(dig(st, "collect_count")),
        },
        "cover": dig(a, "video.cover.url_list.0"),
    }


def douyin_comment(c: dict) -> dict:
    return {
        "platform": "douyin",
        "id": str(first(dig(c, "cid"), dig(c, "comment_id"), default="")),
        "post_id": str(first(dig(c, "aweme_id"), default="")),
        "author": {
            "id": str(first(dig(c, "user.uid"), default="")),
            "handle": first(dig(c, "user.unique_id"), dig(c, "user.sec_uid")),
            "name": dig(c, "user.nickname"),
        },
        "text": truncate(first(dig(c, "text"), dig(c, "content")), 1000),
        "likes": to_int(first(dig(c, "digg_count"), dig(c, "like_count"), default=0)),
        "replies": to_int(first(dig(c, "reply_comment_total"), default=0)),
        "created_at": unix_to_iso(dig(c, "create_time")),
    }


def douyin_trend(t: dict, rank: int) -> dict:
    return {
        "platform": "douyin",
        "rank": rank,
        "title": first(dig(t, "word"), dig(t, "sentence_tag"), dig(t, "title"), default=""),
        "hot_value": to_int(first(dig(t, "hot_value"), dig(t, "view_count"), default=0)),
    }


# ---------------------------------------------------------------- 小红书
def xhs_user(u: dict) -> dict:
    uid = first(dig(u, "id"), dig(u, "user_id"), dig(u, "userid"))
    return {
        "platform": "xiaohongshu",
        "id": str(uid or ""),
        "handle": first(dig(u, "red_id"), dig(u, "red_official_verify_type") and None, dig(u, "name")),
        "name": first(dig(u, "name"), dig(u, "nickname")),
        "bio": truncate(first(dig(u, "desc"), dig(u, "sub_title")), 400),
        "followers": _num_group(first(dig(u, "sub_title"), dig(u, "fans"))),
        "following": to_int(dig(u, "following")),
        "posts": to_int(dig(u, "notes")),
        "verified": bool(dig(u, "red_official_verified", default=False)),
        "avatar": _avatar(u),
        "url": ("https://www.xiaohongshu.com/user/profile/%s" % uid) if uid else None,
    }


def xhs_note(n: dict) -> dict:
    nid = first(dig(n, "id"), dig(n, "note_id"))
    ui = dig(n, "user", default={}) or {}
    return {
        "platform": "xiaohongshu",
        "id": str(nid or ""),
        "url": ("https://www.xiaohongshu.com/explore/%s" % nid) if nid else None,
        "author": {
            "id": str(first(dig(ui, "userid"), dig(ui, "user_id"), default="")),
            "handle": dig(ui, "red_id"),
            "name": dig(ui, "nickname"),
        },
        "text": truncate(first(dig(n, "title"), "") + ("\n" + dig(n, "desc") if dig(n, "desc") else ""), 1200),
        "created_at": unix_to_iso(first(dig(n, "time"), dig(n, "last_update_time"))),
        "stats": {
            "likes": to_int(first(dig(n, "liked_count"), dig(n, "interact_info.liked_count"), default=0)),
            "comments": to_int(first(dig(n, "comments_count"), dig(n, "interact_info.comment_count"), default=0)),
            "shares": to_int(first(dig(n, "shared_count"), default=0)),
            "views": to_int(first(dig(n, "view_count"), default=0)),
            "collects": to_int(first(dig(n, "collected_count"), dig(n, "interact_info.collected_count"), default=0)),
        },
        "cover": first(dig(n, "cover.url"), dig(n, "images_list.0.url"), default=None),
    }


def xhs_comment(c: dict) -> dict:
    ui = first(dig(c, "user_info"), dig(c, "user"), default={}) or {}
    return {
        "platform": "xiaohongshu",
        "id": str(first(dig(c, "id"), dig(c, "comment_id"), default="")),
        "post_id": str(first(dig(c, "note_id"), default="")),
        "author": {
            "id": str(first(dig(ui, "user_id"), dig(ui, "userid"), default="")),
            "handle": dig(ui, "red_id"),
            "name": dig(ui, "nickname"),
        },
        "text": truncate(first(dig(c, "content"), dig(c, "text")), 1000),
        "likes": to_int(first(dig(c, "like_count"), dig(c, "liked_count"), default=0)),
        "replies": to_int(first(dig(c, "sub_comment_count"), default=0)),
        "created_at": unix_to_iso(first(dig(c, "create_time"), dig(c, "time"))),
    }


# ---------------------------------------------------------------- Instagram
def ig_user(u: dict) -> dict:
    un = first(dig(u, "username"), dig(u, "user.username"))
    return {
        "platform": "instagram",
        "id": str(first(dig(u, "id"), dig(u, "pk"), default="")),
        "handle": un,
        "name": first(dig(u, "full_name"), dig(u, "name"), un),
        "bio": truncate(first(dig(u, "biography"), dig(u, "description")), 400),
        "followers": to_int(first(dig(u, "follower_count"), dig(u, "edge_followed_by.count"), default=0)),
        "following": to_int(first(dig(u, "following_count"), dig(u, "edge_follow.count"), default=0)),
        "posts": to_int(first(dig(u, "media_count"), dig(u, "edge_owner_to_timeline_media.count"), default=0)),
        "verified": bool(dig(u, "is_verified", default=False)),
        "avatar": _avatar(u),
        "url": ("https://www.instagram.com/%s/" % un) if un else None,
    }


def ig_post(p: dict) -> dict:
    code = first(dig(p, "code"), dig(p, "shortcode"), dig(p, "id"))
    ui = first(dig(p, "user"), dig(p, "owner"), default={}) or {}
    return {
        "platform": "instagram",
        "id": str(first(dig(p, "id"), dig(p, "pk"), code, default="")),
        "url": ("https://www.instagram.com/p/%s/" % code) if code else None,
        "author": {
            "id": str(first(dig(ui, "id"), dig(ui, "pk"), default="")),
            "handle": dig(ui, "username"),
            "name": first(dig(ui, "full_name"), dig(ui, "username")),
        },
        "text": truncate(first(dig(p, "caption.text"), dig(p, "caption"), dig(p, "text")), 1200),
        "created_at": unix_to_iso(first(dig(p, "taken_at"), dig(p, "taken_at_timestamp"))),
        "stats": {
            "likes": to_int(first(dig(p, "like_count"), dig(p, "edge_liked_by.count"), default=0)),
            "comments": to_int(first(dig(p, "comment_count"), dig(p, "edge_media_to_comment.count"), default=0)),
            "shares": 0,
            "views": to_int(first(dig(p, "play_count"), dig(p, "view_count"), default=0)),
            "collects": 0,
        },
        "cover": first(dig(p, "image_versions2.candidates.0.url"), dig(p, "display_url")),
    }


def ig_comment(c: dict) -> dict:
    ui = first(dig(c, "user"), default={}) or {}
    return {
        "platform": "instagram",
        "id": str(first(dig(c, "pk"), dig(c, "id"), default="")),
        "post_id": str(first(dig(c, "media_id"), default="")),
        "author": {
            "id": str(first(dig(ui, "pk"), dig(ui, "id"), default="")),
            "handle": dig(ui, "username"),
            "name": first(dig(ui, "full_name"), dig(ui, "username")),
        },
        "text": truncate(dig(c, "text"), 1000),
        "likes": to_int(first(dig(c, "comment_like_count"), dig(c, "like_count"), default=0)),
        "replies": to_int(first(dig(c, "child_comment_count"), default=0)),
        "created_at": unix_to_iso(first(dig(c, "created_at"), dig(c, "created_at_utc"))),
    }


# ---------------------------------------------------------------- YouTube
def yt_video(v: dict) -> dict:
    vid = first(dig(v, "video_id"), dig(v, "id"), dig(v, "videoId"))
    return {
        "platform": "youtube",
        "id": str(vid or ""),
        "url": ("https://www.youtube.com/watch?v=%s" % vid) if vid else None,
        "author": {
            "id": str(first(dig(v, "channel_id"), dig(v, "channelId"), default="")),
            "handle": first(dig(v, "channel_handle"), dig(v, "channel"), dig(v, "author")),
            "name": first(dig(v, "author"), dig(v, "channel_name"), dig(v, "channel")),
        },
        "text": truncate(first(dig(v, "title"), dig(v, "headline")), 1200),
        "created_at": first(dig(v, "published_time"), dig(v, "publishedTimeText")),
        "stats": {
            "likes": to_int(first(dig(v, "like_count"), default=0)),
            "comments": to_int(first(dig(v, "comment_count"), default=0)),
            "shares": 0,
            "views": to_int(first(dig(v, "number_of_views"), dig(v, "view_count"), dig(v, "viewCountText"), default=0)),
            "collects": 0,
        },
        "cover": first(dig(v, "thumbnails.0.url"), dig(v, "thumbnail")),
    }


def yt_comment(c: dict) -> dict:
    ui = first(dig(c, "author"), default={}) or {}
    return {
        "platform": "youtube",
        "id": str(first(dig(c, "comment_id"), dig(c, "id"), default="")),
        "post_id": str(first(dig(c, "video_id"), default="")),
        "author": {
            "id": str(first(dig(ui, "channel_id"), dig(c, "author_channel_id"), default="")),
            "handle": dig(ui, "handle"),
            "name": first(dig(ui, "name"), dig(c, "author"), dig(c, "author_name")),
        },
        "text": truncate(first(dig(c, "content"), dig(c, "text")), 1000),
        "likes": to_int(first(dig(c, "like_count"), dig(c, "vote_count"), default=0)),
        "replies": to_int(first(dig(c, "reply_count"), default=0)),
        "created_at": first(dig(c, "published_time"), dig(c, "published")),
    }


def yt_channel(ch: dict) -> dict:
    cid = first(dig(ch, "channel_id"), dig(ch, "id"))
    name = first(dig(ch, "channel_name"), dig(ch, "title"), dig(ch, "name"))
    return {
        "platform": "youtube",
        "id": str(cid or ""),
        "handle": first(dig(ch, "handle"), dig(ch, "channel_handle")),
        "name": name,
        "bio": truncate(first(dig(ch, "description"), dig(ch, "about")), 400),
        "followers": to_int(first(dig(ch, "subscriber_count"), dig(ch, "subscribers"), default=0)),
        "following": 0,
        "posts": to_int(first(dig(ch, "video_count"), default=0)),
        "verified": bool(dig(ch, "is_verified", default=False)),
        "avatar": first(dig(ch, "avatar"), dig(ch, "thumbnails.0.url"), default=None),
        "url": ("https://www.youtube.com/channel/%s" % cid) if cid else None,
    }


# ---------------------------------------------------------------- X / Twitter
def tw_user(u: dict) -> dict:
    un = first(dig(u, "screen_name"), dig(u, "username"), dig(u, "user_info.screen_name"))
    return {
        "platform": "twitter",
        "id": str(first(dig(u, "rest_id"), dig(u, "id_str"), dig(u, "user_info.rest_id"), default="")),
        "handle": un,
        "name": first(dig(u, "name"), dig(u, "user_info.name"), un),
        "bio": truncate(first(dig(u, "description"), dig(u, "desc"), dig(u, "user_info.description")), 400),
        "followers": to_int(first(dig(u, "followers_count"), dig(u, "user_info.followers_count"), default=0)),
        "following": to_int(first(dig(u, "friends_count"), dig(u, "following_count"), default=0)),
        "posts": to_int(first(dig(u, "statuses_count"), dig(u, "tweets_count"), default=0)),
        "verified": bool(first(dig(u, "is_blue_verified"), dig(u, "verified"), default=False)),
        "avatar": first(dig(u, "profile_image_url_https"), dig(u, "avatar"), default=None),
        "url": ("https://x.com/%s" % un) if un else None,
    }


def tw_tweet(t: dict) -> dict:
    tid = first(dig(t, "tweet_id"), dig(t, "id"), dig(t, "id_str"))
    un = first(dig(t, "screen_name"), dig(t, "user_info.screen_name"))
    return {
        "platform": "twitter",
        "id": str(tid or ""),
        "url": ("https://x.com/%s/status/%s" % (un, tid)) if un and tid else None,
        "author": {
            "id": str(first(dig(t, "user_info.rest_id"), default="")),
            "handle": un,
            "name": first(dig(t, "user_info.name"), un),
        },
        "text": truncate(first(dig(t, "text"), dig(t, "full_text")), 1200),
        "created_at": dig(t, "created_at"),
        "stats": {
            "likes": to_int(first(dig(t, "favorites"), dig(t, "favorite_count"), default=0)),
            "comments": to_int(first(dig(t, "replies"), dig(t, "reply_count"), default=0)),
            "shares": to_int(first(dig(t, "retweets"), dig(t, "retweet_count"), default=0)),
            "views": to_int(first(dig(t, "views"), dig(t, "view_count"), default=0)),
            "collects": to_int(first(dig(t, "bookmarks"), default=0)),
        },
        "cover": first(dig(t, "media.0.media_url_https"), dig(t, "media.0.url"), default=None),
    }


def tw_comment(c: dict) -> dict:
    ui = first(dig(c, "user_info"), dig(c, "user"), default={}) or {}
    return {
        "platform": "twitter",
        "id": str(first(dig(c, "tweet_id"), dig(c, "id"), default="")),
        "post_id": str(first(dig(c, "conversation_id"), default="")),
        "author": {
            "id": str(first(dig(ui, "rest_id"), default="")),
            "handle": first(dig(c, "screen_name"), dig(ui, "screen_name")),
            "name": dig(ui, "name"),
        },
        "text": truncate(first(dig(c, "text"), dig(c, "full_text")), 1000),
        "likes": to_int(first(dig(c, "favorites"), default=0)),
        "replies": to_int(first(dig(c, "replies"), default=0)),
        "created_at": dig(c, "created_at"),
    }


NORMALIZERS = {
    ("tiktok", "user"): tiktok_user,
    ("tiktok", "post"): tiktok_post,
    ("tiktok", "comment"): tiktok_comment,
    ("douyin", "user"): douyin_user,
    ("douyin", "post"): douyin_post,
    ("douyin", "comment"): douyin_comment,
    ("xiaohongshu", "user"): xhs_user,
    ("xiaohongshu", "post"): xhs_note,
    ("xiaohongshu", "comment"): xhs_comment,
    ("instagram", "user"): ig_user,
    ("instagram", "post"): ig_post,
    ("instagram", "comment"): ig_comment,
    ("youtube", "post"): yt_video,
    ("youtube", "comment"): yt_comment,
    ("youtube", "user"): yt_channel,
    ("twitter", "user"): tw_user,
    ("twitter", "post"): tw_tweet,
    ("twitter", "comment"): tw_comment,
}


def normalize(platform: str, kind: str, obj: dict, index: int = 0) -> dict:
    if kind == "trend":
        return douyin_trend(obj, index + 1)
    fn = NORMALIZERS.get((platform, kind))
    if fn is None:
        return {"platform": platform, "raw": truncate(obj, 800)}
    try:
        return fn(obj)
    except Exception:  # 单个元素异常不能拖垮整批
        return {"platform": platform, "error": "normalize_failed"}
