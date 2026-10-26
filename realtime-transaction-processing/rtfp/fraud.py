"""Streaming fraud rules (stateful): large amounts and per-account velocity in a sliding window."""
from collections import defaultdict, deque

from .models import Transaction


class FraudDetector:
    def __init__(self, high_amount_cents: int = 500_000, max_per_window: int = 5, window_s: float = 10.0):
        self.high_amount_cents = high_amount_cents
        self.max_per_window = max_per_window
        self.window_s = window_s
        self._recent: dict[str, deque] = defaultdict(deque)

    def check(self, t: Transaction) -> str | None:
        """Return a hold reason, or None. Uses event time so results are deterministic."""
        q = self._recent[t.account]
        q.append(t.ts)
        while q and t.ts - q[0] > self.window_s:
            q.popleft()
        if t.amount_cents >= self.high_amount_cents:
            return "HIGH_AMOUNT"
        if len(q) > self.max_per_window:
            return "VELOCITY"
        return None
