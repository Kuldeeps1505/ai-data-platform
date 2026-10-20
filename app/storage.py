from datetime import datetime, timezone
from pathlib import Path
import json
import pyarrow as pa
import pyarrow.parquet as pq
from .config import settings


def _append_rows(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    new_table = pa.Table.from_pylist(rows)
    if path.exists():
        new_table = pa.concat_tables([pq.read_table(path), new_table], promote_options="default")
    pq.write_table(new_table, path)


def write_raw_event(event: dict) -> str:
    event_day = event["event_time"].astimezone(timezone.utc).strftime("%Y-%m-%d")
    path = Path(settings.raw_storage_path) / f"event_date={event_day}" / "events.parquet"
    serializable = {key: value.isoformat() if isinstance(value, datetime) else value for key, value in event.items()}
    _append_rows(path, [serializable])
    return str(path)


def write_curated_metrics(dataset_id: str, rows: list[dict]) -> str:
    path = Path(settings.curated_storage_path) / "agent_metrics" / f"dataset_id={dataset_id}" / "metrics.parquet"
    serializable = []
    for row in rows:
        serializable.append({key: value.isoformat() if isinstance(value, datetime) else value for key, value in row.items()})
    _append_rows(path, serializable)
    return str(path)


def quality_report_path(dataset_id: str) -> str:
    return str(Path(settings.curated_storage_path) / "agent_metrics" / f"dataset_id={dataset_id}" / "quality.json")


def write_quality_report(dataset_id: str, report: dict) -> str:
    path = Path(quality_report_path(dataset_id))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    return str(path)
