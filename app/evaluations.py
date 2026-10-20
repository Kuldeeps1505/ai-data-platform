"""Evaluation scenarios retain sanitized evidence, provenance, and repeatable result metadata."""
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from uuid import uuid4
from .config import settings
from .database import AuditLogRecord, EvaluationRunRecord, EvaluationScenarioRecord, SessionLocal
from .schemas import EvaluationRunRequest, EvaluationScenarioRequest


def sanitize(text: str) -> str:
    text = re.sub(r"[\w.+-]+@[\w-]+\.[\w.-]+", "[REDACTED_EMAIL]", text)
    text = re.sub(r"\b(?:\+?\d[\d ()-]{7,}\d)\b", "[REDACTED_PHONE]", text)
    return re.sub(r"\b(?:\d[ -]*?){13,16}\b", "[REDACTED_CARD]", text)


def _write_json(kind: str, record_id: str, payload: dict) -> str:
    path = Path(settings.evaluation_storage_path) / kind / f"{record_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return str(path)


def _audit(session, action: str, resource_type: str, resource_id: str, details: dict, actor: str = "api-key") -> None:
    session.add(AuditLogRecord(audit_id=f"audit_{uuid4().hex}", action=action, actor=actor,
        resource_type=resource_type, resource_id=resource_id, occurred_at=datetime.now(timezone.utc), details=json.dumps(details)))


def create_scenario(request: EvaluationScenarioRequest) -> EvaluationScenarioRecord:
    scenario_id = f"scenario_{uuid4().hex}"
    sanitized_reference = None
    if request.sanitized_input:
        sanitized_reference = _write_json("scenarios", scenario_id, {"sanitized_input": sanitize(request.sanitized_input)})
    with SessionLocal.begin() as session:
        existing = session.query(EvaluationScenarioRecord).filter_by(source_run_id=request.source_run_id).count()
        scenario = EvaluationScenarioRecord(scenario_id=scenario_id, source_run_id=request.source_run_id,
            source_event_id=request.source_event_id, scenario_version=existing + 1,
            failure_category=request.failure_category, expected_behavior=request.expected_behavior,
            evaluation_method=request.evaluation_method, sanitized_input_reference=sanitized_reference,
            source_dataset_version=request.source_dataset_version, status="active", created_at=datetime.now(timezone.utc))
        session.add(scenario)
        _audit(session, "evaluation_scenario_created", "evaluation_scenario", scenario_id, {"source_run_id": request.source_run_id})
    return scenario


def record_evaluation(request: EvaluationRunRequest) -> EvaluationRunRecord:
    evaluation_id = f"evaluation_{uuid4().hex}"
    with SessionLocal.begin() as session:
        scenario = session.get(EvaluationScenarioRecord, request.scenario_id)
        if not scenario:
            raise KeyError("evaluation scenario not found")
        result_reference = _write_json("results", evaluation_id, {"observed_behavior": sanitize(request.observed_behavior), "outcome": request.outcome, "score": request.score})
        evaluation = EvaluationRunRecord(evaluation_id=evaluation_id, scenario_id=scenario.scenario_id,
            scenario_version=scenario.scenario_version, outcome=request.outcome, observed_behavior=sanitize(request.observed_behavior),
            score=request.score, result_reference=result_reference, created_at=datetime.now(timezone.utc))
        session.add(evaluation)
        _audit(session, "evaluation_recorded", "evaluation_run", evaluation_id, {"scenario_id": scenario.scenario_id, "outcome": request.outcome})
    return evaluation
