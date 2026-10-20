from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv(
        "DATABASE_URL", "postgresql+psycopg://platform:platform@localhost:5432/ai_data_platform"
    )
    raw_storage_path: str = os.getenv("RAW_STORAGE_PATH", "./data/raw")
    curated_storage_path: str = os.getenv("CURATED_STORAGE_PATH", "./data/curated")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    max_event_size_bytes: int = int(os.getenv("MAX_EVENT_SIZE_BYTES", "65536"))
    kafka_bootstrap_servers: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "")
    kafka_events_topic: str = os.getenv("KAFKA_EVENTS_TOPIC", "agent-events.v1")
    kafka_consumer_group: str = os.getenv("KAFKA_CONSUMER_GROUP", "ai-data-platform-streaming-v1")
    otel_exporter_otlp_endpoint: str = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
    otel_service_name: str = os.getenv("OTEL_SERVICE_NAME", "ai-data-platform-api")
    api_key: str = os.getenv("API_KEY", "")
    evaluation_storage_path: str = os.getenv("EVALUATION_STORAGE_PATH", "./data/evaluations")
    object_store_endpoint: str = os.getenv("OBJECT_STORE_ENDPOINT", "")
    object_store_access_key: str = os.getenv("OBJECT_STORE_ACCESS_KEY", "")
    object_store_secret_key: str = os.getenv("OBJECT_STORE_SECRET_KEY", "")
    object_store_bucket: str = os.getenv("OBJECT_STORE_BUCKET", "ai-data-platform")
    clickhouse_host: str = os.getenv("CLICKHOUSE_HOST", "")
    clickhouse_port: int = int(os.getenv("CLICKHOUSE_PORT", "8123"))
    clickhouse_database: str = os.getenv("CLICKHOUSE_DATABASE", "ai_data_platform")
    clickhouse_username: str = os.getenv("CLICKHOUSE_USERNAME", "platform")
    clickhouse_password: str = os.getenv("CLICKHOUSE_PASSWORD", "platform")
    qdrant_url: str = os.getenv("QDRANT_URL", "")
    qdrant_collection: str = os.getenv("QDRANT_COLLECTION", "documents")


settings = Settings()
