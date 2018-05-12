import asyncio
import inspect
import linecache
from typing import Any, Awaitable, Callable

from quart.globals import _app_ctx_stack, _request_ctx_stack, _websocket_ctx_stack


def sync_with_context(future: Awaitable) -> Any:
    context = None
    if _request_ctx_stack.top is not None:
        context = _request_ctx_stack.top.copy()
    elif _websocket_ctx_stack.top is not None:
        context = _websocket_ctx_stack.top.copy()
    elif _app_ctx_stack.top is not None:
        context = _app_ctx_stack.top.copy()

    async def context_wrapper() -> Any:
        if context is not None:
            async with context:
                return await future
        else:
            return await future

    return asyncio.get_event_loop().sync_wait(context_wrapper())  # type: ignore


def maybe_sync(func: Callable) -> Callable:
    """Make the func synchronous iff it was called synchronously."""

    def maybe_sync_wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            stack = inspect.stack()
            if _is_async_call(func.__name__, stack[1].filename, stack[1].lineno):
                return func(*args, **kwargs)
            else:
                return sync_with_context(func(*args, **kwargs))
        finally:
            del stack

    return maybe_sync_wrapper


def _is_async_call(func_name: str, filename: str, lineno: int, offset: int=0) -> bool:
    """Try a best effort guess of how the function was called.

    This is quite horrible to read/think about, but other attempts
    using inspect are not affectual.
    """
    line = linecache.getline(filename, lineno - offset)
    if 'await' in line or 'async' in line:
        return True
    elif f"{func_name}(" in line:
        return False
    elif offset < 100:  # Hard to imagine a function call with more than 100 lines...
        return _is_async_call(func_name, filename, lineno, offset + 1)
    else:
        return False
