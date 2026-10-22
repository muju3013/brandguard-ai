import time
from collections import defaultdict
from typing import Dict, List
from fastapi import Request, HTTPException, status
from app.config import settings

class InMemoryRateLimiter:
    """
    High-performance sliding-window in-memory rate limiter.
    Zero external dependencies, fail-safe against DDoS and Gemini quota starvation.
    """
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.window_seconds = 60.0
        self._history: Dict[str, List[float]] = defaultdict(list)

    def __call__(self, request: Request):
        # Allow disabling or high-limits in test environments if requested
        if settings.environment == "testing" and self.requests_per_minute > 500:
            return

        # Determine client key: combine IP and Authorization header prefix
        client_ip = "127.0.0.1"
        if request.client and request.client.host:
            client_ip = request.client.host
        
        # Check X-Forwarded-For if behind a reverse proxy (e.g. Render, Vercel, Fly.io)
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()

        auth_header = request.headers.get("Authorization", "")
        # Masked token prefix if present
        token_id = auth_header[:24] if auth_header else "anonymous"
        key = f"{client_ip}:{token_id}"

        now = time.time()
        cutoff = now - self.window_seconds
        
        # Prune expired timestamps
        timestamps = [ts for ts in self._history[key] if ts > cutoff]
        self._history[key] = timestamps

        if len(timestamps) >= self.requests_per_minute:
            oldest = timestamps[0]
            retry_after = max(1, int(oldest + self.window_seconds - now))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Maximum {self.requests_per_minute} requests per minute allowed.",
                headers={"Retry-After": str(retry_after)}
            )

        self._history[key].append(now)

# Global rate limiter dependencies
rate_limiter_general = InMemoryRateLimiter(requests_per_minute=settings.rate_limit_per_minute)
rate_limiter_check = InMemoryRateLimiter(requests_per_minute=settings.rate_limit_check_per_minute)
