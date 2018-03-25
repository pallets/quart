import asyncio
from typing import Any

from quart.ctx import copy_current_request_context
from quart.helpers import (
    _endpoint_from_view_func, flash as quart_flash, get_flashed_messages,
    make_response as quart_make_response, url_for,
)
from quart.wrappers import Response

locked_cached_property = property


def make_response(*args: Any) -> Response:
    return asyncio.get_event_loop().sync_wait(quart_make_response(*args))  # type: ignore


def flash(*args: Any, **kwargs: Any) -> None:
    asyncio.get_event_loop().sync_wait(  # type: ignore
        copy_current_request_context(quart_flash)(*args, **kwargs),
    )


__all__ = (
    '_endpoint_from_view_func', 'flash', 'get_flashed_messages', 'locked_cached_property',
    'make_response', 'url_for',
)
