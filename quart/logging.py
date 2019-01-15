import sys
from logging import DEBUG, Formatter, getLogger, INFO, Logger, NOTSET, StreamHandler
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .app import Quart  # noqa

default_handler = StreamHandler(sys.stderr)
default_handler.setFormatter(Formatter('[%(asctime)s] %(levelname)s in %(module)s: %(message)s'))

serving_handler = StreamHandler(sys.stdout)
serving_handler.setFormatter(Formatter('[%(asctime)s] %(message)s'))


def create_logger(app: 'Quart') -> Logger:
    """Create a logger for the app based on the app settings.

    This creates a logger named quart.app that has a log level based
    on the app configuration.
    """
    logger = getLogger('quart.app')

    if app.debug and logger.level == NOTSET:
        logger.setLevel(DEBUG)

    logger.addHandler(default_handler)
    return logger


def create_serving_logger() -> Logger:
    """Create a logger for serving.

    This creates a logger named quart.serving.
    """
    logger = getLogger('quart.serving')

    if logger.level == NOTSET:
        logger.setLevel(INFO)

    logger.addHandler(serving_handler)
    return logger
