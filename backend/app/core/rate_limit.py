"""In-process sliding-window rate limiter.

Deliberately in-memory, not Redis-backed: this deployment runs a single
uvicorn process (see the Dockerfile's CMD — no `--workers` flag) and
there is no Redis anywhere in `docker-compose.yml`. If this app is ever
scaled to multiple worker processes or machines, each would track its
own counters independently and the effective limit would multiply by
the process count — move to a shared store (Redis) at that point, not
before. For a small single-process home-server beta deployment this is
simple, dependency-free, and easy to test.
"""
import time
from collections import defaultdict, deque
from datetime import date
from threading import Lock


class RateLimiter:
    """Per-key sliding-window request counter.

    FastAPI runs sync `def` route handlers in a threadpool, so all state
    access is lock-protected. `clock` is injectable so tests can
    simulate the passage of time without real sleeps.
    """

    def __init__(self, limit: int, window_seconds: float, *, clock=time.monotonic):
        self.limit = limit
        self.window_seconds = window_seconds
        self._clock = clock
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str) -> float | None:
        """Record a hit for `key` if under the limit.

        Returns `None` if the request is allowed. Returns the number of
        seconds until the caller may retry if the limit was already
        exceeded (the rejected attempt itself is NOT counted as a hit).
        """
        now = self._clock()
        cutoff = now - self.window_seconds
        with self._lock:
            q = self._hits[key]
            while q and q[0] <= cutoff:
                q.popleft()
            if len(q) >= self.limit:
                return max(q[0] + self.window_seconds - now, 0.0)
            q.append(now)
            return None

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


class DailyCharBudget:
    """Per-key daily character-count budget, calendar-day granularity.

    Separate from RateLimiter (which counts requests, not a variable
    "cost" per request) -- used for /tts's per-account daily character
    cap (Phase H2), where one request can consume anywhere from a few
    to 5,000 characters. In-memory for the same single-process reason
    RateLimiter is (see module docstring); resets naturally at UTC
    midnight since `_usage` is keyed by (key, date).
    """

    def __init__(self, daily_limit: int, *, today=lambda: date.today()):
        self.daily_limit = daily_limit
        self._today = today
        self._usage: dict[tuple[str, date], int] = defaultdict(int)
        self._lock = Lock()

    def reserve(self, key: str, chars: int) -> bool:
        """Attempt to reserve `chars` against today's budget for `key`.

        Returns True and records the usage if under budget, False
        (recording nothing) if it would exceed the daily cap.
        """
        today = self._today()
        with self._lock:
            usage_key = (key, today)
            if self._usage[usage_key] + chars > self.daily_limit:
                return False
            self._usage[usage_key] += chars
            return True

    def reset(self) -> None:
        with self._lock:
            self._usage.clear()


_all_limiters: list[RateLimiter | DailyCharBudget] = []


def register_limiter(limiter: RateLimiter | DailyCharBudget) -> RateLimiter | DailyCharBudget:
    """Track a limiter so `reset_all()` (used between tests) can find it."""
    _all_limiters.append(limiter)
    return limiter


def reset_all() -> None:
    """Clear every registered limiter's state. Test-isolation hook only —
    production code never needs to call this."""
    for limiter in _all_limiters:
        limiter.reset()
