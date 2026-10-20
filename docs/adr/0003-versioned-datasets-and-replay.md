# ADR 0003: Versioned Datasets and Non-Destructive Replay

- **Status:** Accepted for the local project
- **Date:** 2026-10-20

## Context

Historical events may need to be recomputed after a transformation change or
data correction. Replacing the previous output in place would obscure which
logic produced it and make comparisons difficult.

## Decision

Give generated metrics datasets unique dataset IDs and transformation
versions. Replay produces a new dataset and records replay status rather than
silently overwriting prior output. Reconciliation reports differences for
investigation instead of mutating streaming history.

## Consequences

- Previous outputs can be retained for comparison and provenance.
- Consumers of datasets need a clear way to select the desired version.
- Retention and cleanup policies are still needed as history grows.
- Automated replay-idempotency, correction, and mismatch tests remain
  necessary; this design choice alone does not prove those behaviors.
