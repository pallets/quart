from __future__ import annotations

import asyncio
import inspect
import os
import subprocess
import sys
from collections.abc import AsyncIterator
from collections.abc import Awaitable
from collections.abc import Callable
from collections.abc import Coroutine
from collections.abc import Iterable
from collections.abc import Iterator
from contextvars import copy_context
from functools import partial
from functools import wraps
from pathlib import Path
from typing import Any
from typing import TYPE_CHECKING
from typing import TypeVar

from werkzeug.datastructures import Headers

from .typing import Event
from .typing import FilePath

if TYPE_CHECKING:
    from .wrappers.response import Response  # noqa: F401


class MustReloadError(Exception):
    pass


def file_path_to_path(*paths: FilePath) -> Path:
    # Flask supports bytes paths
    safe_paths: list[str | os.PathLike] = []
    for path in paths:
        if isinstance(path, bytes):
            safe_paths.append(path.decode())
        else:
            safe_paths.append(path)
    return Path(*safe_paths)


def run_sync(func: Callable[..., Any]) -> Callable[..., Coroutine[None, None, Any]]:
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
        if inspect.isgenerator(result):
            return run_sync_iterable(result)
        else:
            return result

    _wrapper._quart_async_wrapper = True  # type: ignore
    return _wrapper


T = TypeVar("T")


def run_sync_iterable(iterable: Iterator[T]) -> AsyncIterator[T]:
    async def _gen_wrapper() -> AsyncIterator[T]:
        # Wrap the generator such that each iteration runs
        # in the executor. Then rationalise the raised
        # errors so that it ends.
        def _inner() -> T:
            # https://bugs.python.org/issue26221
            # StopIteration errors are swallowed by the
            # run_in_exector method
            try:
                return next(iterable)
            except StopIteration as e:
                raise StopAsyncIteration() from e

        loop = asyncio.get_running_loop()
        while True:
            try:
                yield await loop.run_in_executor(None, copy_context().run, _inner)
            except StopAsyncIteration:
                return

    return _gen_wrapper()


def encode_headers(headers: Headers) -> list[tuple[bytes, bytes]]:
    return [(key.lower().encode(), value.encode()) for key, value in headers.items()]


def decode_headers(headers: Iterable[tuple[bytes, bytes]]) -> Headers:
    return Headers([(key.decode(), value.decode()) for key, value in headers])


async def observe_changes(
    sleep: Callable[[float], Awaitable[Any]], shutdown_event: Event
) -> None:
    last_updates: dict[Path, float] = {}
    for module in list(sys.modules.values()):
        filename = getattr(module, "__file__", None)
        if filename is None:
            continue
        path = Path(filename)
        try:
            last_updates[Path(filename)] = path.stat().st_mtime
        except (FileNotFoundError, NotADirectoryError):
            pass

    while not shutdown_event.is_set():
        await sleep(1)

        for index, (path, last_mtime) in enumerate(last_updates.items()):
            if index % 10 == 0:
                # Yield to the event loop
                await sleep(0)

            try:
                mtime = path.stat().st_mtime
            except FileNotFoundError as e:
                # File deleted
                raise MustReloadError() from e
            else:
                if mtime > last_mtime:
                    raise MustReloadError()
                else:
                    last_updates[path] = mtime


async def cancel_tasks(tasks: set[asyncio.Task]) -> None:
    # Cancel any pending, and wait for the cancellation to
    # complete i.e. finish any remaining work.
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    raise_task_exceptions(tasks)


def raise_task_exceptions(tasks: set[asyncio.Task]) -> None:
    # Raise any unexpected exceptions
    for task in tasks:
        if not task.cancelled() and task.exception() is not None:
            raise task.exception()


def run_reloader() -> None:
    while True:
        args = [sys.executable, *sys.orig_argv[1:]]
        new_environ = os.environ.copy()
        new_environ["QUART_RUN_MAIN"] = "true"
        exit_code = subprocess.call(args, env=new_environ, close_fds=False)

        if exit_code == 3:
            sys.exit(0)
