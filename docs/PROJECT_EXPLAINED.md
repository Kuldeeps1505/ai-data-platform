# AI Data Platform — Simple Project Explanation

## 1. What this project is

This project is a local **data-platform prototype for AI applications**. The
architecture below explains the intended system; it is not a claim that every
path has been validated. See [current capability status](ARCHITECTURE_EXPANSION.md),
[known limitations](KNOWN_LIMITATIONS.md), and the dated
[manual test results](MANUAL_TEST_RESULTS.md) before describing a feature as
working.

An AI application produces useful records: which tool it used, how long it
took, and whether it succeeded. This project has an event-ingestion path and
additional local components for analytics, retrieval, features, and evaluation.
The event path has dated manual evidence; several additional paths are optional
or need more validation.

In simple terms, it turns scattered AI application activity into reliable, reusable data.

## 2. The problem it solves

Without a data platform, information is usually split across application logs, databases, files, dashboards, and manual spreadsheets. It becomes difficult to answer questions such as:

- Which AI agent fails most often?
- Which tools make responses slow?
- Can we reproduce an old AI run?
- What data was used to generate an answer?
- Did a database change reach downstream consumers?
- Can an AI application retrieve the latest trusted context?

This project provides one controlled route from source data to useful AI data products.

## 3. The big picture

```text
AI events / database changes / documents
                |
                v
       Validation and ingestion APIs
                |
                v
       Kafka event stream + raw archive
                |
        +-------+--------+
        |                |
        v                v
   Flink streaming    Spark batch recompute
        |                |
        +-------+--------+
                |
                v
       Quality checks and reconciliation
                |
                v
  ClickHouse / features / retrieval index
                |
                v
          Unified AI data APIs
                |
                v
   Dashboards, AI apps, evaluation workflows
```

## 4. The data journey, step by step

### Step 1: Data enters the platform

The intended architecture supports three types of source data, with different
implementation status:

| Source | Example | How this project receives it |
|---|---|---|
| AI agent events | An agent called `document_search` and took 150 ms | FastAPI `POST /v1/events`; manually exercised |
| Database changes | A customer was upgraded to the `gold` tier | Optional `sources` profile; one local CDC insert was manually exercised |
| Documents | A policy, support guide, or product document | `POST /v1/documents`; a manual test returned HTTP 500, so ingestion is not validated |

The API validates incoming fields before accepting them. For example, an agent event must have an event ID, agent ID, run ID, timestamp, event type, latency, and success value. This is called a **data contract**.

### Step 2: Keep the original data

The event path writes raw records as Parquet files. Parquet is a compact
column-based file format that is efficient for analytics.

The document route is intended to store documents in an S3-compatible object
store. Locally, this uses LocalStack, but the recorded HTTP 500 means that
archive path must not be treated as validated.

Keeping raw data is important because it lets us replay, audit, or recompute later instead of losing the original evidence.

### Step 3: Send changes through Kafka

Kafka is the platform’s event pipeline. Think of it as a durable conveyor belt:

```text
New event -> Kafka topic -> consumer / Flink job -> downstream data product
```

Kafka helps different services work independently. The API can accept an event even if a downstream analytic process is temporarily slow.

### Step 4: Process the data in two ways

The platform has two processing styles because they solve different problems.

| Tool | Type of processing | Main purpose |
|---|---|---|
| Default consumer | Streaming windows | Updates local streaming metrics from Kafka; recovery/latency guarantees need more tests |
| Flink (optional) | Event-time stream processing | Advanced local job; not part of the default flow |
| Spark (optional) | Batch / historical | Advanced local recompute from Parquet; automated comparison is still needed |

Example: Flink can show an agent’s recent failure rate soon after events arrive. Spark can recompute last month’s metrics after a bug fix or a changed business rule.

### Step 5: Check data quality

Before metrics are considered trusted, the platform checks items such as:

- Required fields are present.
- Event IDs are unique.
- Input event counts and output metric counts make sense.
- Generated datasets have a version and a timestamp.

This avoids publishing analytics that are silently incomplete or malformed.

### Step 6: Create data products

The same source data is delivered in forms appropriate for different users and applications.

| Data product | Tool | What it is for |
|---|---|---|
| Curated metrics | Parquet | Trusted historical datasets |
| Analytics tables | ClickHouse | Fast dashboard and SQL-style metric queries |
| Online features | PostgreSQL | Fast per-agent or per-customer values for applications |
| Retrieval index | Qdrant | Find relevant documents for AI context |

## 5. What each major tool does

### FastAPI

FastAPI is the front door of the platform. It exposes HTTP endpoints so applications, testers, and dashboards can send or request data.

Examples:

- `POST /v1/events` — send an AI event.
- `POST /v1/documents` — archive and index a document.
- `GET /v1/access/analytics` — read analytics from ClickHouse.
- `POST /v1/access/context` — get features and retrieval context together.

### PostgreSQL

PostgreSQL stores platform metadata, run information, feature values, audit records, and transactional state. It is the reliable database for operational data.

### Kafka

Kafka transports events between services. It is especially useful when many producers and consumers need to use the same stream of changes.

### Debezium

Debezium watches a PostgreSQL database and turns inserts, updates, and deletes into Kafka events. This is called **Change Data Capture (CDC)**.

It means another system can react to database changes without repeatedly polling the database.

### LocalStack / S3-style object storage

Object storage holds files instead of database rows. Here it stores archived documents and can be replaced with AWS S3 in production.

### Parquet

Parquet is the file format used for analytics data. It is efficient when reading selected columns from large datasets.

### Flink

Flink is an optional advanced stream processor. The packaged local job reads
Kafka events, uses event time and watermarks, groups events into hourly
windows, and writes metrics to ClickHouse; local manual execution is recorded,
but durable checkpoints and production delivery guarantees are not established.

### Spark

Spark is the batch processor. It reads raw Parquet files and recomputes hourly metrics. It is useful when data must be recalculated from history.

### ClickHouse

ClickHouse is the analytics database. It is optimized for fast aggregation queries such as failure rate, latency, retry count, and total runs.

### Qdrant

Qdrant is the vector database. It stores document vectors so an AI application can retrieve potentially relevant documents using a text query.

The current vectors are deterministic development vectors. They prove the workflow; a production deployment should use an approved embedding model.

### Grafana, Prometheus, and OpenTelemetry

These tools help operate the platform.

- Prometheus collects numeric metrics.
- Grafana displays metrics and dashboards.
- OpenTelemetry records traces so requests can be followed through services.

## 6. Example use case: an AI support assistant

Imagine an AI support assistant helping customers.

1. A customer asks a question.
2. The assistant searches internal support documents.
3. The assistant emits an event showing which tool ran, latency, and success/failure.
4. The event is validated, stored in Parquet, and sent through Kafka.
5. Flink updates recent operational metrics.
6. ClickHouse makes the metrics available to a dashboard.
7. The support document is archived and indexed in Qdrant.
8. Future questions can retrieve relevant support context.
9. An evaluator can later compare answers and record whether the assistant was correct.

This is why the project is called an **AI data platform**: it supports both the operations of an AI application and the data needed to improve it.

## 7. Why both a dashboard and APIs are useful

Grafana is best for operations: service health, failures, lag, latency, and alerts.

The platform APIs are best for application data: feature values, document search, analytics rows, provenance, and evaluation records.

So Grafana does not replace platform APIs, and APIs do not replace Grafana. They serve different users.

## 8. Local URLs

| Service | Address | Purpose |
|---|---|---|
| API documentation | `http://localhost:8000/docs` | Try platform endpoints in a browser |
| Grafana | `http://localhost:3000` | Operational dashboards; local login is `admin` / `admin` |
| Prometheus | `http://localhost:9090` | Raw metrics and alert inspection |
| Flink | `http://localhost:8081` | Streaming job status |
| Spark | `http://localhost:8080` | Batch cluster and submitted application status |

## 9. What is complete locally, and what changes for production

The default Compose stack contains the core services, and the 18 October 2026
manual record exercises several core and optional paths. It does **not** prove
the complete architecture: document ingestion failed, tests do not yet cover
the multi-service workflow, and optional services are not production
deployments. Use [the capability status](ARCHITECTURE_EXPANSION.md) for the
evidence-backed breakdown.

Before production use, these items need production-grade configuration:

- Replace LocalStack with cloud object storage such as AWS S3.
- Store secrets in a secret manager instead of Compose environment values.
- Configure durable Flink checkpoints and a stronger idempotent/exactly-once sink design.
- Use a real embedding model for document vectors.
- Add access roles, network restrictions, backups, cost controls, and production alerting.
- Run Spark reconciliation on a schedule before publishing recomputed outputs.

## 10. A helpful way to remember the project

```text
Collect -> Store -> Stream -> Process -> Check -> Serve -> Observe -> Improve
```

That is the core concept of this project.

- **Collect:** APIs and CDC receive data.
- **Store:** PostgreSQL, Parquet, and object storage preserve it.
- **Stream:** Kafka distributes changes.
- **Process:** Flink and Spark create useful metrics.
- **Check:** quality gates and reconciliation build trust.
- **Serve:** ClickHouse, feature APIs, and Qdrant support users and AI applications.
- **Observe:** Grafana, Prometheus, logs, and traces show system health.
- **Improve:** evaluation data and replayability support better AI behavior.

---

## 11. Detailed architecture by layer

The project is easier to understand when viewed as layers. Each layer has one responsibility and passes trusted data to the next layer.

```text
Source layer       : Where data starts
Ingestion layer    : Where data is checked and accepted
Transport layer    : Where changes are distributed
Storage layer      : Where original and curated data is preserved
Processing layer   : Where events become metrics and datasets
Serving layer      : Where data becomes useful to applications
Access layer       : Where applications use one consistent API
Operations layer   : Where health, failures, and cost can be observed
Governance layer   : Security, contracts, lineage, freshness, recovery
```

### 11.1 Source layer

Sources are systems that create information. This project has three kinds.

#### Agent-event source

An AI application sends one event per important activity. Examples include:

- `agent.run_started`
- `agent.tool_completed`
- `agent.tool_retry`
- `agent.run_failed`

An event is not the full conversation. It is a structured operational record about what happened during a run.

```json
{
  "event_id": "evt-1001",
  "event_type": "agent.tool_completed",
  "event_time": "2026-10-18T11:15:00Z",
  "run_id": "run-501",
  "agent_id": "support-agent",
  "tool_name": "document_search",
  "latency_ms": 150,
  "success": true
}
```

Why this matters: once every application uses the same event structure, the platform can calculate common metrics for every agent.

#### Database-change source

Some important business data already lives in a database. For example, customer tier, account status, product inventory, or user preferences.

Instead of making every consumer repeatedly query the source database, Debezium reads database changes from PostgreSQL replication logs and publishes them to Kafka. This gives downstream systems a change record such as:

```text
customer_context changed
customer_id: customer-001
tier: standard -> gold
account_status: active
operation: update
```

This pattern is called CDC, or Change Data Capture.

#### Document source

Documents can come from manuals, policies, knowledge-base articles, product documentation, or support content. The project treats documents as versioned data assets, not just files uploaded somewhere.

For every accepted document, the platform records:

- Document ID and title
- Source location
- Content hash
- Version
- Object-storage location
- Vector-index status

This makes it possible to answer: “Which exact version of this document was retrieved for an AI answer?”

### 11.2 Ingestion layer

The ingestion layer is the safety gate. It prevents invalid or incomplete data from becoming part of the platform.

The FastAPI service checks:

| Check | Why it matters |
|---|---|
| Required fields | A metric cannot be correctly calculated if `agent_id` or `event_time` is missing. |
| Field types | `latency_ms` must be a number, not text. |
| Timestamp timezone | Time windows become wrong if time zones are unclear. |
| Event ID behavior | Duplicate requests do not create duplicate business events. |
| API key | Unauthenticated callers cannot send or read platform data. |

The API does not directly depend on Kafka success for acceptance. It records an outbox entry in PostgreSQL first. A dispatcher publishes pending outbox records to Kafka. This is the **transactional outbox pattern**.

Why it matters: if Kafka is temporarily unavailable, the accepted event is not lost.

### 11.3 Transport layer

Kafka moves event data between producers and consumers.

```text
FastAPI -> PostgreSQL outbox -> dispatcher -> Kafka topic -> consumers
                                          |
                                          +-> Flink job
```

Important Kafka ideas:

| Term | Meaning in this project |
|---|---|
| Topic | A named stream of events, for example `agent-events.v1`. |
| Producer | A service that writes events to a topic. |
| Consumer | A service that reads events from a topic. |
| Consumer group | A named reader identity that tracks its own progress. |
| Offset | A consumer’s position in a topic. |
| Dead-letter queue | A holding place for events that cannot be processed safely. |

Kafka is not the final system of record. It is the reliable transport mechanism between systems.

### 11.4 Storage layer

The project stores different kinds of data in the location that suits its use.

| Storage | Stores | Why it is used |
|---|---|---|
| PostgreSQL | Metadata, outbox, features, evaluations, audit records | Transactional updates and operational lookup |
| Parquet | Raw agent events and curated metric datasets | Efficient historical analytics and recomputation |
| S3-compatible object storage | Versioned document objects | Durable file/object storage |
| Kafka | Events waiting to be processed | Decoupled, durable event transport |
| ClickHouse | Fast analytical metrics | Fast aggregate queries |
| Qdrant | Document vectors and metadata | Similarity search for retrieval |

This separation is intentional. A single database is rarely ideal for transactions, huge analytical scans, file archives, event streams, and vector search at the same time.

### 11.5 Processing layer

The processing layer converts low-level facts into data that humans and applications can use.

#### The Python consumer

The existing consumer reads agent events from Kafka and maintains recent streaming metrics. It is the simpler baseline processor and is useful for dependable local operation.

#### The Flink job

Flink processes the Kafka stream continuously. Its job is:

1. Read events from `agent-events.v1`.
2. Use `event_time`, not arrival time, as the business time.
3. Allow a short amount of out-of-order arrival using a watermark.
4. Group events by agent and hourly time window.
5. Calculate runs, failures, average latency, and retries.
6. Write the result into ClickHouse.

The simple idea of event time is important:

```text
Event occurred at 11:05
Event reaches Kafka at 11:07

Correct business window: 11:00 to 12:00
```

If the platform used only processing time, a delayed event could be placed in the wrong hour. Watermarks let the system wait briefly for late events before finalizing a window.

#### The Spark job

Spark performs historical recomputation. It reads raw Parquet events and creates the same type of hourly agent metrics.

Use Spark when:

- A transformation rule changes.
- A bug is fixed.
- Historical raw data must be recalculated.
- A quality issue requires a trusted rebuild.

Spark output is written separately from the currently published curated metrics. This protects production analytics from accidental replacement.

### 11.6 Quality and reconciliation layer

The platform distinguishes between “data exists” and “data is trusted.”

A dataset becomes publishable only after quality checks pass. Typical checks include:

```text
raw input has required fields
          +
event IDs are unique
          +
metric rows were created
          +
dataset has a generation timestamp and version
          =
quality-passed dataset
```

Reconciliation compares two paths that should agree. For example:

```text
Number of accepted agent events in PostgreSQL
                   versus
Number of events represented in the curated dataset
```

If these numbers differ unexpectedly, the platform should alert an operator before analytics are trusted.

### 11.7 Serving layer

The serving layer makes processed data fast to use.

#### ClickHouse analytics

ClickHouse answers questions such as:

- What was the failure rate by agent in the last hour?
- Which tool has the highest average latency?
- How many retries occurred today?

The API endpoint `GET /v1/access/analytics` reads this analytics view.

Curated Parquet remains the durable data product. ClickHouse is a fast serving mirror that can be rebuilt if necessary.

#### Feature serving

A feature is a value useful for an application decision. Examples:

```text
agent success rate = 0.95
customer tier = gold
recent failure count = 3
```

Features are stored with entity, name, version, and event time. The event-time rule prevents an older event from accidentally overwriting a newer value.

The feature endpoints are:

```text
POST /v1/features
GET  /v1/features/{entity_id}
```

#### Retrieval serving

Documents are indexed in Qdrant so an application can request potentially related context.

```text
User asks: “How are streaming metrics calculated?”
                 |
                 v
Qdrant searches document vectors
                 |
                 v
API returns document text and version metadata
```

The endpoint is `POST /v1/retrieval/query`.

### 11.8 AI data-access layer

An AI application should not need to know which database contains every type of data. The access layer provides a simpler interface.

For example, this endpoint combines multiple stores:

```text
POST /v1/access/context?entity_id=manual-agent
```

It returns:

- Feature values from PostgreSQL.
- Retrieval results from Qdrant.
- Source and freshness information.

This makes it easier to build AI applications while keeping the storage architecture flexible behind the API.

## 12. End-to-end example in detail

Consider a support agent answering: “Why did my subscription change?”

### 12.1 The application needs context

The application asks the platform for customer features and related documents.

```text
AI application
   |
   +-> feature API: customer tier, account status
   |
   +-> retrieval API: subscription policy documents
   |
   v
Generates an answer using approved context
```

### 12.2 The application produces observability events

During the answer, the application may create these events:

```text
agent.run_started
agent.tool_completed: customer lookup
agent.tool_completed: document retrieval
agent.run_completed
```

Each event includes the same `run_id`, making it possible to reconstruct the run later.

### 12.3 The platform processes the events

```text
FastAPI validates event
  -> PostgreSQL stores metadata/outbox
  -> Parquet preserves raw event
  -> Kafka distributes it
  -> consumer and Flink process it
  -> ClickHouse serves operational analytics
```

### 12.4 An operator investigates an issue

If users complain that the agent is slow, the operator can:

1. Open Grafana to see latency trends.
2. Query ClickHouse analytics to find the slowest agent or tool.
3. Use the run/provenance endpoints to inspect the related source events.
4. Replay or recompute data if a transformation needs to change.

## 13. Data versions, lineage, and provenance

These words are closely related but not identical.

| Concept | Simple meaning | Example in this project |
|---|---|---|
| Version | Which revision of something was used | Transformation version `v1`; document version `2` |
| Lineage | The chain from source to output | Raw event -> curated metrics -> ClickHouse mirror |
| Provenance | Evidence of where a particular result came from | A run’s event IDs, raw paths, timestamps, and datasets |
| Freshness | How recent data is | When a dataset or feature was generated or updated |

These concepts matter because AI systems need explainability. If a result looks wrong, the team should be able to trace it back to its source rather than guessing.

## 14. Reliability patterns used in the project

### Idempotency

Idempotency means it is safe to repeat an operation without creating an incorrect duplicate result.

Example: if the client sends the same `event_id` twice because of a network retry, the platform recognizes it as a duplicate instead of counting it twice.

### Transactional outbox

The event is recorded in PostgreSQL before Kafka publishing is attempted. A dispatcher keeps retrying pending records.

This avoids a dangerous failure case:

```text
Bad case: database saved event, Kafka publish failed, event is lost downstream

Outbox case: database saved event and pending outbox record,
             dispatcher retries Kafka safely
```

### Dead-letter queue

Events that repeatedly fail processing can be isolated instead of blocking the entire stream. Operators can inspect and correct them later.

### Replay and recompute

Raw storage means the platform can recreate derived data. This is important because data logic changes over time.

## 15. Security and privacy concepts

The local environment uses a simple API key to make the workflow easy to test. Production security is stronger.

| Area | Local approach | Production direction |
|---|---|---|
| API access | Shared API key | Identity provider, roles, service accounts |
| Secrets | Compose environment values | AWS Secrets Manager or another secret manager |
| Data encryption | Local Docker storage | Encryption in transit and at rest |
| Network | Local Docker network | Private subnets, security groups, restricted endpoints |
| Sensitive values | Sanitization support | Formal data classification, retention, and access policies |

Never put real production credentials into source files, Markdown documents, Docker Compose files, or Git history.

## 16. Observability: how the platform tells us it is healthy

Observability is the ability to understand a running system from the outside.

This project uses four main signals:

| Signal | Question it answers | Tool |
|---|---|---|
| Metrics | How many, how long, how often? | Prometheus and Grafana |
| Logs | What happened in a service? | Structured application logs / Docker logs |
| Traces | Which services handled one request? | OpenTelemetry |
| Data-quality signals | Is the data trustworthy? | Dataset quality reports and reconciliation |

Examples of useful alerts:

- API rejection rate is high.
- Kafka consumer lag keeps increasing.
- No new dataset was generated within the expected period.
- Flink job is not running.
- CDC connector task is failed.
- Reconciliation counts differ.

## 17. How to think about the project’s maturity

The project has two levels.

### Current local prototype

Docker Compose starts the default local stack. The current automated tests are
contract/schema tests; end-to-end recovery and data-correctness claims require
more test evidence. Optional profiles are not all started by the default
Compose command. See [the synthetic demo](DEMO.md) and record actual outcomes
when you run it; the walkthrough itself is not proof that an unrun path works.

### Production platform level

A production environment needs the same logical components, but stronger operational controls:

```text
Local Compose                     Production
-------------                    ------------------------------
LocalStack                        AWS S3 or equivalent
Docker environment variables      Managed secret store
Local volumes                     Backed-up durable storage
One local Kafka broker            Managed or multi-broker Kafka
Local Flink checkpoint state      Object-store-backed checkpoints
Development vectors               Approved embedding service/model
Manual commands                   CI/CD and scheduled orchestration
```

The local project is therefore not a toy; it is an implementation foundation. Production work makes each component secure, scalable, and recoverable.

## 18. Suggested learning order

If you are new to this type of system, learn it in this order:

1. Send an agent event through the FastAPI docs page.
2. View its streaming metrics response.
3. Create a curated dataset and view ClickHouse analytics.
4. Insert a CDC record and watch it arrive in Kafka.
5. Store a feature and request unified context.
6. Open Flink and Spark UIs to understand streaming versus batch.
7. Read the manual test results and runbook.

Helpful project documents:

- [Manual test results](MANUAL_TEST_RESULTS.md)
- [Advanced processing and serving runbook](ADVANCED_LAYER_RUNBOOK.md)
- [Architecture expansion status](ARCHITECTURE_EXPANSION.md)
- [Remaining environment work guide](REMAINING_WORK_GUIDE.md)
