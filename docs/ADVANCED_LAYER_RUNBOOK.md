# Advanced Processing and Serving Runbook

## Profiles

The default Compose stack is the smallest local path. It has manual evidence,
but its complete event-to-metrics workflow is not yet covered by an automated
integration test. Start optional systems deliberately:

```powershell
docker compose --profile sources up -d
docker compose --profile advanced up -d
```

`sources` starts LocalStack S3, source PostgreSQL, Debezium Connect, and connector setup. `advanced` starts ClickHouse, Qdrant, Flink JobManager/TaskManager, and Spark master/worker.

## Data-product ownership

| Product | System of record | Serving mirror | Freshness contract |
|---|---|---|---|
| Raw events | Parquet/object archive | Kafka stream | Ingest to archive before publication |
| Curated metrics | Versioned Parquet | ClickHouse | Published only after quality gate; ClickHouse is retryable mirror |
| Online features | PostgreSQL `feature_records` | FastAPI feature endpoint | Latest value per entity, feature, version; event-time ordered |
| Retrieval documents | Object archive | Qdrant | Archive first; index status indicates whether vector indexing is pending |

## Acceptance checks

1. **ClickHouse:** Create a metrics dataset then call `GET /v1/access/analytics` with an API key. The response source must be `clickhouse`.
2. **Qdrant:** Post a document and call `POST /v1/retrieval/query`; results must carry document ID and version metadata.
3. **Features:** Post a feature then query `GET /v1/features/{entity_id}`. Post an older event-time value and confirm it does not replace the newer value.
4. **Unified context:** Call `POST /v1/access/context?entity_id=<id>` with a retrieval query and verify feature and retrieval sources are shown.
5. **Spark:** Run the recompute job over raw Parquet and compare the result against curated metrics over the same interval.
6. **Flink:** Run `docker compose --profile advanced up -d flink-jobmanager flink-taskmanager`, then `docker compose --profile advanced run --rm flink-submit`. Confirm `http://localhost:8081/jobs/overview` reports `RUNNING`; publish a later event-time record to advance the watermark and verify rows in `stream_agent_metrics`.

## Important limitations

- The Qdrant adapter uses deterministic development vectors. Replace it with an approved embedding model before using semantic relevance as a production signal.
- The recorded manual test found that `POST /v1/documents` returned HTTP 500. The new-document archive/index path is not currently an accepted capability; do not use the Qdrant acceptance check as evidence until ingestion is fixed and retested.
- The Flink artifact is a packaged Java job with a pinned Flink 1.20 Kafka connector and ClickHouse JDBC sink. It uses an at-least-once sink; production exactly-once delivery requires an idempotent/upsert sink design and durable checkpoint storage.
- The Spark recompute job writes Parquet; write to ClickHouse only after a reconciliation/quality pass.
- PostgreSQL feature records are a lightweight online serving layer. Introduce Feast only if offline/online feature definitions, point-in-time joins, and materialization workflows become a demonstrated requirement.
