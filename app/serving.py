"""Serving adapters: ClickHouse analytics, PostgreSQL feature values, and Qdrant retrieval."""
from datetime import datetime, timezone
import hashlib
import json
from uuid import uuid4
import clickhouse_connect
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
from .config import settings
from .database import FeatureRecord, SessionLocal


def _vector(text: str, size: int = 32) -> list[float]:
    # Deterministic development embedding; replace with an approved embedding model in production.
    digest = hashlib.sha256(text.encode()).digest()
    return [(digest[index % len(digest)] / 127.5) - 1 for index in range(size)]


def _qdrant() -> QdrantClient:
    if not settings.qdrant_url:
        raise RuntimeError("QDRANT_URL is not configured")
    return QdrantClient(url=settings.qdrant_url)


def index_document(document_id: str, title: str, content: str, source_uri: str, version: int) -> None:
    client = _qdrant()
    try:
        client.get_collection(settings.qdrant_collection)
    except Exception:
        client.create_collection(settings.qdrant_collection, vectors_config=VectorParams(size=32, distance=Distance.COSINE))
    point_id = str(uuid4())
    client.upsert(settings.qdrant_collection, points=[PointStruct(id=point_id, vector=_vector(content), payload={"document_id": document_id, "title": title, "source_uri": source_uri, "version": version, "content": content})])


def retrieve(query: str, limit: int) -> list[dict]:
    client = _qdrant()
    response = client.query_points(collection_name=settings.qdrant_collection, query=_vector(query), limit=limit, with_payload=True)
    return [{"score": point.score, "document": point.payload} for point in response.points]


def upsert_feature(entity_id: str, feature_name: str, feature_value: str, feature_version: str, event_time: datetime) -> FeatureRecord:
    feature_id = f"{entity_id}:{feature_name}:{feature_version}"
    with SessionLocal.begin() as session:
        row = session.get(FeatureRecord, feature_id)
        if not row:
            row = FeatureRecord(feature_id=feature_id, entity_id=entity_id, feature_name=feature_name, feature_value=feature_value, feature_version=feature_version, event_time=event_time, created_at=datetime.now(timezone.utc))
            session.add(row)
        elif event_time >= row.event_time:
            row.feature_value, row.event_time = feature_value, event_time
    return row


def get_features(entity_id: str) -> list[dict]:
    with SessionLocal() as session:
        rows = session.query(FeatureRecord).filter_by(entity_id=entity_id).all()
    return [{"feature_name": row.feature_name, "feature_value": row.feature_value, "feature_version": row.feature_version, "event_time": row.event_time} for row in rows]


def clickhouse_metrics(agent_id: str | None, limit: int) -> list[dict]:
    if not settings.clickhouse_host:
        raise RuntimeError("CLICKHOUSE_HOST is not configured")
    client = clickhouse_connect.get_client(host=settings.clickhouse_host, port=settings.clickhouse_port, database=settings.clickhouse_database, username=settings.clickhouse_username, password=settings.clickhouse_password)
    query = "SELECT window_start, agent_id, total_runs, failed_runs, failure_rate, average_latency_ms, p95_latency_ms, generated_at FROM agent_metrics"
    parameters = {}
    if agent_id:
        query += " WHERE agent_id = {agent_id:String}"
        parameters["agent_id"] = agent_id
    query += " ORDER BY window_start DESC LIMIT {limit:UInt32}"
    parameters["limit"] = limit
    result = client.query(query, parameters=parameters)
    return [dict(zip(result.column_names, row)) for row in result.result_rows]


def publish_metrics_to_clickhouse(rows: list[dict]) -> int:
    """Mirror a quality-passed curated dataset to the analytical serving store."""
    if not rows or not settings.clickhouse_host:
        return 0
    client = clickhouse_connect.get_client(host=settings.clickhouse_host, port=settings.clickhouse_port, database=settings.clickhouse_database, username=settings.clickhouse_username, password=settings.clickhouse_password)
    columns = ["window_start", "agent_id", "total_runs", "failed_runs", "failure_rate", "average_latency_ms", "p95_latency_ms", "retry_count", "dataset_version", "transformation_version", "quality_status", "generated_at"]
    client.insert("agent_metrics", [[row.get(column) for column in columns] for row in rows], column_names=columns)
    return len(rows)
