"""Retry pending transactional-outbox events while Kafka is unavailable or recovering."""
import logging
import signal
import time
from .config import settings
from .logging_config import configure_logging
from .services import publish_pending_events

running = True


def _stop(*_):
    global running
    running = False


def main() -> None:
    configure_logging(settings.log_level)
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    while running:
        try:
            publish_pending_events()
        except Exception:
            logging.getLogger(__name__).exception("outbox_dispatch_failed")
        time.sleep(2)


if __name__ == "__main__":
    main()
