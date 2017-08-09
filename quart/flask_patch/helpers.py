import asyncio
from typing import Any

from quart.helpers import (
    flash, get_flashed_messages, make_response as quart_make_response, url_for,
)
from quart.wrappers import Response


def make_response(*args: Any) -> Response:
    return asyncio.get_event_loop().sync_wait(quart_make_response(*args))  # type: ignore


__all__ = ('flash', 'get_flashed_messages', 'make_response', 'url_for')
