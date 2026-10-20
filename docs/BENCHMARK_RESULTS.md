# Benchmark Method and Results

## Current status

**No benchmark results are published.** Do not use throughput or latency
numbers on a resume until the run includes the workload, environment,
configuration, raw result, and post-run correctness checks.

The current [benchmark client](../scripts/benchmark_ingestion.py) measures
client-side request latency and status codes, but does not send the required
`X-API-Key` header used by the default Compose configuration. Add and validate
that support before treating its output as useful evidence. The current client
also does not verify persisted event counts, expected metrics, consumer lag,
or reconciliation.

## Required run record

For every run, record:

| Field | Value |
|---|---|
| Date/time (UTC) | Not measured |
| Git commit | Not recorded |
| Environment / CPU / memory | Not recorded |
| OS, Python, Docker versions | Not recorded |
| Compose profile and service configuration | Not recorded |
| Command | `python scripts/benchmark_ingestion.py --events 1000 --concurrency 10` (requires an authenticated client update first) |
| Warm-up and repeat count | Not measured |
| Event count and payload bytes | Not measured |
| Concurrency | Not measured |
| Duration and throughput | Not measured |
| p50 / p95 / p99 client latency | Not measured |
| HTTP success / rejection / error counts | Not measured |
| Accepted unique event IDs after run | Not checked |
| Expected streaming/curated metric result | Not checked |
| Consumer lag and backlog drain time | Not measured |
| Reconciliation outcome | Not checked |

Replace this table with dated measurements only after running the benchmark
against a stated environment and verifying output correctness. Keep local and
cloud measurements separate. Avoid machine-specific CI performance thresholds
until repeated-run variance is understood.
