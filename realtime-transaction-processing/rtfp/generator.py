"""Synthetic transaction stream: normal traffic plus invalid, duplicate, large and burst events.

Event time (`ts`) comes from a simulated clock (about 4 events/second overall, so each account
averages one transaction every few seconds). This keeps the velocity rule meaningful no matter
how fast the stream is replayed through the engine.
"""
import random
import uuid
from typing import Iterator

from .models import Transaction


def make_accounts(n: int) -> list[str]:
    return [f"ACC{i:03d}" for i in range(1, n + 1)]


def generate(count: int, accounts: list[str], seed: int | None = 42) -> Iterator[Transaction]:
    rnd = random.Random(seed)
    clock = 1_700_000_000.0
    emitted = 0
    last: Transaction | None = None

    def tick(gap: float | None = None) -> float:
        nonlocal clock
        clock += rnd.expovariate(4.0) if gap is None else gap
        return clock

    def new_id() -> str:
        return uuid.UUID(int=rnd.getrandbits(128)).hex[:12]

    def normal(account: str | None = None, gap: float | None = None) -> Transaction:
        kind = rnd.choices(["deposit", "withdrawal", "transfer"], weights=[30, 40, 30])[0]
        acct = account or rnd.choice(accounts)
        amount = max(100, min(int(rnd.lognormvariate(8.0, 0.9)), 200_000))  # mostly tens of dollars
        to = rnd.choice([a for a in accounts if a != acct]) if kind == "transfer" else None
        return Transaction(new_id(), acct, kind, amount, "USD", to, tick(gap))

    while emitted < count:
        roll = rnd.random()
        if roll < 0.02 and last is not None:  # duplicate delivery of an earlier message
            t = Transaction(last.txn_id, last.account, last.type, last.amount_cents,
                            last.currency, last.to_account, tick())
            yield t
            emitted += 1
        elif roll < 0.03:  # invalid transaction
            bad = rnd.choice(["neg", "type", "ccy"])
            b = normal()
            if bad == "neg":
                t = Transaction(b.txn_id, b.account, b.type, -b.amount_cents, "USD", b.to_account, b.ts)
            elif bad == "type":
                t = Transaction(b.txn_id, b.account, "refund??", b.amount_cents, "USD", None, b.ts)
            else:
                t = Transaction(b.txn_id, b.account, b.type, b.amount_cents, "XXX", b.to_account, b.ts)
            yield t
            emitted += 1
        elif roll < 0.04:  # unusually large withdrawal
            b = normal()
            t = Transaction(b.txn_id, b.account, "withdrawal", rnd.randint(600_000, 2_000_000), "USD", None, b.ts)
            yield t
            emitted += 1
            last = t
        elif roll < 0.05:  # velocity burst: 8 transactions from one account within ~70ms
            acct = rnd.choice(accounts)
            for _ in range(8):
                if emitted >= count:
                    break
                t = normal(acct, gap=0.01)
                yield t
                emitted += 1
                last = t
        else:
            t = normal()
            yield t
            emitted += 1
            last = t
