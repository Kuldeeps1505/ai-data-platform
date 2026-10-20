# Turn the AI Data Platform into a Resume-Ready Project

This guide is the single prioritized improvement plan for presenting this repository as a flagship resume project. The goal is not to add the most tools. It is to make one end-to-end data platform reliable, explainable, reproducible, measurable, and easy to demonstrate.

## The project story to aim for

> An event data platform for AI-agent operations that validates and stores execution events, reliably streams them for near-real-time metrics, rebuilds historical datasets, checks streaming results against batch results, and turns sanitized failures into traceable regression evaluations.

This is a stronger story than “a platform using FastAPI, Kafka, Flink, Spark, ClickHouse, Qdrant, and AWS.” Tools are supporting details; reliability, correctness, and measured outcomes are the proof.

## Where the project stands

The repository already has useful foundations: a versioned event contract, FastAPI ingestion, PostgreSQL metadata, Parquet datasets, Kafka with an outbox/dispatcher, a streaming consumer, replay and reconciliation APIs, evaluation/provenance features, CI, and optional source and advanced Compose profiles. The existing architecture and operational notes are in [ARCHITECTURE_EXPANSION.md](./ARCHITECTURE_EXPANSION.md), [PHASE_2_OPERATIONS.md](./PHASE_2_OPERATIONS.md), and [ADVANCED_LAYER_RUNBOOK.md](./ADVANCED_LAYER_RUNBOOK.md).

The 18 October 2026 manual test record says the document-ingestion endpoint returned HTTP 500. The architecture status now reflects that failure instead of claiming successful ingestion. The CI workflow runs `pytest -q`, while the test directory currently contains only schema tests, so the core multi-service workflow and its failure cases still need automated coverage before they can be presented as verified.

## Prioritized roadmap

Do these in order. Each phase has a stop condition: do not move on just because another technology would be interesting.

### 1. Make the core story accurate and repeatable

**Why it matters:** A recruiter or interviewer should be able to clone the repository, run one command, follow one demo, and see the same result. A known failure is better disclosed than accidentally presented as a success.

**Work**

- Reproduce the document-ingestion HTTP 500 using the exact endpoint, request, and profile from the manual test. Fix it and add an integration test, or clearly mark document ingestion/retrieval as experimental and remove any conflicting “verified” claims.
- Choose one supported default demonstration path: event submission -> validation/idempotency -> raw archive and metadata -> outbox -> Kafka -> consumer metrics -> batch dataset -> quality check -> reconciliation -> evaluation/provenance.
- Add an automated integration test for that path. Assert meaningful outputs and persisted state, not only HTTP status codes.
- Add focused failure-path tests for invalid schema, exact duplicate, conflicting duplicate, database/Kafka interruption, retry/DLQ behavior, failed quality gate, replay idempotency, and reconciliation mismatch.
- Make CI run the relevant tests with the required services or a documented integration-test profile. Keep fast unit/contract tests separate from slower service integration tests.
- Review the README and architecture docs against what the tests actually prove. Label capabilities as **implemented and tested**, **implemented but not integration-tested**, **optional local profile**, or **planned**.

**Done when**

- A clean checkout can run the documented tests and core demo.
- The demo's assertions pass in CI or in a reproducible CI integration job.
- Every shown feature's status agrees with automated or dated manual evidence.

### 2. Prove reliability, correctness, and recovery

**Why it matters:** This is the project's strongest data-engineering signal. “Kafka is included” is less impressive than showing duplicate delivery, process restarts, recovery, and reconciliation do not silently corrupt results.

**Work**

- Document and test the event's lifecycle and idempotency key at every boundary: API, durable raw storage, outbox, Kafka consumer, dataset publication, and replay.
- Test crash windows around the PostgreSQL/outbox/Kafka boundary. State clearly what is at-least-once, what is idempotent, and what is not exactly-once.
- Add deterministic fixtures for late events, duplicate delivery, malformed records, and corrected records. Verify event-time windowing and historical recomputation behavior.
- Define a small set of explicit service objectives for the demo, such as ingestion success under a stated load, maximum processing lag, and recovery time. Treat these as targets until measurements verify them.
- Run and record a failure exercise: stop the consumer, continue ingesting, restart it, check lag recovery, then reconcile the affected period.

**Done when**

- The failure exercise is repeatable and its result is captured in a test or benchmark record.
- Streaming-versus-batch differences are explained, detected, and visible; reconciliation does not silently rewrite history.
- Delivery guarantees and known limitations are stated accurately.

### 3. Add useful tests and measurable performance evidence

**Why it matters:** A benchmark without workload details or correctness checks is not evidence. Report measured results, never invented or unrepeatable performance claims.

**Work**

- Extend the benchmark beyond the existing small client-side run. Record event count, payload size, concurrency, hardware/runtime, command, duration, errors, throughput, and p50/p95/p99 latency.
- Measure consumer lag and time to drain a known backlog. Include warm-up and repeat runs where practical.
- Check correctness after each benchmark: accepted/rejected counts, unique event IDs, expected metrics, and reconciliation result.
- Add a lightweight CI smoke benchmark only if it is stable; keep machine-dependent performance thresholds out of CI until variance is understood.
- Save a concise, dated results table with the exact commit/configuration. Separate local measurements from any cloud measurements.

**Done when**

- Another person can rerun the benchmark and understand what each number means.
- Every resume metric is traceable to a command, workload, environment, and result.

### 4. Make one AI-specific capability genuinely useful

**Why it matters:** The agent-event use case is distinctive. Avoid diluting it with a generic catalog of databases and AI buzzwords.

**Work**

- Make the existing evaluation loop the primary AI-specific differentiator: eligible failed run -> sanitization -> versioned scenario -> repeatable evaluation -> provenance back to source event/dataset.
- Create a small synthetic scenario set with fixed expected outcomes and test that rerunning the same evaluation version is reproducible.
- Define evaluation metrics that fit the scenario (for example pass rate or task-specific assertions); do not imply that a score alone proves model quality.
- If document retrieval remains in scope, first fix and test ingestion/versioning. The current runbook identifies deterministic development vectors, so do not claim semantic retrieval quality until a real embedding model and a small relevance evaluation set are used.
- Keep prompt/tool payloads out of the default telemetry path unless there is a documented, consented, and appropriately protected need.

**Done when**

- A demo can trace an evaluation result to versioned input evidence without exposing raw sensitive payloads.
- Repeated runs produce explainable, versioned results.

### 5. Harden the operational and security story

**Why it matters:** A local development stack is not a production deployment. Being precise about the gap demonstrates good engineering judgment.

**Work**

- Make development credentials unmistakably local-only; fail safely or emit a clear startup warning when insecure defaults are used outside local development.
- Add a secret scan and dependency/container vulnerability checks to CI. Pin or review dependency versions and keep upgrade evidence.
- Add bounded request sizes, authentication/authorization tests, structured error logging, and retention/deletion behavior tests for the data actually stored.
- Review logs, metrics, traces, and dashboards for useful correlation IDs and actionable failure signals; avoid recording secrets or event payloads.
- Validate Terraform formatting and configuration in CI. Keep the deployment described as a baseline until the missing cloud dependencies and network/service rollout are provisioned and tested.
- If pursuing a live deployment, choose one small, affordable target and deploy only the core flow first. Record cost assumptions and teardown steps. Do not expose the local Compose setup as production-ready.

**Done when**

- The threat/limitations section identifies what is and is not protected.
- CI has at least basic security checks and infrastructure validation.
- Any cloud claim is backed by a deployed, tested environment rather than Terraform files alone.

### 6. Package the project for a reviewer

**Why it matters:** The project should be understandable before someone reads the implementation.

**Work**

- Make the README the short landing page: problem, architecture image, five-minute quickstart, one demo, test command, benchmark evidence, limitations, and links to deeper docs.
- Keep the draw.io diagram aligned with the executable default stack. Visually distinguish default services, optional Compose profiles, and planned/cloud-only infrastructure.
- Add a concise demo script with sample requests and expected results, including one failure/recovery scenario. Use synthetic data only.
- Add a small set of architecture decision records for the most consequential trade-offs, such as Parquet plus PostgreSQL metadata, the outbox, replay/versioning, and why optional processing systems are or are not needed.
- Add a “Known limitations” section that names the current guarantees and the next steps, rather than describing future work as delivered.
- Remove stale or contradictory claims and avoid adding another framework unless a measured requirement justifies it.

**Done when**

- A reviewer can understand the problem, start the system, run the test/demo, inspect evidence, and identify limitations without asking for missing context.

## Suggested sequence

Work in thin vertical slices; the durations below are planning estimates, not promises.

| Order | Slice | Evidence to produce |
|---|---|---|
| 1 | Reconcile the known document-ingestion failure and correct capability claims | Passing regression test or explicit experimental status |
| 2 | Automate the core event-to-metric workflow | CI integration-test result |
| 3 | Test duplicate, retry, restart, replay, and reconciliation behavior | Failure-exercise output and test coverage |
| 4 | Benchmark a stated workload and verify output correctness | Reproducible results table |
| 5 | Demonstrate the evaluation/provenance loop with synthetic data | Scripted demo and repeatable evaluation |
| 6 | Add security/infrastructure checks and decide whether to deploy | CI checks; deployment evidence only if actually deployed |
| 7 | Tighten the README and diagram for reviewer experience | Five-minute clean-checkout walkthrough |

If time is limited, complete slices 1–4 and 7 before expanding the optional Flink/Spark/Qdrant/cloud surface. A well-tested, measured core is a stronger flagship project than a larger unverified architecture.

## Resume positioning

Use a role title and project story that match the jobs being targeted. For data-engineering roles, emphasize ingestion, streaming, correctness, and recovery. For AI platform roles, emphasize agent telemetry, evaluation, and provenance. Do not list every optional service as a core production capability.

Draft bullet templates—replace every bracketed item with measured, verified evidence:

- Built an AI-agent telemetry platform with **[FastAPI/PostgreSQL/Kafka/Parquet]**, validating versioned events and using a transactional outbox plus idempotent consumers to **[measured delivery/recovery result]**.
- Implemented quality-gated, versioned metrics and replay/reconciliation workflows; verified **[batch-versus-streaming result]** over **[workload/window]**.
- Created a traceable evaluation workflow that converts sanitized **[N]** synthetic failure cases into versioned regression scenarios and records **[measured repeatability/result]**.
- Benchmarked **[N]** events at **[concurrency/payload]**, measuring **[throughput]**, **[p95 latency]**, and **[consumer lag/recovery]** on **[environment]**.

Do not claim “exactly once,” “production-ready,” “real-time” without a defined latency measure, or cloud deployment unless the corresponding guarantee or deployment has been implemented and verified.

## Interview-ready checklist

Before calling this the flagship project, be ready to answer:

- What user/problem does the platform solve, and why are agent execution events useful?
- What happens if the API process or Kafka broker fails between persistence and publication?
- How are duplicate and late events handled? What does “idempotent” mean in this implementation?
- How do replay and dataset versioning prevent silent overwrites?
- What does reconciliation compare, and how are differences investigated?
- Which components are required for the core demo, and which are optional or experimental?
- What did the benchmark actually measure, and what are its limitations?
- What is deliberately not production-ready, and what would you change first for production?

If you can demonstrate the answers with tests, logs, metrics, and a reproducible run—not just explain them—the project will read as a credible engineering portfolio piece.
