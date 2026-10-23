"""评论洞察 —— 把一堆评论压成结论，而不是把 JSON 丢回去。

v1 用关键词与词频，不依赖外部模型，毫秒级返回。
"""
from __future__ import annotations

import re
from collections import Counter
from typing import Any

from .util import truncate

POS = ["好", "赞", "喜欢", "爱了", "不错", "棒", "惊艳", "值得", "想要", "太美", "实用", "有用", "香",
       "love", "great", "awesome", "amazing", "nice", "good", "best", "perfect", "beautiful", "fire",
       "obsessed", "need", "want", "thank"]
NEG = ["差", "贵", "坑", "难用", "失望", "骗", "退货", "假", "垃圾", "丑", "难吃", "没用", "不值",
       "bad", "worst", "scam", "fake", "expensive", "hate", "disappointed", "broken", "trash", "refund"]
Q_WORDS = ["?", "？", "怎么", "如何", "多少", "哪里", "哪儿", "哪个", "有没有", "能不能", "可不可以",
           "how", "what", "where", "which", "why", "does", "can i", "price", "link"]
STOP = set("""the and for you with this that from have are was were will can just not but they your our
about into over out more most some any all one two get got make made very much also how what where when
which who why is are am be been being do does did done a an of to in on at by as it its i me my we us
了 的 是 我 你 他 她 它 们 在 有 和 就 都 也 很 还 不 这 那 个 上 下 好 啊 吧 呢 吗 呀 哦 嗯 一个 真的
太 都 会 说 要 去 来 看 想 觉得 没有 什么 怎么 可以 这个 那个""".split())


def _lang_split(text: str):
    """中英分开：中文取二字/三字词，英文取单词。"""
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"@[\w.]+", " ", text)
    en = [w.lower() for w in re.findall(r"[A-Za-z][A-Za-z']{2,}", text) if w.lower() not in STOP]
    zh_src = re.sub(r"[^\u4e00-\u9fff]+", " ", text)
    zh = []
    for seg in zh_src.split():
        for n in (2, 3):
            for i in range(len(seg) - n + 1):
                gram = seg[i:i + n]
                if gram not in STOP:
                    zh.append(gram)
    return en, zh


def analyze(comments: list[dict], post: dict | None = None) -> dict:
    texts = [(c.get("text") or "") for c in comments]
    texts = [t for t in texts if t.strip()]
    total = len(texts)
    joined = "\n".join(texts).lower()

    pos_hits = sum(joined.count(w.lower()) for w in POS)
    neg_hits = sum(joined.count(w.lower()) for w in NEG)
    # 按条判定，避免一条长评论淹没整体
    per_pos = sum(1 for t in texts if any(w.lower() in t.lower() for w in POS))
    per_neg = sum(1 for t in texts if any(w.lower() in t.lower() for w in NEG))
    questions = sum(1 for t in texts if any(w.lower() in t.lower() for w in Q_WORDS))

    en, zh = [], []
    for t in texts:
        e, z = _lang_split(t)
        en += e
        zh += z

    phrases = Counter()
    phrases.update(en)
    # 中文字符级 n-gram 噪音大，取出现 >= 2 的，且同一评论只计一次
    zh_counter = Counter()
    for t in texts:
        _, z = _lang_split(t)
        for g in set(z):
            zh_counter[g] += 1
    phrases.update({k: v for k, v in zh_counter.items() if v >= 2})
    top_phrases = [{"phrase": k, "count": v} for k, v in phrases.most_common(15) if v >= 2][:15]

    top_liked = sorted(
        [c for c in comments if (c.get("text") or "").strip()],
        key=lambda c: c.get("likes") or 0, reverse=True)[:5]

    likes = [c.get("likes") or 0 for c in comments if isinstance(c.get("likes"), int)]
    summary_bits = []
    if total:
        summary_bits.append("共分析 %d 条评论" % total)
        if questions:
            summary_bits.append("其中 %d 条（%.0f%%）是提问，说明购买意图明确"
                                % (questions, questions * 100.0 / total))
        if per_pos or per_neg:
            tone = "正面为主" if per_pos > per_neg * 1.5 else ("负面偏多" if per_neg > per_pos else "褒贬接近")
            summary_bits.append("情绪%s（正面 %d 条 / 负面 %d 条）" % (tone, per_pos, per_neg))
        if top_phrases:
            summary_bits.append("高频词：%s" % "、".join(p["phrase"] for p in top_phrases[:5]))
        if likes:
            summary_bits.append("单条最高点赞 %d" % max(likes))

    return {
        "total": total,
        "sentiment": {
            "positive": per_pos,
            "negative": per_neg,
            "neutral": max(0, total - per_pos - per_neg),
            "positive_hits": pos_hits,
            "negative_hits": neg_hits,
        },
        "questions": {"count": questions, "ratio": round(questions / total, 3) if total else 0.0},
        "engagement": {"max_likes": max(likes) if likes else 0,
                       "avg_likes": round(sum(likes) / len(likes), 1) if likes else 0},
        "top_phrases": top_phrases,
        "top_liked": [{"text": truncate(c.get("text"), 160), "likes": c.get("likes") or 0,
                       "author": (c.get("author") or {}).get("name")} for c in top_liked],
        "summary": "；".join(summary_bits) or "没有取到评论内容",
        "post": {k: post.get(k) for k in ("platform", "id", "text", "stats")} if post else None,
    }
