import asyncio
import inspect
import sys
import types
from typing import Any, Callable

from quart.local import LocalStack, TaskLocal
from ._synchronise import sync_with_context

try:
    from asyncio import _enter_task, _leave_task  # type: ignore
except ImportError:
    def _enter_task(loop: asyncio.AbstractEventLoop, task: asyncio.Task) -> None:
        task.__class__._current_tasks[loop] = task  # type: ignore

    def _leave_task(loop: asyncio.AbstractEventLoop, task: asyncio.Task) -> None:
        task.__class__._current_tasks.pop(loop, task)  # type: ignore


def _patch_asyncio() -> None:
    # This patches asyncio to add a sync_wait method to the event
    # loop. This method can then be called from within a task
    # including a synchronous function called from a task. Sadly it
    # requires the python Task and Future implementations, which
    # invokes some performance cost.
    asyncio.Task = asyncio.tasks._CTask = asyncio.tasks.Task = asyncio.tasks._PyTask  # type: ignore
    asyncio.Future = asyncio.futures._CFuture = asyncio.futures.Future = asyncio.futures._PyFuture  # type: ignore # noqa

    def _sync_wait(self, future):  # type: ignore
        preserved_ready = list(self._ready)
        self._ready.clear()
        future = asyncio.tasks.ensure_future(future, loop=self)
        preserved_task = future.current_task(self)
        _leave_task(self, preserved_task)
        while not future.done() and not future.cancelled():
            self._run_once()
            if self._stopping:
                break
        self._ready.extendleft(preserved_ready)
        if preserved_task is not None:
            _enter_task(self, preserved_task)
        return future.result()

    asyncio.BaseEventLoop.sync_wait = _sync_wait  # type: ignore


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
    return new_module


def _patch_modules() -> None:
    if 'flask' in sys.modules:
        raise ImportError('Cannot mock flask, already imported')

    # Create a set of Flask modules, prioritising those within the
    # flask_patch namespace over simple references to the Quart
    # versions.
    flask_modules = {}
    for name, module in list(sys.modules.items()):
        if name.startswith('quart.flask_patch._'):
            continue
        elif name.startswith('quart.flask_patch'):
            flask_modules[name.replace('quart.flask_patch', 'flask')] = module
        elif name.startswith('quart.') and not name.startswith('quart.serving'):
            flask_name = name.replace('quart.', 'flask.')
            if flask_name not in flask_modules:
                flask_modules[flask_name] = _convert_module(flask_name, module)

    sys.modules.update(flask_modules)


def _patch_quart_local() -> None:
    LocalStack.__ident_func__ = lambda _: TaskLocal._task_identity()  # type: ignore


def patch_all() -> None:
    _patch_asyncio()
    _patch_modules()
    _patch_quart_local()
