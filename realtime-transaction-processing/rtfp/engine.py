"""Streaming engine.

producer -> [partitioned queues, one per worker, keyed by account] -> workers -> result queue -> batch writer

Partitioning by account keeps each account's events in order (needed for correct
velocity checks and balance updates) while different accounts are handled concurrently.
"""
import asyncio
import dataclasses
import time
import zlib

from .fraud import FraudDetector
from .generator import generate, make_accounts
from .ledger import Ledger
from .metrics import Metrics
from .models import Result
from .processor import Processor
from .store import Store

_TICK = object()


async def _producer(txns, queues, rate: float):
    start = time.perf_counter()
    for i, t in enumerate(txns):
        if rate > 0:  # pace the stream; rate 0 = as fast as possible
            delay = start + i / rate - time.perf_counter()
            if delay > 0:
                await asyncio.sleep(delay)
        t = dataclasses.replace(t, received_at=time.time())
        idx = zlib.crc32(t.account.encode()) % len(queues)
        await queues[idx].put(t)  # bounded queue -> back-pressure on the producer
    for q in queues:
        await q.put(None)


async def _worker(q, processor: Processor, results: asyncio.Queue, metrics: Metrics):
    while True:
        t = await q.get()
        if t is None:
            break
        status, reason = processor.process(t)
        latency_ms = (time.time() - t.received_at) * 1000
        r = Result(t, status, reason, latency_ms)
        metrics.record(r)
        await results.put(r)


async def _writer(results: asyncio.Queue, store: Store, batch_size=200, flush_s=0.5):
    batch: list[Result] = []
    while True:
        try:
            item = await asyncio.wait_for(results.get(), timeout=flush_s)
        except asyncio.TimeoutError:
            item = _TICK
        if item is None:
            break
        if item is not _TICK:
            batch.append(item)
        if batch and (len(batch) >= batch_size or item is _TICK):
            await asyncio.to_thread(store.insert_results, batch)
            batch = []
    if batch:
        await asyncio.to_thread(store.insert_results, batch)


async def _monitor(metrics: Metrics, total: int, start: float):
    while True:
        await asyncio.sleep(1.0)
        el = time.perf_counter() - start
        print(f"  ... {metrics.total}/{total} processed ({metrics.total / el:,.0f} tps)")


async def run(count=2000, rate=1000.0, workers=4, db_path="transactions.db",
              seed=42, accounts=20, quiet=False) -> dict:
    account_ids = make_accounts(accounts)
    ledger = Ledger(account_ids)
    processor = Processor(ledger, FraudDetector())
    metrics = Metrics()
    store = Store(db_path)

    queues = [asyncio.Queue(maxsize=1000) for _ in range(workers)]
    results: asyncio.Queue = asyncio.Queue()

    start = time.perf_counter()
    writer = asyncio.create_task(_writer(results, store))
    mon = None if quiet else asyncio.create_task(_monitor(metrics, count, start))
    wtasks = [asyncio.create_task(_worker(q, processor, results, metrics)) for q in queues]

    await _producer(generate(count, account_ids, seed), queues, rate)
    await asyncio.gather(*wtasks)
    elapsed = time.perf_counter() - start

    await results.put(None)
    await writer
    if mon:
        mon.cancel()

    store.save_balances(ledger.balances)
    store.close()

    report = metrics.report(elapsed)
    report["reconciled"] = ledger.reconciles()
    report["total_balance_cents"] = sum(ledger.balances.values())
    report["database"] = db_path
    return report
