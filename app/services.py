from collections import defaultdict
from datetime import datetime, timedelta, timezone
import hashlib
import json
import logging
from statistics import quantiles
from uuid import uuid4
from sqlalchemy import select
from .database import DatasetRecord, EventRecord, OutboxRecord, ReplayRecord, SessionLocal
from .schemas import AgentExecutionEvent
from .storage import write_curated_metrics, write_quality_report, write_raw_event
from .kafka import publish_event
from .observability import DATASET_FRESHNESS, EVENTS_DUPLICATE, EVENTS_INGESTED, QUALITY_STATUS
from .serving import publish_metrics_to_clickhouse

logger = logging.getLogger(__name__)
TRANSFORMATION_VERSION = "v1"


class ConflictingEventError(Exception):
    pass


def _canonical_payload(event: AgentExecutionEvent) -> dict:
    # Keep native datetimes for PostgreSQL and Parquet; JSON is used only for hashing.
    return event.model_dump(mode="python")


def ingest_event(event: AgentExecutionEvent) -> tuple[bool, EventRecord]:
    payload = _canonical_payload(event)
    payload_hash = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()
    with SessionLocal.begin() as session:
        existing = session.get(EventRecord, event.event_id)
        if existing:
            if existing.payload_hash == payload_hash:
                EVENTS_DUPLICATE.inc()
                return True, existing
            raise ConflictingEventError(f"event_id '{event.event_id}' has a different payload")
        now = datetime.now(timezone.utc)
        raw_path = write_raw_event({**payload, "ingestion_time": now})
        record = EventRecord(
            **payload,
            payload_hash=payload_hash,
            ingestion_time=now,
            raw_path=raw_path,
        )
        session.add(record)
        session.add(OutboxRecord(
            event_id=event.event_id, payload=json.dumps(payload, default=str), status="pending",
            attempts=0, last_error=None, created_at=now, published_at=None,
        ))
        EVENTS_INGESTED.labels(event_type=event.event_type.value).inc()
        logger.info("event_ingested", extra={"event_id": event.event_id, "run_id": event.run_id})
        return False, record


def publish_pending_events(limit: int = 100) -> int:
    """Transactional outbox dispatcher: persisted events survive Kafka outages and are retried."""
    with SessionLocal() as session:
        pending = list(session.scalars(select(OutboxRecord).where(OutboxRecord.status == "pending").limit(limit)).all())
    published = 0
    for outbox in pending:
        try:
            publish_event(json.loads(outbox.payload))
            with SessionLocal.begin() as session:
                current = session.get(OutboxRecord, outbox.event_id)
                current.status = "published"
                current.attempts += 1
                current.published_at = datetime.now(timezone.utc)
                current.last_error = None
            published += 1
        except Exception as exc:
            logger.warning("outbox_publish_failed", extra={"event_id": outbox.event_id})
            with SessionLocal.begin() as session:
                current = session.get(OutboxRecord, outbox.event_id)
                current.attempts += 1
                current.last_error = str(exc)
    return published


def _percentile_95(values: list[int]) -> float | None:
    if not values:
        return None
    if len(values) == 1:
        return float(values[0])
    return round(quantiles(values, n=100, method="inclusive")[94], 2)


def build_metrics(start_time: datetime | None = None, end_time: datetime | None = None,
                  transformation_version: str = TRANSFORMATION_VERSION) -> DatasetRecord:
    with SessionLocal() as session:
        query = select(EventRecord)
        if start_time:
            query = query.where(EventRecord.event_time >= start_time)
        if end_time:
            query = query.where(EventRecord.event_time < end_time)
        events = list(session.scalars(query).all())
        generated_at = datetime.now(timezone.utc)
        dataset_id = f"metrics_{uuid4().hex}"
        grouped: dict[tuple[str, datetime], list[EventRecord]] = defaultdict(list)
        for event in events:
            window = event.event_time.replace(minute=0, second=0, microsecond=0)
            grouped[(event.agent_id, window)].append(event)

        rows = []
        for (agent_id, window_start), group in grouped.items():
            completed = [item for item in group if item.event_type in ("agent.tool_completed", "agent.run_completed", "agent.run_failed")]
            failures = [item for item in completed if item.success is False or item.event_type == "agent.run_failed"]
            latencies = [item.latency_ms for item in completed if item.latency_ms is not None]
            rows.append({
                "window_start": window_start,
                "window_end": window_start + timedelta(hours=1),
                "agent_id": agent_id,
                "total_runs": len({item.run_id for item in completed}),
                "failed_runs": len({item.run_id for item in failures}),
                "failure_rate": round(len({item.run_id for item in failures}) / len({item.run_id for item in completed}), 4) if completed else 0.0,
                "average_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else None,
                "p95_latency_ms": _percentile_95(latencies),
                "retry_count": sum(1 for item in group if item.event_type == "agent.tool_retry"),
                "dataset_version": dataset_id,
                "transformation_version": transformation_version,
                "quality_status": "pending",
                "generated_at": generated_at,
            })
        report = {
            "schema_valid": True,
            "unique_event_ids": len({event.event_id for event in events}) == len(events),
            "required_fields_complete": all(event.run_id and event.agent_id for event in events),
            "freshness_generated_at": generated_at.isoformat(),
            "input_event_count": len(events),
            "metric_row_count": len(rows),
        }
        quality_status = "passed" if all(value is not False for value in report.values() if isinstance(value, bool)) else "failed"
        report["quality_status"] = quality_status
        for row in rows:
            row["quality_status"] = quality_status
        quality_path = write_quality_report(dataset_id, report)
        storage_path = write_curated_metrics(dataset_id, rows) if quality_status == "passed" else quality_path
        dataset = DatasetRecord(
            dataset_id=dataset_id,
            dataset_type="agent_operational_metrics",
            transformation_version=transformation_version,
            quality_status=quality_status,
            generated_at=generated_at,
            source_start=start_time,
            source_end=end_time,
            row_count=len(rows),
            storage_path=storage_path,
            quality_report=json.dumps(report),
        )
        session.add(dataset)
        session.commit()
        if quality_status == "passed":
            try:
                publish_metrics_to_clickhouse(rows)
            except Exception:
                # Curated Parquet remains the system of record; analytical mirror retries can be scheduled.
                logger.exception("clickhouse_metrics_publish_failed", extra={"dataset_id": dataset_id})
        QUALITY_STATUS.labels(dataset_type=dataset.dataset_type).set(1 if quality_status == "passed" else 0)
        DATASET_FRESHNESS.labels(dataset_type=dataset.dataset_type).set(0)
        return dataset


def create_replay(start_time: datetime, end_time: datetime, transformation_version: str) -> ReplayRecord:
    replay = ReplayRecord(
        replay_id=f"replay_{uuid4().hex}", start_time=start_time, end_time=end_time,
        status="queued", transformation_version=transformation_version,
        dataset_id=None, error_message=None, created_at=datetime.now(timezone.utc),
    )
    with SessionLocal.begin() as session:
        session.add(replay)
    return replay


def run_replay(replay_id: str) -> None:
    with SessionLocal.begin() as session:
        replay = session.get(ReplayRecord, replay_id)
        if not replay:
            return
        replay.status = "running"
        start_time, end_time, version = replay.start_time, replay.end_time, replay.transformation_version
    try:
        dataset = build_metrics(start_time, end_time, version)
        with SessionLocal.begin() as session:
            replay = session.get(ReplayRecord, replay_id)
            replay.status = "completed" if dataset.quality_status == "passed" else "quality_failed"
            replay.dataset_id = dataset.dataset_id
    except Exception as exc:  # record operational failure; retain raw data for diagnosis/retry
        logger.exception("replay_failed", extra={"replay_id": replay_id})
        with SessionLocal.begin() as session:
            replay = session.get(ReplayRecord, replay_id)
            replay.status = "failed"
            replay.error_message = str(exc)
