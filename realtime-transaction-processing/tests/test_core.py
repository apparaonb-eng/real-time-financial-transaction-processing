import asyncio
import os
import tempfile
import unittest

from rtfp.engine import run
from rtfp.fraud import FraudDetector
from rtfp.ledger import Ledger
from rtfp.models import Transaction
from rtfp.processor import Processor
from rtfp.validator import validate

ACCTS = ["A", "B"]


def tx(id_, acct="A", type_="deposit", amt=1000, to=None, ts=0.0, ccy="USD"):
    return Transaction(id_, acct, type_, amt, ccy, to, ts)


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.p = Processor(Ledger(ACCTS, 10_000), FraudDetector(high_amount_cents=50_000, max_per_window=4))

    def test_validation(self):
        self.assertEqual(validate(tx("1", amt=-5), ACCTS), "INVALID_AMOUNT")
        self.assertEqual(validate(tx("1", type_="bogus"), ACCTS), "INVALID_TYPE")
        self.assertEqual(validate(tx("1", acct="Z"), ACCTS), "UNKNOWN_ACCOUNT")
        self.assertEqual(validate(tx("1", type_="transfer", to="A"), ACCTS), "SELF_TRANSFER")
        self.assertIsNone(validate(tx("1"), ACCTS))

    def test_idempotency(self):
        self.assertEqual(self.p.process(tx("1"))[0], "APPROVED")
        self.assertEqual(self.p.process(tx("1")), ("REJECTED", "DUPLICATE"))
        self.assertEqual(self.p.ledger.balances["A"], 11_000)  # applied once

    def test_insufficient_funds(self):
        self.assertEqual(self.p.process(tx("1", type_="withdrawal", amt=20_000)), ("REJECTED", "INSUFFICIENT_FUNDS"))

    def test_transfer_moves_money(self):
        self.p.process(tx("1", type_="transfer", amt=4_000, to="B"))
        self.assertEqual((self.p.ledger.balances["A"], self.p.ledger.balances["B"]), (6_000, 14_000))
        self.assertTrue(self.p.ledger.reconciles())

    def test_fraud_high_amount_and_velocity(self):
        self.assertEqual(self.p.process(tx("1", amt=60_000)), ("HELD", "HIGH_AMOUNT"))
        for i in range(2, 5):
            self.assertEqual(self.p.process(tx(str(i), ts=i * 0.1))[0], "APPROVED")
        self.assertEqual(self.p.process(tx("9", ts=0.9)), ("HELD", "VELOCITY"))
        self.assertEqual(self.p.process(tx("10", ts=50.0))[0], "APPROVED")  # window expired


class EngineTest(unittest.TestCase):
    def test_end_to_end_reconciles(self):
        with tempfile.TemporaryDirectory() as d:
            r = asyncio.run(run(count=1500, rate=0, workers=4, db_path=os.path.join(d, "t.db"), quiet=True))
        self.assertEqual(r["processed"], 1500)
        self.assertTrue(r["reconciled"])
        self.assertEqual(sum(r["status"].values()), 1500)


if __name__ == "__main__":
    unittest.main()
