from __future__ import annotations

import asyncio
import inspect
import sys
import types
from typing import Any, Callable

from quart.local import LocalStack, TaskLocal
from ._synchronise import sync_with_context


def _patch_asyncio() -> None:
    # This patches asyncio to add a sync_wait method to the event
    # loop. This method can then be called from within a task
    # including a synchronous function called from a task. Sadly it
    # requires the python Task and Future implementations, which
    # invokes some performance cost.
    asyncio.Task = asyncio.tasks._CTask = asyncio.tasks.Task = asyncio.tasks._PyTask  # type: ignore
    asyncio.Future = (  # type: ignore
        asyncio.futures._CFuture  # type: ignore
    ) = asyncio.futures.Future = asyncio.futures._PyFuture  # type: ignore # noqa

    current_policy = asyncio.get_event_loop_policy()
    if hasattr(asyncio, "unix_events"):
        target_policy = asyncio.unix_events._UnixDefaultEventLoopPolicy
    else:
        target_policy = object  # type: ignore

    if not isinstance(current_policy, target_policy):
        raise RuntimeError("Flask Patching only works with the default event loop policy")

    _patch_loop()
    _patch_task()


def _patch_loop() -> None:
    def _sync_wait(self, future):  # type: ignore
        preserved_ready = list(self._ready)
        self._ready.clear()
        current_task = asyncio.tasks._current_tasks.get(self)
        future = asyncio.tasks.ensure_future(future, loop=self)
        while not future.done() and not future.cancelled():
            self._run_once()
            if self._stopping:
                break
            if current_task._must_cancel:
                future.cancel()
        self._ready.extendleft(preserved_ready)
        return future.result()

    asyncio.BaseEventLoop.sync_wait = _sync_wait  # type: ignore


def _patch_task() -> None:
    # Patch the asyncio task to allow it to be re-entered.
    def enter_task(loop, task):  # type: ignore
        asyncio.tasks._current_tasks[loop] = task

    asyncio.tasks._enter_task = enter_task  # type: ignore

    def leave_task(loop, task):  # type: ignore
        del asyncio.tasks._current_tasks[loop]

    asyncio.tasks._leave_task = leave_task  # type: ignore

    def step(self, exception=None):  # type: ignore
        current_task = asyncio.tasks._current_tasks.get(self._loop)
        try:
            self._Task__step_orig(exception)
        finally:
            if current_task is None:
                asyncio.tasks._current_tasks.pop(self._loop, None)
            else:
                asyncio.tasks._current_tasks[self._loop] = current_task

    asyncio.Task._Task__step_orig = asyncio.Task._Task__step  # type: ignore
    asyncio.Task._Task__step = step  # type: ignore


def _context_decorator(func: Callable) -> Callable:
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return sync_with_context(func(*args, **kwargs))

    return wrapper


def _convert_module(new_name, module):  # type: ignore
    new_module = types.ModuleType(new_name)
    for name, member in inspect.getmembers(module):
        if inspect.getmodule(member) == module and inspect.iscoroutinefunction(member):
            setattr(new_module, name, _context_decorator(member))
        else:
            setattr(new_module, name, member)
    setattr(new_module, "_QUART_PATCHED", True)
    return new_module


def _patch_modules() -> None:
    if "flask" in sys.modules:
        raise ImportError("Cannot mock flask, already imported")

    # Create a set of Flask modules, prioritising those within the
    # flask_patch namespace over simple references to the Quart
    # versions.
    flask_modules = {}
    for name, module in list(sys.modules.items()):
        if name.startswith("quart.flask_patch._"):
            continue
        elif name.startswith("quart.flask_patch"):
            setattr(module, "_QUART_PATCHED", True)
            flask_modules[name.replace("quart.flask_patch", "flask")] = module
        elif name.startswith("quart.") and not name.startswith("quart.serving"):
            flask_name = name.replace("quart.", "flask.")
            if flask_name not in flask_modules:
                flask_modules[flask_name] = _convert_module(flask_name, module)

    sys.modules.update(flask_modules)


def _patch_quart_local() -> None:
    LocalStack.__ident_func__ = lambda _: TaskLocal._task_identity()  # type: ignore


def patch_all() -> None:
    _patch_asyncio()
    _patch_modules()
    _patch_quart_local()
