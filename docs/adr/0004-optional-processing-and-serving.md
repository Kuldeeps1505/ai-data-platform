# ADR 0004: Keep Advanced Processing and Serving Optional

- **Status:** Accepted for the local project
- **Date:** 2026-10-20

## Context

The repository includes optional CDC, Flink, Spark, ClickHouse, Qdrant, and
feature-serving components. Enabling every technology by default increases
startup cost and obscures the core event-ingestion and correctness story.

## Decision

Keep the core event-to-metrics path as the default Compose experience. Start
source and advanced components through explicit Compose profiles. Add or
promote a component only when a measurable requirement and acceptance test
justify it.

## Consequences

- A clean local demo has a smaller service footprint.
- Optional capabilities must be clearly labeled and tested independently.
- The current `sources` and `advanced` profiles remain local experiments;
  their presence does not imply production support.
- Existing Grafana panels already expose the project's current operational
  signals; a second bespoke dashboard is not a priority until a user need
  exceeds those panels.
