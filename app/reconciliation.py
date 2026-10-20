"""Compare streaming event-based windows to a recomputation from the durable event store."""
from collections import defaultdict
from datetime import datetime
from sqlalchemy import select
from .database import EventRecord, SessionLocal
from .streaming import streaming_metrics


def reconcile(start_time: datetime, end_time: datetime) -> dict:
    """Use event-based semantics shared with the consumer: count, failures, retries, average latency."""
    with SessionLocal() as session:
        events = session.scalars(select(EventRecord).where(
            EventRecord.event_time >= start_time, EventRecord.event_time < end_time
        )).all()
    expected = defaultdict(lambda: {"event_count": 0, "failure_count": 0, "retry_count": 0, "latency_sum": 0, "latency_count": 0})
    for event in events:
        window = event.event_time.replace(minute=0, second=0, microsecond=0)
        row = expected[(event.agent_id, window)]
        row["event_count"] += 1
        row["failure_count"] += int(event.success is False or event.event_type == "agent.run_failed")
        row["retry_count"] += int(event.event_type == "agent.tool_retry")
        if event.latency_ms is not None:
            row["latency_sum"] += event.latency_ms
            row["latency_count"] += 1
    actual = {(row["agent_id"], row["window_start"]): row for row in streaming_metrics(start_time, end_time)}
    differences = []
    for key in sorted(set(expected) | set(actual), key=lambda item: (item[0], item[1])):
        batch = expected.get(key, {"event_count": 0, "failure_count": 0, "retry_count": 0, "latency_sum": 0, "latency_count": 0})
        stream = actual.get(key, {"event_count": 0, "failure_count": 0, "retry_count": 0, "average_latency_ms": None})
        expected_average = round(batch["latency_sum"] / batch["latency_count"], 2) if batch["latency_count"] else None
        actual_values = {key: stream[key] for key in ("event_count", "failure_count", "retry_count")}
        expected_values = {key: batch[key] for key in ("event_count", "failure_count", "retry_count")}
        if actual_values != expected_values or stream["average_latency_ms"] != expected_average:
            differences.append({"agent_id": key[0], "window_start": key[1], "batch": {**expected_values, "average_latency_ms": expected_average}, "streaming": {**actual_values, "average_latency_ms": stream["average_latency_ms"]}})
    return {"start_time": start_time, "end_time": end_time, "matched": not differences, "difference_count": len(differences), "differences": differences}
