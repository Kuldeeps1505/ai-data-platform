import pytest
from pydantic import ValidationError
from app.schemas import AgentExecutionEvent, DocumentIngestRequest, FeatureUpsertRequest, RetrievalQuery


def event(**overrides):
    payload = {
        "event_id": "evt-1", "schema_version": 1, "event_type": "agent.tool_completed",
        "event_time": "2026-10-18T10:30:00Z", "run_id": "run-1", "agent_id": "agent-1",
        "tool_name": "document_search", "latency_ms": 240, "success": True,
    }
    payload.update(overrides)
    return payload


def test_valid_event_contract():
    result = AgentExecutionEvent(**event())
    assert result.event_id == "evt-1"


def test_event_time_requires_timezone():
    with pytest.raises(ValidationError):
        AgentExecutionEvent(**event(event_time="2026-10-18T10:30:00"))


def test_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        AgentExecutionEvent(**event(untrusted_payload="no"))


def test_rejects_out_of_range_latency():
    with pytest.raises(ValidationError):
        AgentExecutionEvent(**event(latency_ms=-1))


def test_document_contract():
    document = DocumentIngestRequest(document_id="doc-1", title="Runbook", source_uri="docs://runbook", content="safe content")
    assert document.content_type == "text/plain"


def test_feature_and_retrieval_contracts():
    feature = FeatureUpsertRequest(entity_id="agent-1", feature_name="failure_rate", feature_value="0.1", event_time="2026-10-18T10:00:00Z")
    assert feature.feature_version == "v1"
    assert RetrievalQuery(query="search failures").limit == 5


