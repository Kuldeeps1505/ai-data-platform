# Architecture Decision Records

These records capture the current project's most consequential choices. They
describe the local design, not proof that its reliability requirements have
been met.

| ADR | Decision |
|---|---|
| [0001](./0001-parquet-and-postgresql.md) | Keep Parquet as the data-file store and PostgreSQL as metadata/index. |
| [0002](./0002-transactional-outbox.md) | Publish events through a transactional outbox and design consumers for retries. |
| [0003](./0003-versioned-datasets-and-replay.md) | Preserve dataset versions and make replay produce new outputs. |
| [0004](./0004-optional-processing-and-serving.md) | Keep advanced processing and serving systems optional until justified by evidence. |
