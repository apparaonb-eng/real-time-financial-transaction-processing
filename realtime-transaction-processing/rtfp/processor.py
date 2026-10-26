"""Decision logic for one transaction: validate -> idempotency -> fraud -> ledger."""
from .fraud import FraudDetector
from .ledger import Ledger
from .models import Transaction
from .validator import validate


class Processor:
    def __init__(self, ledger: Ledger, fraud: FraudDetector):
        self.ledger = ledger
        self.fraud = fraud
        self._seen: set[str] = set()

    def process(self, t: Transaction) -> tuple[str, str | None]:
        reason = validate(t, self.ledger.balances)
        if reason:
            return "REJECTED", reason
        if t.txn_id in self._seen:  # idempotency: a retried/duplicated message is not applied twice
            return "REJECTED", "DUPLICATE"
        self._seen.add(t.txn_id)
        hold = self.fraud.check(t)
        if hold:
            return "HELD", hold
        reason = self.ledger.apply(t)
        if reason:
            return "REJECTED", reason
        return "APPROVED", None
