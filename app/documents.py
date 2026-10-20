from datetime import datetime, timezone
import hashlib
from uuid import uuid4
from .database import AuditLogRecord, DocumentRecord, SessionLocal
from .object_store import put_json
from .schemas import DocumentIngestRequest
from .serving import index_document


def ingest_document(request: DocumentIngestRequest) -> DocumentRecord:
    content_hash = hashlib.sha256(request.content.encode()).hexdigest()
    with SessionLocal.begin() as session:
        previous = session.get(DocumentRecord, request.document_id)
        if previous and previous.content_hash == content_hash:
            return previous
        version = (previous.version + 1) if previous else 1
        object_key = f"documents/document_id={request.document_id}/version={version}.json"
        put_json(object_key, {"document_id": request.document_id, "title": request.title, "source_uri": request.source_uri, "content": request.content, "content_type": request.content_type, "version": version, "ingested_at": datetime.now(timezone.utc).isoformat()})
        record = DocumentRecord(document_id=request.document_id, source_uri=request.source_uri, content_hash=content_hash, content_type=request.content_type, title=request.title, object_key=object_key, version=version, status="archived", created_at=datetime.now(timezone.utc))
        if previous:
            session.delete(previous)
        session.add(record)
        session.add(AuditLogRecord(audit_id=f"audit_{uuid4().hex}", action="document_ingested", actor="api-key", resource_type="document", resource_id=request.document_id, occurred_at=datetime.now(timezone.utc), details=f'{{"version": {version}, "content_hash": "{content_hash}"}}'))
    # Archive succeeds before optional index creation; a retry worker can index pending records.
    try:
        index_document(request.document_id, request.title, request.content, request.source_uri, version)
    except Exception:
        with SessionLocal.begin() as session:
            pending = session.get(DocumentRecord, request.document_id)
            pending.status = "archive_pending_index"
        record.status = "archive_pending_index"
    return record
