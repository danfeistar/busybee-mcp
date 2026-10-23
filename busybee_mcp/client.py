"""HTTP 客户端 —— 只在进程内持有 API Key，不打印、不落盘。"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

DEFAULT_BASE = "https://lucydomi.com"
SIGNUP_URL = "https://lucydomi.com"


class BusyBeeError(Exception):
    """带中文说明的业务异常，直接回给 AI/用户看。"""

    def __init__(self, message: str, code: str = "error", hint: str | None = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.hint = hint

    def as_dict(self) -> dict:
        d = {"ok": False, "error": self.code, "message": self.message}
        if self.hint:
            d["hint"] = self.hint
        return d


class Client:
    def __init__(self, api_key: str | None = None, base_url: str | None = None, timeout: int | None = None):
        self.api_key = api_key or os.environ.get("BUSYBEE_API_KEY") or os.environ.get("XMF_API_KEY")
        self.base_url = (base_url or os.environ.get("BUSYBEE_BASE_URL") or DEFAULT_BASE).rstrip("/")
        self.timeout = int(timeout or os.environ.get("BUSYBEE_TIMEOUT") or 90)
        self._bal_cache: tuple[float, float] | None = None

    # ------------------------------------------------------------ 基础请求
    def _request(self, path: str, params: dict | None = None, method: str = "GET",
                 body: dict | None = None, auth: bool = True) -> dict:
        if auth and not self.api_key:
            raise BusyBeeError(
                "还没有配置 API Key。免费领取地址：%s" % SIGNUP_URL,
                code="no_api_key",
                hint="注册后到「控制台 → API 密钥 → 新建密钥」复制 sk- 开头的串，"
                     "并在客户端里配置环境变量 BUSYBEE_API_KEY。",
            )
        url = self.base_url + path
        if params:
            clean = {k: v for k, v in params.items() if v not in (None, "")}
            if clean:
                url += "?" + urllib.parse.urlencode(clean)
        data = None
        headers = {"Accept": "application/json", "User-Agent": "busybee-mcp/0.1"}
        if auth:
            headers["Authorization"] = "Bearer " + str(self.api_key)
        if body is not None:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, headers=headers,
                                     method="POST" if body is not None else method)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                raw = r.read()
        except urllib.error.HTTPError as e:
            raw = e.read()
            raise self._http_error(e.code, raw) from None
        except urllib.error.URLError as e:
            raise BusyBeeError(
                "连不上服务（%s）。请检查网络后重试。" % getattr(e, "reason", e),
                code="network_error") from None
        try:
            return json.loads(raw)
        except ValueError:
            raise BusyBeeError("服务返回了无法解析的内容，请稍后重试。", code="bad_response") from None

    @staticmethod
    def _http_error(status: int, raw: bytes) -> BusyBeeError:
        msg, hint = None, None
        try:
            j = json.loads(raw)
            err = j.get("error") if isinstance(j, dict) else None
            if isinstance(err, dict):
                msg, hint = err, (err.get("hint") or err.get("groups_cn"))
            elif isinstance(j, dict):
                msg = j.get("message") or j.get("detail")
            if isinstance(msg, dict):
                hint = hint or msg.get("hint")
                msg = msg.get("message_zh") or msg.get("message") or msg.get("msg")
            if msg is not None and not isinstance(msg, str):
                msg = None
        except ValueError:
            pass
        if status == 401:
            return BusyBeeError(msg or "API Key 无效或未登录。", code="unauthorized",
                                hint=hint or "确认 Key 是 sk- 开头且未删除；免费领取：%s" % SIGNUP_URL)
        if status == 402:
            return BusyBeeError(msg or "账户余额不足。", code="insufficient_balance",
                                hint="到 %s 充值后重试。" % SIGNUP_URL)
        if status == 403:
            return BusyBeeError(msg or "当前 API Key 无权调用该平台。", code="forbidden", hint=hint)
        if status == 429:
            return BusyBeeError(msg or "请求太频繁，触发了限流。", code="rate_limited",
                                hint="降低并发或稍后重试。")
        if status >= 500:
            return BusyBeeError(msg or "上游服务暂时不可用（%d）。" % status, code="upstream_error",
                                hint="这通常是临时故障，重试一次通常可恢复。")
        return BusyBeeError(msg or "请求失败（HTTP %d）。" % status, code="http_%d" % status, hint=hint)

    # ------------------------------------------------------------ 业务封装
    def call_endpoint(self, path: str, params: dict | None = None, method: str = "GET",
                      body: dict | None = None) -> dict:
        return self._request(path, params=params, method=method, body=body)

    def me(self) -> dict:
        """账户概览：用户名、余额、分组。"""
        j = self._request("/api/gw/me")
        return j.get("data", j) if isinstance(j, dict) else {}

    def balance_usd(self, fresh: bool = False) -> float | None:
        now = time.time()
        if not fresh and self._bal_cache and now - self._bal_cache[0] < 30:
            return self._bal_cache[1]
        try:
            data = self.me()
        except BusyBeeError:
            return None
        bal = data.get("quota_exact_usd")
        if bal is None:
            bal = data.get("quota_usd")
        if isinstance(bal, (int, float)):
            self._bal_cache = (now, float(bal))
            return float(bal)
        return None

    def pricing(self) -> dict:
        return self._request("/api/gw/pricing")
