# Known Limitations and Evidence Gaps

This is the current project status, not a list of production guarantees. The
default Compose stack is for local development and demonstration.

## Validation and correctness

- The current `tests/` directory contains event/document/feature schema tests.
  CI runs `pytest -q`; it does not currently start the required services or
  test the complete event-to-metrics workflow.
- The manual record dated 18 October 2026 says `POST /v1/documents` returned
  HTTP 500. Document ingestion, new-document indexing, and the archive-to-
  retrieval flow are therefore **not validated**. Existing indexed-item
  retrieval was exercised, but that does not prove new-document ingestion.
- Duplicate, retry/DLQ, service interruption, replay idempotency, quality-gate
  failure, and reconciliation-mismatch paths need automated integration tests.
- The synthetic walkthrough in [DEMO.md](./DEMO.md) is documentation, not a
  substitute for CI assertions or a recorded successful run.

## Delivery and streaming

- The transactional outbox makes accepted events retryable when Kafka
  publication is unavailable. Dispatch and consumption can be retried; do not
  describe the complete pipeline as exactly-once.
- Consumer idempotency and streaming window behavior need focused automated
  tests, including duplicate delivery, late events, restarts, and corrected
  events.
- No measured event-latency or consumer-lag service objective has been
  established. Use “near-real-time” only as an architectural intent, not a
  verified latency guarantee.
- The consumer lag gauge is updated during record processing and is served by
  the consumer process itself. It is unavailable while that process is stopped
  and may be stale during an outage; it is not a broker-side lag exporter.
- Reconciliation reports differences; it does not repair or rewrite results.
  Spark output comparison and scheduled reconciliation are not automated.

## Data, retrieval, and evaluation

- The event contract avoids collecting prompt and tool payloads by default.
  The built-in sanitizer covers common email, phone-like, and card-like
  strings; it is not comprehensive DLP. Do not send real sensitive content in
  the demo.
- Qdrant uses deterministic development vectors. No relevance benchmark or
  approved semantic embedding model is established.
- Evaluation endpoints record versioned scenario/result data, but the current
  demo's `human_review` outcome is manually supplied. There is no tested model
  evaluation harness or evidence of repeatable model quality.
- The local data is retained in Docker volumes. Production deletion,
  backup/restore, and retention workflows are not implemented end-to-end.

## Operations and security

- Compose uses local development credentials and plaintext service
  communication. The API key is a shared local guard, not user identity,
  role-based authorization, or production authentication.
- The local API and monitoring ports are published on the host. Do not expose
  the stack publicly.
- Flink's local job lacks durable checkpoints and an idempotent sink strategy.
  The Spark recompute path writes Parquet; publishing a recomputation requires
  a quality and reconciliation decision.
- Prometheus/Grafana provide local signals but are not an on-call, alert
  delivery, or production observability service.
- Terraform is a partial AWS baseline. No cloud environment or cloud
  acceptance test is recorded; required network, managed database/streaming,
  and service rollout decisions remain open.

## Performance evidence

- No benchmark result is currently published. The existing client benchmark
  does not send `X-API-Key`, so it cannot successfully measure the default
  authenticated Compose API until updated.
- Throughput, payload-size impact, p50/p95/p99 latency, consumer drain time,
  and recovery time have not been recorded with a reproducible environment and
  correctness checks. See [BENCHMARK_RESULTS.md](./BENCHMARK_RESULTS.md).

## Documentation status

Capability claims should follow [ARCHITECTURE_EXPANSION.md](./ARCHITECTURE_EXPANSION.md)
and the dated evidence in [MANUAL_TEST_RESULTS.md](./MANUAL_TEST_RESULTS.md).
Update this page when a limitation is resolved and the corresponding test or
dated result is available.
