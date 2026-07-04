from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass
from threading import Lock

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response


@dataclass(frozen=True)
class RateLimitRule:
    limit: int
    window_seconds: int


class InMemoryRateLimitMiddleware(BaseHTTPMiddleware):
    """Small per-process IP rate limiter for MVP public deployments."""

    def __init__(self, app, default_rule: RateLimitRule, path_rules: dict[str, RateLimitRule] | None = None):
        super().__init__(app)
        self.default_rule = default_rule
        self.path_rules = path_rules or {}
        self.requests: dict[tuple[str, str], deque[float]] = defaultdict(deque)
        self.lock = Lock()

    async def dispatch(self, request: Request, call_next) -> Response:
        rule = self._rule_for(request.url.path)
        if rule is None:
            return await call_next(request)

        client_ip = self._client_ip(request)
        key = (client_ip, request.url.path)
        now = time.monotonic()

        with self.lock:
            bucket = self.requests[key]
            cutoff = now - rule.window_seconds
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()

            if len(bucket) >= rule.limit:
                retry_after = max(1, int(rule.window_seconds - (now - bucket[0])))
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "Rate limit exceeded. Please wait before trying again.",
                        "retry_after_seconds": retry_after,
                    },
                    headers={"Retry-After": str(retry_after)},
                )

            bucket.append(now)

        return await call_next(request)

    def _rule_for(self, path: str) -> RateLimitRule | None:
        if not path.startswith("/v1/"):
            return None
        return self.path_rules.get(path, self.default_rule)

    def _client_ip(self, request: Request) -> str:
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",", 1)[0].strip()
        return request.client.host if request.client else "unknown"
