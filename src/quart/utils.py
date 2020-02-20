from __future__ import annotations

import asyncio
import functools
import inspect
import sys
import warnings
from contextvars import copy_context
from functools import partial, wraps
from inspect import isgenerator
from os import PathLike
from pathlib import Path
from typing import Any, AsyncGenerator, Callable, Coroutine, Generator, List, TYPE_CHECKING, Union

from .globals import current_app
from .typing import FilePath

if TYPE_CHECKING:
    from .wrappers.response import Response  # noqa: F401


def redirect(location: str, code: int = 302) -> "Response":
    body = f"""
<!doctype html>
<title>Redirect</title>
<h1>Redirect</h1>
You should be redirected to <a href="{location}">{location}</a>, if not please click the link
    """

    return current_app.response_class(body, status=code, headers={"Location": location})


def ensure_coroutine(func: Callable) -> Callable:
    warnings.warn(
        "Please switch to using a coroutine function. "
        "Synchronous functions will not be supported in 0.13 onwards.",
        DeprecationWarning,
    )
    if is_coroutine_function(func):
        return func
    else:
        async_func = asyncio.coroutine(func)
        async_func._quart_async_wrapper = True  # type: ignore
        return async_func


def file_path_to_path(*paths: FilePath) -> Path:
    # Flask supports bytes paths
    safe_paths: List[Union[str, PathLike]] = []
    for path in paths:
        if isinstance(path, bytes):
            safe_paths.append(path.decode())
        else:
            safe_paths.append(path)
    return Path(*safe_paths)


def run_sync(func: Callable[..., Any]) -> Callable[..., Coroutine[Any, None, None]]:
    """Ensure that the sync function is run within the event loop.

    If the *func* is not a coroutine it will be wrapped such that
    it runs in the default executor (use loop.set_default_executor
    to change). This ensures that synchronous functions do not
    block the event loop.
    """

    @wraps(func)
    async def _wrapper(*args: Any, **kwargs: Any) -> Any:
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None, copy_context().run, partial(func, *args, **kwargs)
        )
        if isgenerator(result):
            return run_sync_iterable(result)  # type: ignore
        else:
            return result

    _wrapper._quart_async_wrapper = True  # type: ignore
    return _wrapper


def run_sync_iterable(iterable: Generator[Any, None, None]) -> AsyncGenerator[Any, None]:
    async def _gen_wrapper() -> AsyncGenerator[Any, None]:
        # Wrap the generator such that each iteration runs
        # in the executor. Then rationalise the raised
        # errors so that it ends.
        def _inner() -> Any:
            # https://bugs.python.org/issue26221
            # StopIteration errors are swallowed by the
            # run_in_exector method
            try:
                return next(iterable)
            except StopIteration:
                raise StopAsyncIteration()

        loop = asyncio.get_running_loop()
        while True:
            try:
                yield await loop.run_in_executor(None, copy_context().run, _inner)
            except StopAsyncIteration:
                return

    return _gen_wrapper()


def is_coroutine_function(func: Any) -> bool:
    # Python < 3.8 does not correctly determine partially wrapped
    # coroutine functions are coroutine functions, hence the need for
    # this to exist. Code taken from CPython.
    if sys.version_info >= (3, 8):
        return asyncio.iscoroutinefunction(func)
    else:
        # Note that there is something special about the CoroutineMock
        # such that it isn't determined as a coroutine function
        # without an explicit check.
        try:
            from asynctest.mock import CoroutineMock

            if isinstance(func, CoroutineMock):
                return True
        except ImportError:
            # Not testing, no asynctest to import
            pass

        while inspect.ismethod(func):
            func = func.__func__
        while isinstance(func, functools.partial):
            func = func.func
        if not inspect.isfunction(func):
            return False
        result = bool(func.__code__.co_flags & inspect.CO_COROUTINE)
        return result or getattr(func, "_is_coroutine", None) is asyncio.coroutines._is_coroutine
