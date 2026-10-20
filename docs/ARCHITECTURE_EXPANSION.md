# Architecture and Capability Status

This document describes what is present in the repository and what has evidence
behind it. A component being configured in Docker Compose is not, by itself,
proof that its full workflow is reliable or production-ready.

## Status definitions

- **Implemented; manually exercised:** a dated local test is recorded in
  [MANUAL_TEST_RESULTS.md](./MANUAL_TEST_RESULTS.md); automated integration
  coverage is not implied.
- **Implemented; contract-tested:** covered by the current schema/unit test
  suite, but not necessarily by a live multi-service test.
- **Implemented; needs validation:** code/configuration exists, but the
  documented manual evidence is incomplete, failed, or contradictory.
- **Optional local profile:** not started by the default Compose command.
- **Not deployed:** configuration or code exists, but no cloud deployment is
  evidenced.

## Default local flow

| Capability | Implementation | Evidence and status |
|---|---|---|
| Agent event ingestion | FastAPI -> PostgreSQL metadata, raw Parquet, transactional outbox | Manually exercised on 18 October 2026; automated tests currently cover schemas only. |
| Event transport and streaming metrics | Outbox dispatcher -> Kafka -> consumer -> streaming windows | Components are in the default Compose stack; complete recovery behavior still needs automated integration and failure-exercise evidence. |
| Curated metrics and quality gate | PostgreSQL event metadata -> versioned Parquet metrics and quality report | Manually exercised on 18 October 2026; no end-to-end CI test currently proves the workflow. |
| Replay and reconciliation | FastAPI endpoints and versioned metric output | Implemented; recovery, idempotency, and mismatch cases still need integration tests. |
| Observability | Prometheus, Grafana, OpenTelemetry | Grafana and Prometheus are in the default stack; see the provisioned dashboard and [operations runbook](./PHASE_2_OPERATIONS.md). |
| Evaluations and provenance | Sanitized scenario/result records, audit metadata, run provenance endpoint | Implemented; repeatability and full provenance need automated scenario coverage. |

## Optional source and advanced profiles

| Capability | Compose profile | Evidence and status |
|---|---|---|
| PostgreSQL CDC | `sources` | Debezium connector and one insert event were manually exercised on 18 October 2026. Optional; no source-owner production contract is defined. |
| S3-compatible document archive | `sources` | **Needs validation.** The manual test recorded `POST /v1/documents` returning HTTP 500. Do not claim successful document ingestion or archive-to-index behavior until a regression test passes. |
| ClickHouse analytics | `advanced` | Manually exercised on 18 October 2026; local evidence only. |
| Qdrant retrieval | `advanced` | Retrieval of an existing indexed item was manually exercised. New-document ingestion is blocked by the recorded HTTP 500. Development vectors do not establish semantic retrieval quality. |
| Flink stream job | `advanced` | Job submission and a local output were manually exercised on 18 October 2026. Durable checkpoints and an idempotent sink are not established. |
| Spark recompute job | `advanced` | A local recompute wrote Parquet output on 18 October 2026; automated comparison against curated output is still needed. |

Start optional services deliberately:

```powershell
docker compose --profile sources up -d
docker compose --profile advanced up -d
```

See [ADVANCED_LAYER_RUNBOOK.md](./ADVANCED_LAYER_RUNBOOK.md) for profile
acceptance checks and limitations. The dated evidence and the document-ingestion
failure are listed in [MANUAL_TEST_RESULTS.md](./MANUAL_TEST_RESULTS.md).

## Cloud status

Terraform files provide a partial AWS baseline, not a running deployment. The
repository does not evidence provisioned PostgreSQL, managed Kafka, networking,
an internet/private service rollout, or a cloud acceptance test. Treat cloud
deployment as **not deployed**; see [REMAINING_WORK_GUIDE.md](./REMAINING_WORK_GUIDE.md).
