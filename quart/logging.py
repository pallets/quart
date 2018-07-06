import os
import sys
import time
from logging import DEBUG, Formatter, getLogger, INFO, Logger, NOTSET, StreamHandler
from typing import TYPE_CHECKING

from .wrappers import Request, Response

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


class AccessLogAtoms(dict):

    def __init__(
            self,
            request: Request,
            response: Response,
            protocol: str,
            request_time: float,
    ) -> None:
        self.update({
            'h': request.remote_addr,
            'l': '-',
            't': time.strftime('[%d/%b/%Y:%H:%M:%S %z]'),
            'r': f"{request.method} {request.path} {protocol}",
            's': response.status_code,
            'm': request.method,
            'U': request.path,
            'q': request.query_string.decode('ascii'),
            'H': protocol,
            'b': response.headers.get('Content-Length', '-'),
            'B': response.headers.get('Content-Length'),
            'f': request.headers.get('Referer', '-'),
            'a': request.headers.get('User-Agent', '-'),
            'T': int(request_time),
            'D': int(request_time * 1000000),
            'L': f"{request_time:.6f}",
            'p': f"<{os.getpid()}>",
        })
        for name, value in request.headers.items():
            self[f"{{{name.lower()}}}i"] = value
        for name, value in response.headers.items():
            self[f"{{{name.lower()}}}o"] = value
        for name, value in os.environ.items():
            self[f"{{{name.lower()}}}e"] = value

    def __getitem__(self, key: str) -> str:
        try:
            if key.startswith('{'):
                return super().__getitem__(key.lower())
            else:
                return super().__getitem__(key)
        except KeyError:
            return '-'
