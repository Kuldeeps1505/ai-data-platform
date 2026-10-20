"""Kafka producer/consumer helpers with JSON-only, versioned event transport."""
import json
import logging
from confluent_kafka import Consumer, Producer
from .config import settings

logger = logging.getLogger(__name__)


def publish_event(event: dict) -> None:
    """Publish after durable local persistence; PostgreSQL idempotency protects retry delivery."""
    if not settings.kafka_bootstrap_servers:
        raise RuntimeError("KAFKA_BOOTSTRAP_SERVERS is required for Phase 2 streaming")
    _publish(settings.kafka_events_topic, event)


def publish_retry(event: dict, attempt: int, error: str) -> None:
    _publish(f"{settings.kafka_events_topic}.retry", event, headers={"attempt": str(attempt), "error": error[:500]})


def publish_dead_letter(event: dict, attempt: int, error: str) -> None:
    _publish(f"{settings.kafka_events_topic}.dlq", event, headers={"attempt": str(attempt), "error": error[:500]})


def _publish(topic: str, event: dict, headers: dict[str, str] | None = None) -> None:
    producer = Producer({"bootstrap.servers": settings.kafka_bootstrap_servers, "enable.idempotence": True, "acks": "all"})
    producer.produce(topic, key=event["event_id"], value=json.dumps(event, default=str).encode(), headers=headers)
    remaining = producer.flush(10)
    if remaining:
        raise RuntimeError(f"Kafka publish timed out with {remaining} undelivered message(s)")


def create_consumer() -> Consumer:
    if not settings.kafka_bootstrap_servers:
        raise RuntimeError("KAFKA_BOOTSTRAP_SERVERS must be configured for the streaming consumer")
    return Consumer({
        "bootstrap.servers": settings.kafka_bootstrap_servers,
        "group.id": settings.kafka_consumer_group,
        "enable.auto.commit": False,
        "auto.offset.reset": "earliest",
        "isolation.level": "read_committed",
    })
