# ADR 0001: Parquet for Data Files, PostgreSQL for Metadata

- **Status:** Accepted for the local project
- **Date:** 2026-10-20

## Context

The platform needs durable raw event records and curated analytical outputs,
alongside transactional event identity, outbox state, dataset metadata, and
workflow status. Keeping all analytical data in application tables would
couple the serving/control plane to bulk dataset storage.

## Decision

Write raw and curated datasets as Parquet files. Use PostgreSQL for event
metadata, identity/idempotency lookups, outbox records, dataset catalog
metadata, and workflow state. Use the object-store adapter for document
archive experiments; that path is not validated end-to-end.

## Consequences

- Columnar files are suitable for batch processing and can be read by the
  Spark job.
- PostgreSQL provides transactional metadata and queryable workflow state.
- Filesystem/object writes and PostgreSQL transactions are separate failure
  domains; orphan files and recovery behavior need tests and operational
  handling.
- The local filesystem/Compose volumes are not a production durability or
  backup strategy.
