"""SQLite persistence (written in batches off the event loop)."""
import sqlite3

from .models import Result


class Store:
    def __init__(self, path: str):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.execute("DROP TABLE IF EXISTS transactions")
        self.conn.execute("DROP TABLE IF EXISTS balances")
        self.conn.execute(
            "CREATE TABLE transactions (txn_id TEXT, account TEXT, type TEXT, to_account TEXT, "
            "amount_cents INTEGER, status TEXT, reason TEXT, latency_ms REAL)"
        )
        self.conn.execute("CREATE TABLE balances (account TEXT PRIMARY KEY, balance_cents INTEGER)")
        self.conn.commit()

    def insert_results(self, results: list[Result]) -> None:
        self.conn.executemany(
            "INSERT INTO transactions VALUES (?,?,?,?,?,?,?,?)",
            [(r.txn.txn_id, r.txn.account, r.txn.type, r.txn.to_account, r.txn.amount_cents,
              r.status, r.reason, round(r.latency_ms, 3)) for r in results],
        )
        self.conn.commit()

    def save_balances(self, balances: dict[str, int]) -> None:
        self.conn.executemany("INSERT INTO balances VALUES (?,?)", list(balances.items()))
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()
