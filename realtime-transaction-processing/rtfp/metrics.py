"""Throughput, latency and outcome metrics."""
import statistics
from collections import Counter

from .models import Result


class Metrics:
    def __init__(self):
        self.status = Counter()
        self.reasons = Counter()
        self.latencies: list[float] = []

    def record(self, r: Result) -> None:
        self.status[r.status] += 1
        if r.reason:
            self.reasons[f"{r.status}:{r.reason}"] += 1
        self.latencies.append(r.latency_ms)

    @property
    def total(self) -> int:
        return sum(self.status.values())

    def report(self, elapsed_s: float) -> dict:
        lat = sorted(self.latencies)

        def pct(p):
            return round(lat[min(len(lat) - 1, int(len(lat) * p))], 2) if lat else 0.0

        return {
            "processed": self.total,
            "elapsed_s": round(elapsed_s, 3),
            "throughput_tps": round(self.total / elapsed_s, 1) if elapsed_s > 0 else 0.0,
            "status": dict(self.status),
            "reasons": dict(self.reasons.most_common()),
            "latency_ms": {
                "mean": round(statistics.fmean(lat), 2) if lat else 0.0,
                "p50": pct(0.50), "p95": pct(0.95), "p99": pct(0.99),
                "max": round(lat[-1], 2) if lat else 0.0,
            },
        }
