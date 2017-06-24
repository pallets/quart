from logging import Formatter, getLogger, Logger, StreamHandler
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .app import Quart  # noqa

PRODUCTION_LOG_FORMAT = "[%(asctime)s] %(levelname)s in %(module)s: %(message)s"
DEBUG_LOG_FORMAT = "{0}\n{1}\n{2}\n{0}".format(
    '-' * 80, "%(levelname)s in %(module)s [%(pathname)s:%(lineno)d]:", "%(message)s",
)


def create_logger(app: 'Quart') -> Logger:
    """Create a logger based on the app settings.

    Notably this will alter the formating and log level based on the
    app configuration.
    """
    logger = getLogger(app.logger_name)
    if app.debug and app.config['LOGGER_HANDLER_POLICY'] in {'always', 'debug'}:
        debug_handler = StreamHandler()
        debug_handler.setFormatter(Formatter(DEBUG_LOG_FORMAT))
        logger.addHandler(debug_handler)

    if not app.debug and app.config['LOGGER_HANDLER_POLICY'] in {'always', 'production'}:
        production_handler = StreamHandler()
        production_handler.setFormatter(Formatter(PRODUCTION_LOG_FORMAT))
        logger.addHandler(production_handler)

    logger.propagate = False
    return logger
