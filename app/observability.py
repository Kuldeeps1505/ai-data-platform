"""Prometheus and OpenTelemetry instrumentation shared by API and consumer."""
import logging
from datetime import datetime, timezone
from prometheus_client import Counter, Gauge, Histogram, make_asgi_app
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from .config import settings

logger = logging.getLogger(__name__)

EVENTS_INGESTED = Counter("ai_data_events_ingested_total", "Accepted events", ["event_type"])
EVENTS_DUPLICATE = Counter("ai_data_events_duplicate_total", "Idempotent duplicate events")
EVENTS_REJECTED = Counter("ai_data_events_rejected_total", "Rejected events", ["reason"])
INGEST_LATENCY = Histogram("ai_data_ingest_duration_seconds", "Event ingestion duration")
CONSUMER_MESSAGES = Counter("ai_data_consumer_messages_total", "Kafka messages processed", ["outcome"])
CONSUMER_LAG = Gauge("ai_data_consumer_lag", "Kafka partition consumer lag", ["topic", "partition"])
PROCESSING_FAILURES = Counter("ai_data_processing_failures_total", "Processing failures", ["component"])
DATASET_FRESHNESS = Gauge("ai_data_dataset_freshness_seconds", "Age of the latest published dataset", ["dataset_type"])
QUALITY_STATUS = Gauge("ai_data_dataset_quality_status", "1 for passed quality, 0 otherwise", ["dataset_type"])


def configure_tracing(app=None) -> None:
    provider = TracerProvider(resource=Resource.create({"service.name": settings.otel_service_name}))
    if settings.otel_exporter_otlp_endpoint:
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint, insecure=True)))
    trace.set_tracer_provider(provider)
    if app:
        FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)


def _refresh_dataset_signals() -> None:
    """Refresh freshness/quality at scrape time, rather than leaving a one-time value."""
    try:
        from sqlalchemy import select
        from .database import DatasetRecord, SessionLocal
        with SessionLocal() as session:
            datasets = session.scalars(select(DatasetRecord).order_by(DatasetRecord.generated_at.desc())).all()
        latest: dict[str, object] = {}
        for dataset in datasets:
            latest.setdefault(dataset.dataset_type, dataset)
        now = datetime.now(timezone.utc)
        for dataset_type, dataset in latest.items():
            DATASET_FRESHNESS.labels(dataset_type=dataset_type).set(max((now - dataset.generated_at).total_seconds(), 0))
            QUALITY_STATUS.labels(dataset_type=dataset_type).set(1 if dataset.quality_status == "passed" else 0)
    except Exception:
        logger.exception("metrics_dataset_signal_refresh_failed")


def mount_metrics(app) -> None:
    prometheus_app = make_asgi_app()

    async def metrics_with_freshness(scope, receive, send):
        _refresh_dataset_signals()
        await prometheus_app(scope, receive, send)

    app.mount("/metrics", metrics_with_freshness)
