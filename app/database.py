from datetime import datetime
from sqlalchemy import Boolean, DateTime, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from .config import settings


class Base(DeclarativeBase):
    pass


class EventRecord(Base):
    __tablename__ = "events"
    event_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ingestion_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    run_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    agent_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    tool_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    success: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(128), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(128), nullable=True)
    raw_path: Mapped[str] = mapped_column(Text, nullable=False)


class DatasetRecord(Base):
    __tablename__ = "datasets"
    dataset_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    dataset_type: Mapped[str] = mapped_column(String(100), nullable=False)
    transformation_version: Mapped[str] = mapped_column(String(64), nullable=False)
    quality_status: Mapped[str] = mapped_column(String(32), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    row_count: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    quality_report: Mapped[str] = mapped_column(Text, nullable=False)


class ReplayRecord(Base):
    __tablename__ = "replays"
    replay_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    transformation_version: Mapped[str] = mapped_column(String(64), nullable=False)
    dataset_id: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class StreamProcessedEvent(Base):
    __tablename__ = "stream_processed_events"
    event_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class StreamingWindowRecord(Base):
    __tablename__ = "streaming_windows"
    window_key: Mapped[str] = mapped_column(String(200), primary_key=True)
    agent_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    event_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failure_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    latency_sum_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    latency_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class OutboxRecord(Base):
    __tablename__ = "event_outbox"
    event_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class EvaluationScenarioRecord(Base):
    __tablename__ = "evaluation_scenarios"
    scenario_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_run_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    source_event_id: Mapped[str | None] = mapped_column(String(128))
    scenario_version: Mapped[int] = mapped_column(Integer, nullable=False)
    failure_category: Mapped[str] = mapped_column(String(100), nullable=False)
    expected_behavior: Mapped[str] = mapped_column(Text, nullable=False)
    evaluation_method: Mapped[str] = mapped_column(String(100), nullable=False)
    sanitized_input_reference: Mapped[str | None] = mapped_column(Text)
    source_dataset_version: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class EvaluationRunRecord(Base):
    __tablename__ = "evaluation_runs"
    evaluation_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    scenario_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    scenario_version: Mapped[int] = mapped_column(Integer, nullable=False)
    outcome: Mapped[str] = mapped_column(String(32), nullable=False)
    observed_behavior: Mapped[str] = mapped_column(Text, nullable=False)
    score: Mapped[int | None] = mapped_column(Integer)
    result_reference: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AuditLogRecord(Base):
    __tablename__ = "audit_log"
    audit_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(128), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    details: Mapped[str] = mapped_column(Text, nullable=False)


class DocumentRecord(Base):
    __tablename__ = "documents"
    document_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_uri: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    object_key: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class FeatureRecord(Base):
    __tablename__ = "feature_records"
    feature_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    entity_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    feature_name: Mapped[str] = mapped_column(String(128), nullable=False)
    feature_value: Mapped[str] = mapped_column(Text, nullable=False)
    feature_version: Mapped[str] = mapped_column(String(64), nullable=False)
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def initialise_database() -> None:
    Base.metadata.create_all(bind=engine)
