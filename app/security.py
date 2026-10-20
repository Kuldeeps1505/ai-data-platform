"""Minimal API-key guard for local/dev deployments; replace with IAM/OIDC in cloud."""
import hmac
from fastapi import HTTPException, Request
from .config import settings

PUBLIC_PATH_PREFIXES = ("/health", "/ready", "/metrics", "/dashboard", "/docs", "/openapi.json")


def require_api_key(request: Request) -> None:
    if request.url.path.startswith(PUBLIC_PATH_PREFIXES):
        return
    if not settings.api_key:
        return  # local Phase 1 compatibility; cloud Terraform injects a managed secret.
    supplied = request.headers.get("X-API-Key", "")
    if not hmac.compare_digest(supplied, settings.api_key):
        raise HTTPException(status_code=401, detail="valid X-API-Key is required")
