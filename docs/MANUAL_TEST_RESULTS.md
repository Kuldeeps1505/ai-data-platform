# Manual Test Results

**Test date:** 18 October 2026  
**Environment:** Local Docker Compose with `sources` and `advanced` profiles enabled.

## Summary

The platform stack started successfully: 19 Compose services were reported running, with PostgreSQL and CDC PostgreSQL healthy. Core event ingestion, metrics, curated analytics, feature serving, unified context, PostgreSQL CDC, Flink execution, and Spark recomputation were manually exercised.

| Test area | Result | Evidence |
|---|---|---|
| Stack startup | Passed | `docker compose --profile sources --profile advanced up -d` reported all 19 services running. |
| Agent event ingestion | Passed | `manual-event-001` was accepted at `2026-10-18T11:31:51.696194Z`. |
| Streaming metrics | Passed | One `manual-agent` event was returned for the 11:00-12:00 UTC window; failure rate was `0.0`, average latency `150 ms`. |
| Curated metrics quality gate | Passed | Dataset `metrics_d7f276f7ff62414097b0f9f24f7ef4b4` was created with `quality_status: passed` and two metric rows. |
| ClickHouse analytics API | Passed | `/v1/access/analytics` returned `source: clickhouse` and a metric row for `manual-agent`. |
| Feature serving | Passed | `manual-agent/success_rate/v1 = 0.95` was stored with the supplied event time. |
| Unified AI context API | Passed | Returned PostgreSQL feature data and Qdrant retrieval results for `manual-agent`. |
| PostgreSQL CDC / Debezium | Passed | Inserted `manual-customer-001`; connector and task were `RUNNING`; its create event was read from `source_app.public.customer_context`. |
| Flink stream processing | Passed | Packaged Flink job was submitted; local JobManager reported the job running. |
| Spark batch recompute | Passed | Spark ran against raw Parquet and created `_SUCCESS` plus a Parquet result under `/data/recomputed/manual-validation-001`. |
| Document ingestion endpoint | Failed | `POST /v1/documents` returned HTTP 500 for `manual-doc-001`. Retrieval still returned an existing indexed document, but new document archival/indexing needs investigation. |

## Key outputs

### Ingestion and analytics

```text
event_id: manual-event-001
status: accepted
dataset_id: metrics_d7f276f7ff62414097b0f9f24f7ef4b4
quality_status: passed
analytics source: clickhouse
manual-agent total_runs: 1
manual-agent failed_runs: 0
manual-agent average_latency_ms: 150.0
```

### CDC

```text
Connector: source-app-postgres
Connector state: RUNNING
Task 0 state: RUNNING
Kafka topic: source_app.public.customer_context
Observed operation: c (create)
Observed customer: manual-customer-001
```

### Spark

```text
Input: /data/raw/event_date=2026-10-18
Output: /data/recomputed/manual-validation-001
Result files: _SUCCESS and part-*.snappy.parquet
```

## Follow-up required

1. Diagnose the HTTP 500 returned by `POST /v1/documents` before accepting the document archive-to-Qdrant path as manually validated.
2. Replace deterministic Qdrant development embeddings with an approved embedding model before using retrieval relevance in production.
3. Configure durable Flink checkpoints and an idempotent/exactly-once sink strategy before production use.
4. Add a scheduled Spark reconciliation comparison before publishing recomputed metrics to ClickHouse.
