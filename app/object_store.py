"""S3-compatible archival. MinIO is used locally; set endpoint empty for AWS S3."""
import json
import boto3
from botocore.client import Config
from .config import settings


def _client():
    kwargs = {"service_name": "s3", "config": Config(signature_version="s3v4")}
    if settings.object_store_endpoint:
        kwargs.update({"endpoint_url": settings.object_store_endpoint, "aws_access_key_id": settings.object_store_access_key, "aws_secret_access_key": settings.object_store_secret_key})
    return boto3.client(**kwargs)


def ensure_bucket() -> None:
    client = _client()
    try:
        client.head_bucket(Bucket=settings.object_store_bucket)
    except Exception:
        client.create_bucket(Bucket=settings.object_store_bucket)


def put_json(key: str, value: dict) -> str:
    client = _client()
    client.put_object(Bucket=settings.object_store_bucket, Key=key, Body=json.dumps(value, default=str).encode(), ContentType="application/json")
    return f"s3://{settings.object_store_bucket}/{key}"
