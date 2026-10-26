"""In-memory account ledger with an integrity (reconciliation) check."""
from .models import Transaction


class Ledger:
    def __init__(self, accounts, initial_cents: int = 100_000):
        self.balances = {a: initial_cents for a in accounts}
        self.initial_total = initial_cents * len(self.balances)
        self.net_external = 0  # deposits minus withdrawals (money entering/leaving the system)

    def apply(self, t: Transaction) -> str | None:
        """Apply an approved transaction. Returns a rejection reason or None.

        There is no `await` between the balance check and the update, so on a single
        event loop each transaction is atomic.
        """
        if t.type == "deposit":
            self.balances[t.account] += t.amount_cents
            self.net_external += t.amount_cents
        elif t.type == "withdrawal":
            if self.balances[t.account] < t.amount_cents:
                return "INSUFFICIENT_FUNDS"
            self.balances[t.account] -= t.amount_cents
            self.net_external -= t.amount_cents
        elif t.type == "transfer":
            if self.balances[t.account] < t.amount_cents:
                return "INSUFFICIENT_FUNDS"
            self.balances[t.account] -= t.amount_cents
            self.balances[t.to_account] += t.amount_cents
        return None

    def reconciles(self) -> bool:
        """Total money must equal the starting total plus net external flow."""
        return sum(self.balances.values()) == self.initial_total + self.net_external
