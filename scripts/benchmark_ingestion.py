"""Reproducible ingestion benchmark: records actual client-side latency and failures."""
import argparse
import concurrent.futures
import statistics
import time
from datetime import datetime, timezone
from uuid import uuid4
import httpx


def send(client: httpx.Client, base_url: str, sequence: int) -> tuple[float, int]:
    payload = {"event_id": f"benchmark-{uuid4().hex}", "schema_version": 1,
               "event_type": "agent.tool_completed", "event_time": datetime.now(timezone.utc).isoformat(),
               "run_id": f"benchmark-run-{sequence}", "agent_id": "benchmark-agent",
               "tool_name": "synthetic", "latency_ms": 25, "success": True}
    started = time.perf_counter()
    response = client.post(f"{base_url}/v1/events", json=payload)
    return (time.perf_counter() - started) * 1000, response.status_code


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--events", type=int, default=1000)
    parser.add_argument("--concurrency", type=int, default=10)
    args = parser.parse_args()
    started = time.perf_counter()
    with httpx.Client(timeout=20) as client, concurrent.futures.ThreadPoolExecutor(args.concurrency) as pool:
        results = list(pool.map(lambda index: send(client, args.url, index), range(args.events)))
    elapsed = time.perf_counter() - started
    latencies = sorted(latency for latency, _ in results)
    success = sum(status in (200, 201) for _, status in results)
    percentile = lambda p: latencies[min(int(len(latencies) * p), len(latencies) - 1)]
    print({"events": args.events, "concurrency": args.concurrency, "successful": success,
           "duration_seconds": round(elapsed, 3), "events_per_second": round(args.events / elapsed, 2),
           "p50_ms": round(percentile(.50), 2), "p95_ms": round(percentile(.95), 2), "p99_ms": round(percentile(.99), 2)})


if __name__ == "__main__":
    main()
