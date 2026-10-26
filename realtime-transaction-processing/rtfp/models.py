"""Core data types. Money is stored as integer cents to avoid floating-point errors."""
import time
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Transaction:
    txn_id: str
    account: str
    type: str                      # deposit | withdrawal | transfer
    amount_cents: int
    currency: str = "USD"
    to_account: str | None = None  # only for transfers
    ts: float = field(default_factory=time.time)  # event time (seconds), used by fraud rules
    received_at: float = 0.0                       # wall-clock time the engine received it


@dataclass
class Result:
    txn: Transaction
    status: str                    # APPROVED | REJECTED | HELD
    reason: str | None
    latency_ms: float              # received -> processed (includes queue wait)
