"""Long-running Kafka consumer. Run as its own container, not inside FastAPI workers."""
import json
import logging
import signal
from prometheus_client import start_http_server
from .config import settings
from .kafka import create_consumer, publish_dead_letter, publish_retry
from .logging_config import configure_logging
from .observability import CONSUMER_LAG, PROCESSING_FAILURES, configure_tracing
from .streaming import process_stream_event

running = True


def _stop(*_):
    global running
    running = False


def main() -> None:
    configure_logging(settings.log_level)
    configure_tracing()
    start_http_server(8001)
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    consumer = create_consumer()
    consumer.subscribe([settings.kafka_events_topic, f"{settings.kafka_events_topic}.retry"])
    try:
        while running:
            message = consumer.poll(1.0)
            if message is None:
                continue
            if message.error():
                logging.getLogger(__name__).warning("kafka_consumer_error", extra={"error": str(message.error())})
                continue
            try:
                process_stream_event(json.loads(message.value()))
                consumer.commit(message=message, asynchronous=False)
                low, high = consumer.get_watermark_offsets(message.topic(), message.partition(), cached=False)
                CONSUMER_LAG.labels(topic=message.topic(), partition=str(message.partition())).set(max(high - message.offset() - 1, 0))
            except Exception as exc:
                PROCESSING_FAILURES.labels(component="stream_consumer").inc()
                logging.getLogger(__name__).exception("stream_event_processing_failed")
                payload = json.loads(message.value())
                headers = dict(message.headers() or [])
                raw_attempt = headers.get("attempt", "0")
                attempt = int(raw_attempt.decode() if isinstance(raw_attempt, bytes) else raw_attempt) + 1
                if attempt <= 3:
                    publish_retry(payload, attempt, str(exc))
                else:
                    publish_dead_letter(payload, attempt, str(exc))
                consumer.commit(message=message, asynchronous=False)
    finally:
        consumer.close()


if __name__ == "__main__":
    main()
