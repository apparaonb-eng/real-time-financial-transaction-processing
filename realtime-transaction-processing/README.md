# Real-Time Financial Transaction Processing (base)

An asyncio streaming engine that validates, screens and settles financial transactions as they arrive.
Standard library only (Python 3.10+).

```
generator -> producer -> [queue per worker, keyed by account] -> workers -> batch writer -> SQLite
                                   (bounded = back-pressure)       |
                                                  validate -> idempotency -> fraud rules -> ledger
```

## Run
```bash
python main.py                                  # 2,000 txns at 1,000/s
python main.py --count 20000 --rate 0           # unthrottled stress test
python -m unittest discover tests -v            # tests
```
Output: a live progress line, a report (throughput, outcomes, rejection reasons, latency percentiles,
ledger reconciliation) and `transactions.db` (tables `transactions`, `balances`).

## How it works
- **Validation** (`validator.py`): type, amount, currency, known accounts, self-transfer.
- **Idempotency** (`processor.py`): a repeated `txn_id` is rejected as `DUPLICATE`, never applied twice.
- **Fraud rules** (`fraud.py`): `HIGH_AMOUNT` (>= $5,000) and `VELOCITY` (more than 5 per account in 10s) put a
  transaction on `HELD` for review instead of settling it.
- **Ledger** (`ledger.py`): integer cents, `INSUFFICIENT_FUNDS` check, and a reconciliation invariant
  (total balance = starting total + deposits - withdrawals) that must hold after every run.
- **Partitioning** (`engine.py`): events are routed by account, so one account's transactions stay in order
  while accounts run concurrently. Queues are bounded, so a slow consumer slows the producer instead of
  exhausting memory.
- **Persistence**: results are written to SQLite in batches off the event loop.

## Production next steps
Replace the in-process queues with Kafka/Redpanda/Kinesis (partition key = account), persist ledger state
and the idempotency set in a database (e.g. Postgres or Redis) so restarts are safe, add a review workflow for
`HELD` items, an HTTP/gRPC ingestion API, and metrics export (Prometheus). Transfers between accounts on
different partitions are atomic here only because everything runs on one event loop; a distributed version
needs a transactional or saga-based approach.
