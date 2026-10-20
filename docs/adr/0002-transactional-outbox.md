# ADR 0002: Transactional Outbox for Event Publication

- **Status:** Accepted for the local project
- **Date:** 2026-10-20

## Context

An API process can persist an event while Kafka is unavailable. Publishing
directly as the only durable write would risk losing accepted events during
that failure window.

## Decision

Persist the event metadata and a pending outbox record in the same PostgreSQL
transaction. A dispatcher publishes pending records to Kafka and marks them
published after broker acknowledgement. Consumer processing is designed to
tolerate duplicate delivery.

## Consequences

- Kafka outages can be retried from persisted pending outbox records.
- A crash after Kafka accepts a record but before the outbox status update can
  cause duplicate publication; consumers must remain idempotent.
- This does not provide end-to-end exactly-once processing. Do not claim that
  guarantee.
- The raw Parquet write is not part of the PostgreSQL transaction; file/DB
  crash windows need separate tests and recovery policy.
