"""Bounded API security middleware with safe request correlation."""

from __future__ import annotations

import asyncio
import json
import logging
import math
from collections import deque
from dataclasses import dataclass
from time import monotonic, perf_counter
from typing import Any
from uuid import uuid4

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

LOGGER = logging.getLogger("leanci.access")
_API_SECURITY_HEADERS = {
    "Cache-Control": "no-store",
    "Content-Security-Policy": (
        "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
    ),
    "Cross-Origin-Opener-Policy": "same-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-Permitted-Cross-Domain-Policies": "none",
}


def _request_id(scope: Scope) -> str:
    state: dict[str, Any] = scope.setdefault("state", {})
    value = state.get("request_id")
    if isinstance(value, str):
        return value
    value = uuid4().hex
    state["request_id"] = value
    return value


def _route_label(scope: Scope) -> str:
    """Return a fixed label so access logs never contain caller-controlled paths."""

    path = str(scope.get("path", ""))
    if path == "/api/analyze":
        return "analyze"
    if path == "/api/health":
        return "health"
    if path == "/api/config-status":
        return "config_status"
    if path == "/api/samples":
        return "samples"
    if path.startswith("/api/samples/"):
        return "sample"
    if path.startswith("/api/captures/"):
        return "capture"
    if path == "/api/benchmark/results":
        return "benchmark_results"
    return "unknown"


def _header_values(scope: Scope, name: bytes) -> list[str]:
    values: list[str] = []
    for raw_name, raw_value in scope.get("headers", []):
        if raw_name.lower() == name:
            values.append(raw_value.decode("latin-1").strip())
    return values


async def _send_json_error(
    send: Send,
    scope: Scope,
    *,
    status_code: int,
    code: str,
    message: str,
    extra_headers: dict[str, str] | None = None,
) -> None:
    request_id = _request_id(scope)
    body = json.dumps(
        {
            "error": {
                "code": code,
                "message": message,
                "request_id": request_id,
            }
        },
        separators=(",", ":"),
    ).encode("utf-8")
    headers = [
        (b"content-type", b"application/json"),
        (b"content-length", str(len(body)).encode("ascii")),
        (b"x-request-id", request_id.encode("ascii")),
    ]
    if extra_headers:
        headers.extend(
            (name.lower().encode("ascii"), value.encode("ascii"))
            for name, value in extra_headers.items()
        )
    await send(
        {
            "type": "http.response.start",
            "status": status_code,
            "headers": headers,
        }
    )
    await send({"type": "http.response.body", "body": body})


class RequestSecurityMiddleware:
    """Issue a server-owned request ID, safe access log, and security headers."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = uuid4().hex
        state: dict[str, Any] = scope.setdefault("state", {})
        state["request_id"] = request_id
        status_code = 500
        response_started = False
        started_at = perf_counter()

        async def secure_send(message: Message) -> None:
            nonlocal response_started, status_code
            if message["type"] == "http.response.start":
                response_started = True
                status_code = int(message["status"])
                headers = MutableHeaders(scope=message)
                headers["X-Request-ID"] = request_id
                if str(scope.get("path", "")).startswith("/api/"):
                    for name, value in _API_SECURITY_HEADERS.items():
                        headers[name] = value
            await send(message)

        try:
            await self.app(scope, receive, secure_send)
        except Exception:
            if response_started:
                raise
            await _send_json_error(
                secure_send,
                scope,
                status_code=500,
                code="INTERNAL_ERROR",
                message="The service could not complete the request.",
            )
        finally:
            LOGGER.info(
                "request_id=%s method=%s route=%s status=%d duration_ms=%d",
                request_id,
                str(scope.get("method", "UNKNOWN")).upper(),
                _route_label(scope),
                status_code,
                round((perf_counter() - started_at) * 1000),
            )


class JsonRequestPolicyMiddleware:
    """Require an uncompressed UTF-8 JSON body for the paid analysis endpoint."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if (
            scope["type"] != "http"
            or scope.get("method") != "POST"
            or scope.get("path") != "/api/analyze"
        ):
            await self.app(scope, receive, send)
            return

        content_encodings = _header_values(scope, b"content-encoding")
        if content_encodings and any(value.casefold() != "identity" for value in content_encodings):
            await _send_json_error(
                send,
                scope,
                status_code=415,
                code="UNSUPPORTED_CONTENT_ENCODING",
                message="Compressed request bodies are not accepted.",
            )
            return

        content_types = _header_values(scope, b"content-type")
        if len(content_types) != 1:
            await self._reject_content_type(scope, send)
            return

        parts = [part.strip() for part in content_types[0].split(";")]
        if not parts or parts[0].casefold() != "application/json":
            await self._reject_content_type(scope, send)
            return
        for parameter in parts[1:]:
            if not parameter:
                continue
            name, separator, value = parameter.partition("=")
            if (
                separator
                and name.strip().casefold() == "charset"
                and value.strip().strip("\"'").casefold() not in {"utf-8", "utf8"}
            ):
                await self._reject_content_type(scope, send)
                return

        await self.app(scope, receive, send)

    @staticmethod
    async def _reject_content_type(scope: Scope, send: Send) -> None:
        await _send_json_error(
            send,
            scope,
            status_code=415,
            code="UNSUPPORTED_MEDIA_TYPE",
            message="POST /api/analyze accepts application/json encoded as UTF-8.",
        )


@dataclass(frozen=True)
class _RateLimitDecision:
    allowed: bool
    limit: int
    remaining: int
    reset_seconds: int


class RateLimitMiddleware:
    """Apply bounded in-memory sliding windows to API and analysis requests."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        api_limit: int,
        analyze_limit: int,
        window_seconds: int,
        max_buckets: int,
    ) -> None:
        self.app = app
        self.api_limit = api_limit
        self.analyze_limit = analyze_limit
        self.window_seconds = window_seconds
        self.max_buckets = max_buckets
        self._buckets: dict[tuple[str, str], deque[float]] = {}
        self._lock = asyncio.Lock()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not str(scope.get("path", "")).startswith("/api/"):
            await self.app(scope, receive, send)
            return

        identity = self._client_identity(scope)
        is_analyze = scope.get("method") == "POST" and scope.get("path") == "/api/analyze"
        decision = await self._consume(identity, is_analyze=is_analyze)
        rate_headers = {
            "RateLimit-Limit": str(decision.limit),
            "RateLimit-Remaining": str(decision.remaining),
            "RateLimit-Reset": str(decision.reset_seconds),
        }
        if not decision.allowed:
            await _send_json_error(
                send,
                scope,
                status_code=429,
                code="RATE_LIMITED",
                message="Too many requests. Wait briefly before retrying.",
                extra_headers={
                    **rate_headers,
                    "Retry-After": str(decision.reset_seconds),
                },
            )
            return

        async def send_with_rate_limit(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                for name, value in rate_headers.items():
                    headers[name] = value
            await send(message)

        await self.app(scope, receive, send_with_rate_limit)

    @staticmethod
    def _client_identity(scope: Scope) -> str:
        client = scope.get("client")
        if isinstance(client, tuple) and client:
            return str(client[0])
        return "unknown"

    async def _consume(self, identity: str, *, is_analyze: bool) -> _RateLimitDecision:
        now = monotonic()
        specifications = [("api", self.api_limit)]
        if is_analyze:
            specifications.append(("analyze", self.analyze_limit))

        async with self._lock:
            self._prune_expired(now)
            missing = sum(
                (identity, category) not in self._buckets for category, _ in specifications
            )
            if len(self._buckets) + missing > self.max_buckets:
                return _RateLimitDecision(
                    allowed=False,
                    limit=self.api_limit,
                    remaining=0,
                    reset_seconds=self.window_seconds,
                )

            active: list[tuple[deque[float], int]] = []
            for category, limit in specifications:
                bucket = self._buckets.setdefault((identity, category), deque())
                active.append((bucket, limit))

            denied = [(bucket, limit) for bucket, limit in active if len(bucket) >= limit]
            if denied:
                bucket, limit = min(denied, key=lambda item: item[1])
                reset = max(1, math.ceil(self.window_seconds - (now - bucket[0])))
                return _RateLimitDecision(
                    allowed=False,
                    limit=limit,
                    remaining=0,
                    reset_seconds=reset,
                )

            for bucket, _limit in active:
                bucket.append(now)
            bucket, limit = min(active, key=lambda item: item[1])
            reset = max(1, math.ceil(self.window_seconds - (now - bucket[0])))
            return _RateLimitDecision(
                allowed=True,
                limit=limit,
                remaining=max(0, limit - len(bucket)),
                reset_seconds=reset,
            )

    def _prune_expired(self, now: float) -> None:
        cutoff = now - self.window_seconds
        empty: list[tuple[str, str]] = []
        for key, bucket in self._buckets.items():
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if not bucket:
                empty.append(key)
        for key in empty:
            self._buckets.pop(key, None)


class AnalysisConcurrencyLimitMiddleware:
    """Reject excess paid work instead of allowing an unbounded request queue."""

    def __init__(self, app: ASGIApp, *, maximum: int) -> None:
        self.app = app
        self.maximum = maximum
        self._active = 0
        self._lock = asyncio.Lock()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if (
            scope["type"] != "http"
            or scope.get("method") != "POST"
            or scope.get("path") != "/api/analyze"
        ):
            await self.app(scope, receive, send)
            return

        async with self._lock:
            if self._active >= self.maximum:
                await _send_json_error(
                    send,
                    scope,
                    status_code=429,
                    code="ANALYSIS_BUSY",
                    message="Another analysis is in progress. Retry after it finishes.",
                    extra_headers={"Retry-After": "1"},
                )
                return
            self._active += 1

        try:
            await self.app(scope, receive, send)
        finally:
            async with self._lock:
                self._active -= 1
