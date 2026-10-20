from datetime import datetime
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field, field_validator


class EventType(str, Enum):
    tool_completed = "agent.tool_completed"
    run_completed = "agent.run_completed"
    run_failed = "agent.run_failed"
    tool_retry = "agent.tool_retry"


class AgentExecutionEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_id: str = Field(min_length=1, max_length=128)
    schema_version: int = Field(ge=1, le=1)
    event_type: EventType
    event_time: datetime
    run_id: str = Field(min_length=1, max_length=128)
    agent_id: str = Field(min_length=1, max_length=128)
    tool_name: str | None = Field(default=None, max_length=128)
    latency_ms: int | None = Field(default=None, ge=0, le=3_600_000)
    success: bool | None = None
    model_version: str | None = Field(default=None, max_length=128)
    prompt_version: str | None = Field(default=None, max_length=128)

    @field_validator("event_time")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("event_time must include a timezone")
        return value


class ReplayRequest(BaseModel):
    start_time: datetime
    end_time: datetime
    transformation_version: str = Field(default="v1", min_length=1, max_length=64)

    @field_validator("end_time")
    @classmethod
    def valid_range(cls, value: datetime, info) -> datetime:
        start = info.data.get("start_time")
        if start and value <= start:
            raise ValueError("end_time must be after start_time")
        return value


class EvaluationScenarioRequest(BaseModel):
    source_run_id: str = Field(min_length=1, max_length=128)
    source_event_id: str | None = Field(default=None, max_length=128)
    failure_category: str = Field(min_length=1, max_length=100)
    expected_behavior: str = Field(min_length=1, max_length=10_000)
    evaluation_method: str = Field(default="human_review", max_length=100)
    source_dataset_version: str | None = Field(default=None, max_length=64)
    sanitized_input: str | None = Field(default=None, max_length=20_000)


class EvaluationRunRequest(BaseModel):
    scenario_id: str = Field(min_length=1, max_length=64)
    observed_behavior: str = Field(min_length=1, max_length=10_000)
    outcome: str = Field(pattern="^(passed|failed|inconclusive)$")
    score: int | None = Field(default=None, ge=0, le=100)


class DocumentIngestRequest(BaseModel):
    document_id: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=512)
    source_uri: str = Field(min_length=1, max_length=2_000)
    content: str = Field(min_length=1, max_length=2_000_000)
    content_type: str = Field(default="text/plain", max_length=100)


class FeatureUpsertRequest(BaseModel):
    entity_id: str = Field(min_length=1, max_length=128)
    feature_name: str = Field(min_length=1, max_length=128)
    feature_value: str = Field(min_length=1, max_length=10_000)
    feature_version: str = Field(default="v1", max_length=64)
    event_time: datetime


class RetrievalQuery(BaseModel):
    query: str = Field(min_length=1, max_length=10_000)
    limit: int = Field(default=5, ge=1, le=50)
