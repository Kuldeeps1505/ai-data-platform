from datetime import datetime, timezone
import logging
from sqlalchemy import select
from .database import SessionLocal, StreamProcessedEvent, StreamingWindowRecord
from .observability import CONSUMER_MESSAGES, PROCESSING_FAILURES
from .schemas import AgentExecutionEvent

logger = logging.getLogger(__name__)


def _window(event_time: datetime) -> datetime:
    return event_time.replace(minute=0, second=0, microsecond=0)


def process_stream_event(payload: dict) -> str:
    """Idempotently update event-based streaming aggregates. Returns processed or duplicate."""
    event = AgentExecutionEvent.model_validate(payload)
    now = datetime.now(timezone.utc)
    window_start = _window(event.event_time)
    window_key = f"{event.agent_id}:{window_start.isoformat()}"
    with SessionLocal.begin() as session:
        if session.get(StreamProcessedEvent, event.event_id):
            CONSUMER_MESSAGES.labels(outcome="duplicate").inc()
            return "duplicate"
        session.add(StreamProcessedEvent(event_id=event.event_id, processed_at=now))
        record = session.get(StreamingWindowRecord, window_key)
        if not record:
            record = StreamingWindowRecord(
                window_key=window_key, agent_id=event.agent_id, window_start=window_start,
                event_count=0, failure_count=0, latency_sum_ms=0, latency_count=0,
                retry_count=0, last_event_time=event.event_time,
            )
            session.add(record)
        record.event_count += 1
        record.failure_count += int(event.success is False or event.event_type.value == "agent.run_failed")
        record.retry_count += int(event.event_type.value == "agent.tool_retry")
        if event.latency_ms is not None:
            record.latency_sum_ms += event.latency_ms
            record.latency_count += 1
        record.last_event_time = max(record.last_event_time, event.event_time)
    CONSUMER_MESSAGES.labels(outcome="processed").inc()
    return "processed"


def streaming_metrics(start_time: datetime, end_time: datetime) -> list[dict]:
    with SessionLocal() as session:
        rows = session.scalars(
            select(StreamingWindowRecord).where(
                StreamingWindowRecord.window_start >= start_time,
                StreamingWindowRecord.window_start < end_time,
            ).order_by(StreamingWindowRecord.window_start)
        ).all()
    return [{
        "agent_id": row.agent_id, "window_start": row.window_start, "event_count": row.event_count,
        "failure_count": row.failure_count,
        "failure_rate": round(row.failure_count / row.event_count, 4) if row.event_count else 0,
        "average_latency_ms": round(row.latency_sum_ms / row.latency_count, 2) if row.latency_count else None,
        "retry_count": row.retry_count, "last_event_time": row.last_event_time,
    } for row in rows]
