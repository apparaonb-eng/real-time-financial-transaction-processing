"""CLI entry point.

Usage:
    python main.py                              # 2,000 txns at 1,000/s
    python main.py --count 20000 --rate 0       # unthrottled stress run
    python main.py --workers 8 --accounts 50
"""
import argparse
import asyncio

from rtfp.engine import run


def main():
    ap = argparse.ArgumentParser(description="Real-Time Financial Transaction Processing")
    ap.add_argument("--count", type=int, default=2000, help="number of transactions to stream")
    ap.add_argument("--rate", type=float, default=1000.0, help="transactions/second (0 = unthrottled)")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--accounts", type=int, default=20)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--db", default="transactions.db")
    a = ap.parse_args()

    print(f"Streaming {a.count} transactions (rate={a.rate or 'max'}/s, workers={a.workers})")
    r = asyncio.run(run(a.count, a.rate, a.workers, a.db, a.seed, a.accounts))

    print("\n=== Report ===")
    print(f"Processed : {r['processed']} in {r['elapsed_s']}s  ->  {r['throughput_tps']:,} tps")
    print(f"Outcomes  : {r['status']}")
    print("Reasons   :")
    for k, v in r["reasons"].items():
        print(f"  {k:<32}{v}")
    l = r["latency_ms"]
    print(f"Latency ms: mean={l['mean']}  p50={l['p50']}  p95={l['p95']}  p99={l['p99']}  max={l['max']}")
    print(f"Ledger reconciles: {r['reconciled']}   (total ${r['total_balance_cents'] / 100:,.2f})")
    print(f"Saved to  : {r['database']}")


if __name__ == "__main__":
    main()
