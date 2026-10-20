from contextlib import asynccontextmanager
from datetime import datetime
import logging
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy import select
from .config import settings
from .database import DatasetRecord, EventRecord, ReplayRecord, SessionLocal, initialise_database
from .logging_config import configure_logging
from .schemas import AgentExecutionEvent, ReplayRequest
from .services import ConflictingEventError, build_metrics, create_replay, ingest_event, publish_pending_events, run_replay
from .observability import EVENTS_REJECTED, INGEST_LATENCY, configure_tracing, mount_metrics
from .reconciliation import reconcile
from .streaming import streaming_metrics
from .security import require_api_key
from .evaluations import create_scenario, record_evaluation
from .schemas import DocumentIngestRequest, EvaluationRunRequest, EvaluationScenarioRequest, FeatureUpsertRequest, RetrievalQuery
from .documents import ingest_document
from .object_store import ensure_bucket
from .serving import clickhouse_metrics, get_features, retrieve, upsert_feature

configure_logging(settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialise_database()
    if settings.object_store_endpoint:
        try:
            ensure_bucket()
        except Exception:
            logger.exception("object_store_unavailable_at_startup")
    yield


app = FastAPI(title="AI Data Platform", version="0.1.0", lifespan=lifespan)
configure_tracing(app)
mount_metrics(app)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError):
    EVENTS_REJECTED.labels(reason="contract_validation").inc()
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.middleware("http")
async def request_context(request: Request, call_next):
    try:
        require_api_key(request)
    except HTTPException as exc:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    request_id = request.headers.get("X-Request-ID", __import__("uuid").uuid4().hex)
    response: Response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.get("/dashboard", response_class=HTMLResponse)
def platform_dashboard() -> str:
    """Small platform-facing navigation surface; Grafana remains the operational dashboard."""
    return """<!doctype html><html><head><title>AI Data Platform</title><style>body{font-family:system-ui;max-width:900px;margin:48px auto;background:#101827;color:#e5e7eb}a{color:#60a5fa}.card{background:#172033;padding:22px;margin:16px 0;border-radius:10px}</style></head><body><h1>AI Data Platform</h1><p>Product-facing controls and data lineage. Use Grafana for live infrastructure metrics.</p><div class='card'><h2>Operations</h2><a href='http://localhost:3000'>Open Grafana operational dashboard</a><p>Monitor ingestion, lag, freshness, quality, and alerts.</p></div><div class='card'><h2>AI evaluation workflow</h2><p>Create versioned scenarios with <code>POST /v1/evaluations/scenarios</code>; record repeatable outcomes with <code>POST /v1/evaluations/runs</code>.</p></div><div class='card'><h2>Provenance</h2><p>Trace an agent run via <code>GET /v1/provenance/runs/{run_id}</code>.</p></div></body></html>"""


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/ready")
def ready() -> dict:
    try:
        with SessionLocal() as session:
            session.execute(select(1))
    except Exception as exc:
        raise HTTPException(status_code=503, detail="database unavailable") from exc
    return {"status": "ready"}


@app.post("/v1/events", status_code=201)
def post_event(event: AgentExecutionEvent, response: Response) -> dict:
    with INGEST_LATENCY.time():
        try:
            duplicate, record = ingest_event(event)
        except ConflictingEventError as exc:
            EVENTS_REJECTED.labels(reason="conflicting_duplicate").inc()
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        # The transactional outbox makes Kafka outages retryable without losing the accepted event.
        publish_pending_events()
    if duplicate:
        response.status_code = 200
    return {"event_id": record.event_id, "status": "duplicate" if duplicate else "accepted", "ingestion_time": record.ingestion_time}


@app.get("/v1/streaming/metrics")
def get_streaming_metrics(start_time: datetime, end_time: datetime) -> dict:
    if end_time <= start_time:
        raise HTTPException(status_code=422, detail="end_time must be after start_time")
    return {"start_time": start_time, "end_time": end_time, "metrics": streaming_metrics(start_time, end_time)}


@app.post("/v1/reconciliation")
def run_reconciliation(start_time: datetime, end_time: datetime) -> dict:
    if end_time <= start_time:
        raise HTTPException(status_code=422, detail="end_time must be after start_time")
    return reconcile(start_time, end_time)


@app.post("/v1/datasets/agent-metrics", status_code=201)
def refresh_metrics() -> dict:
    dataset = build_metrics()
    if dataset.quality_status != "passed":
        raise HTTPException(status_code=409, detail={"dataset_id": dataset.dataset_id, "quality_status": dataset.quality_status})
    return dataset_view(dataset)


@app.get("/v1/metrics/agents")
def agent_metrics(dataset_id: str | None = None) -> dict:
    with SessionLocal() as session:
        query = select(DatasetRecord).where(DatasetRecord.dataset_type == "agent_operational_metrics")
        if dataset_id:
            query = query.where(DatasetRecord.dataset_id == dataset_id)
        dataset = session.scalars(query.order_by(DatasetRecord.generated_at.desc())).first()
        if not dataset:
            raise HTTPException(status_code=404, detail="no metrics dataset found")
        return dataset_view(dataset)


@app.get("/v1/runs/{run_id}")
def run_metadata(run_id: str) -> dict:
    with SessionLocal() as session:
        events = list(session.scalars(select(EventRecord).where(EventRecord.run_id == run_id).order_by(EventRecord.event_time)).all())
        if not events:
            raise HTTPException(status_code=404, detail="run not found")
        return {"run_id": run_id, "events": [{"event_id": event.event_id, "event_type": event.event_type, "event_time": event.event_time, "raw_path": event.raw_path} for event in events]}


@app.get("/v1/provenance/runs/{run_id}")
def run_provenance(run_id: str) -> dict:
    with SessionLocal() as session:
        events = list(session.scalars(select(EventRecord).where(EventRecord.run_id == run_id).order_by(EventRecord.event_time)).all())
        if not events:
            raise HTTPException(status_code=404, detail="run not found")
        datasets = list(session.scalars(select(DatasetRecord).order_by(DatasetRecord.generated_at.desc())).all())
    return {"run_id": run_id, "source_events": [{"event_id": event.event_id, "event_type": event.event_type, "event_time": event.event_time, "ingestion_time": event.ingestion_time, "raw_path": event.raw_path, "schema_version": event.schema_version} for event in events], "derived_datasets": [dataset_view(dataset) for dataset in datasets], "provenance_contract": "Source events retain event IDs, raw Parquet locations, schema versions, and ingestion times; datasets retain transformation and dataset versions."}


@app.post("/v1/evaluations/scenarios", status_code=201)
def post_evaluation_scenario(request: EvaluationScenarioRequest) -> dict:
    scenario = create_scenario(request)
    return scenario_view(scenario)


@app.post("/v1/evaluations/runs", status_code=201)
def post_evaluation_run(request: EvaluationRunRequest) -> dict:
    try:
        evaluation = record_evaluation(request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return evaluation_view(evaluation)


@app.post("/v1/documents", status_code=201)
def post_document(request: DocumentIngestRequest) -> dict:
    document = ingest_document(request)
    return {"document_id": document.document_id, "title": document.title, "version": document.version, "status": document.status, "object_uri": f"s3://{settings.object_store_bucket}/{document.object_key}", "content_hash": document.content_hash}


@app.post("/v1/features", status_code=201)
def post_feature(request: FeatureUpsertRequest) -> dict:
    row = upsert_feature(request.entity_id, request.feature_name, request.feature_value, request.feature_version, request.event_time)
    return {"entity_id": row.entity_id, "feature_name": row.feature_name, "feature_version": row.feature_version, "event_time": row.event_time}


@app.get("/v1/features/{entity_id}")
def get_entity_features(entity_id: str) -> dict:
    return {"entity_id": entity_id, "features": get_features(entity_id)}


@app.post("/v1/retrieval/query")
def retrieval_query(request: RetrievalQuery) -> dict:
    try:
        return {"query": request.query, "results": retrieve(request.query, request.limit)}
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/v1/access/analytics")
def unified_analytics(agent_id: str | None = None, limit: int = 100) -> dict:
    """Unified access-layer analytics route backed by ClickHouse."""
    try:
        return {"source": "clickhouse", "rows": clickhouse_metrics(agent_id, limit)}
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/v1/access/context")
def unified_context(entity_id: str, request: RetrievalQuery) -> dict:
    """AI data-access layer: one bounded response for online features and retrieval context."""
    try:
        retrieval_results = retrieve(request.query, request.limit)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"entity_id": entity_id, "feature_source": "postgres_online_store", "features": get_features(entity_id), "retrieval_source": "qdrant", "retrieval_results": retrieval_results, "freshness_note": "Features are event-time versioned; retrieval content includes document version metadata."}


@app.get("/v1/datasets/{dataset_id}")
def dataset_metadata(dataset_id: str) -> dict:
    with SessionLocal() as session:
        dataset = session.get(DatasetRecord, dataset_id)
        if not dataset:
            raise HTTPException(status_code=404, detail="dataset not found")
        return dataset_view(dataset)


@app.post("/v1/replays", status_code=202)
def request_replay(request: ReplayRequest, tasks: BackgroundTasks) -> dict:
    replay = create_replay(request.start_time, request.end_time, request.transformation_version)
    tasks.add_task(run_replay, replay.replay_id)
    return replay_view(replay)


@app.get("/v1/replays/{replay_id}")
def replay_status(replay_id: str) -> dict:
    with SessionLocal() as session:
        replay = session.get(ReplayRecord, replay_id)
        if not replay:
            raise HTTPException(status_code=404, detail="replay not found")
        return replay_view(replay)


def dataset_view(dataset: DatasetRecord) -> dict:
    return {"dataset_id": dataset.dataset_id, "dataset_type": dataset.dataset_type, "transformation_version": dataset.transformation_version, "quality_status": dataset.quality_status, "generated_at": dataset.generated_at, "source_start": dataset.source_start, "source_end": dataset.source_end, "row_count": dataset.row_count, "storage_path": dataset.storage_path}


def replay_view(replay: ReplayRecord) -> dict:
    return {"replay_id": replay.replay_id, "status": replay.status, "start_time": replay.start_time, "end_time": replay.end_time, "transformation_version": replay.transformation_version, "dataset_id": replay.dataset_id, "error_message": replay.error_message}


def scenario_view(scenario) -> dict:
    return {"scenario_id": scenario.scenario_id, "source_run_id": scenario.source_run_id, "source_event_id": scenario.source_event_id, "scenario_version": scenario.scenario_version, "failure_category": scenario.failure_category, "expected_behavior": scenario.expected_behavior, "evaluation_method": scenario.evaluation_method, "sanitized_input_reference": scenario.sanitized_input_reference, "source_dataset_version": scenario.source_dataset_version, "status": scenario.status, "created_at": scenario.created_at}


def evaluation_view(evaluation) -> dict:
    return {"evaluation_id": evaluation.evaluation_id, "scenario_id": evaluation.scenario_id, "scenario_version": evaluation.scenario_version, "outcome": evaluation.outcome, "score": evaluation.score, "result_reference": evaluation.result_reference, "created_at": evaluation.created_at}
