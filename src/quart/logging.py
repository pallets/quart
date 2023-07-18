from __future__ import annotations

import sys
from logging import DEBUG, Formatter, getLogger, Handler, Logger, LogRecord, NOTSET, StreamHandler
from logging.handlers import QueueHandler, QueueListener
from queue import SimpleQueue as Queue
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .app import Quart  # noqa

default_handler = StreamHandler(sys.stderr)
default_handler.setFormatter(Formatter("[%(asctime)s] %(levelname)s in %(module)s: %(message)s"))


class LocalQueueHandler(QueueHandler):
    """Custom QueueHandler that skips record preparation.

    There is no need to prepare records that go into a local, in-process queue,
    we can skip that process and minimise the cost of logging further.
    """

    def prepare(self, record: LogRecord) -> LogRecord:
        return record


def _setup_logging_queue(*handlers: Handler) -> QueueHandler:
    """Create a new LocalQueueHandler and start an associated QueueListener."""
    queue: Queue = Queue()
    queue_handler = LocalQueueHandler(queue)

    serving_listener = QueueListener(queue, *handlers, respect_handler_level=True)
    serving_listener.start()

    return queue_handler


def has_level_handler(logger: Logger) -> bool:
    """Check if the logger already has a handler"""
    level = logger.getEffectiveLevel()
    current = logger

    while current:
        if any(handler.level <= level for handler in current.handlers):
            return True

        if not current.propagate:
            break

        current = current.parent

    return False


def create_logger(app: Quart) -> Logger:
    """Create a logger for the app based on the app settings.

    This creates a logger named quart.app that has a log level based
    on the app configuration.
    """
    logger = getLogger(app.name)

    if app.debug and logger.level == NOTSET:
        logger.setLevel(DEBUG)

    if not has_level_handler(logger):
        queue_handler = _setup_logging_queue(default_handler)
        logger.addHandler(queue_handler)

    return logger
