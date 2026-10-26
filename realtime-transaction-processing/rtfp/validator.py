"""Stateless validation of an incoming transaction."""
from .models import Transaction

VALID_TYPES = {"deposit", "withdrawal", "transfer"}
VALID_CURRENCIES = {"USD"}


def validate(t: Transaction, known_accounts) -> str | None:
    """Return a rejection reason, or None if the transaction is well-formed."""
    if not t.txn_id:
        return "MISSING_ID"
    if t.type not in VALID_TYPES:
        return "INVALID_TYPE"
    if t.amount_cents <= 0:
        return "INVALID_AMOUNT"
    if t.currency not in VALID_CURRENCIES:
        return "UNSUPPORTED_CURRENCY"
    if t.account not in known_accounts:
        return "UNKNOWN_ACCOUNT"
    if t.type == "transfer":
        if t.to_account not in known_accounts:
            return "UNKNOWN_DESTINATION"
        if t.to_account == t.account:
            return "SELF_TRANSFER"
    return None
