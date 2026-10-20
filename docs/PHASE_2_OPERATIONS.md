# Phase 2 Operations Runbook

## Service responsibilities

| Service | Responsibility | Recovery action |
|---|---|---|
| `api` | Validate events, write PostgreSQL/raw Parquet, enqueue transactional outbox records, expose APIs and metrics. | Restart after checking PostgreSQL. Pending outbox records are safe to retry. |
| `dispatcher` | Publishes pending outbox records to Kafka with idempotent producer settings. | Restart; it retries all `pending` records. |
| `kafka` | Durable event transport. | Restore broker storage; do not delete its volume during incident response. |
| `consumer` | Updates idempotent streaming windows. Retries failed events three times, then writes to the DLQ. | Inspect `agent-events.v1.dlq`, fix the cause, and republish corrected events with a new ID only if payload changes. |
| `prometheus` / `grafana` | Scrape and show platform health. | Verify `/metrics`, targets, and alert rules. |

## Key signals

- `ai_data_events_rejected_total`: contract or duplicate-conflict failures.
- `ai_data_consumer_lag`: unprocessed Kafka messages by topic/partition.
- `ai_data_processing_failures_total`: consumer or processing failures.
- `ai_data_dataset_freshness_seconds`: age of the newest published metrics dataset.
- `ai_data_dataset_quality_status`: `1` means the most recent dataset passed quality gates.

## Failure exercise

1. Start the stack with `docker compose up --build`.
2. Send events through `POST /v1/events`.
3. Stop the `consumer` service: `docker compose stop consumer`.
4. Continue ingestion while the consumer is stopped. Its metrics endpoint is also stopped, so Prometheus/Grafana may show a scrape failure or stale lag gauge during this interval.
5. Start the consumer: `docker compose start consumer`.
6. Observe whether lag drains after processing resumes, then run `POST /v1/reconciliation` over the affected window. Record the actual response; do not assume it will be matched.

The current lag gauge is updated when the consumer processes a record; it is not an independent broker-side lag exporter and does not provide a reliable live reading while the consumer is stopped.

## Reconciliation semantics

Streaming and batch reconciliation compare the same event-based hourly values: event count, failure count, retry count, and average latency. Late events are assigned to the hour of `event_time`; they appear in a later streaming update to that historical window. The reconciliation endpoint intentionally reports differences rather than silently correcting them.

## Kafka recovery policy

- The API first persists an event and its outbox record in PostgreSQL.
- Kafka publication uses `acks=all` and idempotent producer settings.
- Dispatcher failures leave outbox records `pending`; they are retried every two seconds.
- Consumer processing is idempotent per `event_id`.
- A failed message is republished to a retry topic up to three times, then sent to `agent-events.v1.dlq` with failure context in headers.

## Scope note: CDC

Debezium is intentionally not enabled in the default Phase 2 stack because no source database/change contract has been specified. It is an optional connector, not a safe generic feed: enabling it requires an owned source PostgreSQL database, logical-replication settings, a table allow-list, retention rules, and a schema-evolution contract. The Kafka pipeline is ready to accept its resulting versioned events once those controls are defined.
