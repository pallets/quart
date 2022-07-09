from __future__ import annotations

import asyncio
from typing import Any, Awaitable

from quart.globals import _cv_app, _cv_request, _cv_websocket


def sync_with_context(future: Awaitable) -> Any:
    context: Any = None
    if _cv_request.get(None) is not None:
        context = _cv_request.get().copy()
    elif _cv_websocket.get(None) is not None:
        context = _cv_websocket.get().copy()
    elif _cv_app.get(None) is not None:
        context = _cv_app.get().copy()

    async def context_wrapper() -> Any:
        if context is not None:
            async with context:
                return await future
        else:
            return await future

    return asyncio.get_event_loop().sync_wait(context_wrapper())  # type: ignore
