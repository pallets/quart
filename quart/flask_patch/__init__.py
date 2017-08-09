import asyncio

# This patches asyncio to add a sync_wait method to the event
# loop. This method can then be called from within a task including a
# synchronous function called from a task. Sadly it requires the
# python Task and Future implementations, which invokes some
# performance cost.
asyncio.Task = asyncio.tasks._CTask = asyncio.tasks.Task = asyncio.tasks._PyTask  # type: ignore
asyncio.Future = asyncio.futures._CFuture = asyncio.futures.Future = asyncio.futures._PyFuture  # type: ignore # noqa


def _sync_wait(self, future):  # type: ignore
    preserved_ready = list(self._ready)
    self._ready.clear()
    future = asyncio.tasks.ensure_future(future, loop=self)
    preserved_task = future.current_task(self)
    while not future.done() and not future.cancelled():
        self._run_once()
        if self._stopping:
            break
    self._ready.extendleft(preserved_ready)
    if preserved_task is not None:
        future.__class__._current_tasks[self] = preserved_task
    else:
        future.__class__._current_tasks.pop(self, None)
    return future.result()


asyncio.BaseEventLoop.sync_wait = _sync_wait  # type: ignore

import sys  # noqa: E402

from quart import (
    abort, appcontext_popped, appcontext_pushed, appcontext_tearing_down, before_render_template,
    Blueprint, Config, got_request_exception, has_app_context, has_request_context, jsonify,
    message_flashed, Quart, redirect, request_finished, request_started, request_tearing_down,
    Response, ResponseReturnValue, template_rendered,
)  # noqa: E402
from quart.flask_patch.globals import (
    _app_ctx_stack, _request_ctx_stack, current_app, g, request, session,
)  # noqa: E402
from quart.flask_patch.helpers import make_response  # noqa: E402
from quart.helpers import flash, get_flashed_messages, url_for  # noqa: E402
from quart.flask_patch.templating import render_template, render_template_string  # noqa: E402

if 'flask' in sys.modules:
    raise ImportError('Cannot mock flask, already imported')

# Create a set of Flask modules, prioritising those within the
# flask_patch namespace over simple references to the Quart versions.
flask_modules = {}
for name, module in sys.modules.items():
    if name.startswith('quart.flask_patch'):
        flask_modules[name.replace('quart.flask_patch', 'flask')] = module
    if name.startswith('quart.'):
        flask_name = name.replace('quart.', 'flask.')
        if flask_name not in flask_modules:
            flask_modules[flask_name] = module

sys.modules.update(flask_modules)

Flask = Quart

__all__ = (
    '_app_ctx_stack', '_request_ctx_stack', 'abort', 'appcontext_popped', 'appcontext_pushed',
    'appcontext_tearing_down', 'before_render_template', 'Blueprint', 'Config', 'current_app',
    'flash', 'g', 'get_flashed_messages', 'got_request_exception', 'has_app_context',
    'has_request_context', 'jsonify', 'make_response', 'message_flashed', 'Quart', 'redirect',
    'render_template', 'render_template_string', 'request', 'request_finished', 'request_started',
    'request_tearing_down', 'Response', 'ResponseReturnValue', 'session', 'template_rendered',
    'url_for',
)
