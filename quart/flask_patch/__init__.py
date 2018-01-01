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

import sys  # noqa: E402, I202
from builtins import globals as builtin_globals  # noqa: E402

from jinja2 import escape, Markup  # noqa: E402
from quart import (  # noqa: I201
    abort, after_this_request, appcontext_popped, appcontext_pushed, appcontext_tearing_down,
    before_render_template, Blueprint, Config, got_request_exception, has_app_context,
    has_request_context, jsonify, message_flashed, Quart, redirect, Request, request_finished,
    request_started, request_tearing_down, Response, ResponseReturnValue, safe_join, send_file,
    send_from_directory, template_rendered,
)  # noqa: E402
from quart.flask_patch.globals import (
    _app_ctx_stack, _request_ctx_stack, current_app, g, request, session,
)  # noqa: E402
from quart.flask_patch.helpers import make_response  # noqa: E402
from quart.helpers import flash, get_flashed_messages, get_template_attribute, url_for  # noqa: E402
from quart.flask_patch.templating import render_template, render_template_string  # noqa: E402, I100
import quart.views  # noqa: E402, F401, I100

if 'flask' in sys.modules:
    raise ImportError('Cannot mock flask, already imported')

# Create a set of Flask modules, prioritising those within the
# flask_patch namespace over simple references to the Quart versions.
flask_modules = {}
for name, module in sys.modules.items():
    if name.startswith('quart.flask_patch'):
        flask_modules[name.replace('quart.flask_patch', 'flask')] = module
    elif name.startswith('quart.') and not name.startswith('quart.serving'):
        flask_name = name.replace('quart.', 'flask.')
        if flask_name not in flask_modules:
            flask_modules[flask_name] = module
        # This ensures that the sub modules e.g. json are importable
        # from flask i.e. from flask import json works (as it puts
        # the json module in this module called json).
        if name.count('.') == 1:
            builtin_globals()[name.rsplit('.', 1)[1]] = module

sys.modules.update(flask_modules)


# Now replace the exception handling defaults to allow for Werkzeug
# HTTPExceptions to be considered in a special way (like the quart
# HTTPException).
try:
    from werkzeug.exceptions import HTTPException
except ImportError:
    HTTPException = object  # type: ignore


old_handle_user_exception = Quart.handle_user_exception


async def new_handle_user_exception(self, error: Exception) -> Response:  # type: ignore
    if isinstance(error, HTTPException):
        return await self.handle_http_exception(error)
    else:
        return await old_handle_user_exception(self, error)


Quart.handle_user_exception = new_handle_user_exception  # type: ignore
old_handle_http_exception = Quart.handle_http_exception


async def new_handle_http_exception(self, error: Exception) -> Response:  # type: ignore
    if isinstance(error, HTTPException):
        handler = self._find_exception_handler(error)
        if handler is None:
            werkzeug_response = error.get_response()
            return await self.make_response((
                werkzeug_response.get_data(), werkzeug_response.status_code,
                werkzeug_response.headers,
            ))
        else:
            return await handler(error)
    else:
        return await old_handle_http_exception(self, error)


Quart.handle_http_exception = new_handle_http_exception  # type: ignore

Flask = Quart

from quart.local import LocalStack, TaskLocal  # noqa: E402, I202

LocalStack.__ident_func__ = lambda _: TaskLocal._task_identity()  # type: ignore

__all__ = (
    '_app_ctx_stack', '_request_ctx_stack', 'abort', 'after_this_request', 'appcontext_popped',
    'appcontext_pushed', 'appcontext_tearing_down', 'before_render_template', 'Blueprint',
    'Config', 'current_app', 'escape', 'flash', 'g', 'get_flashed_messages',
    'got_request_exception', 'get_template_attribute', 'has_app_context', 'has_request_context',
    'jsonify', 'Markup', 'make_response', 'message_flashed', 'Quart', 'redirect',
    'render_template', 'render_template_string', 'request', 'request_finished', 'request_started',
    'request_tearing_down', 'Request', 'Response', 'ResponseReturnValue', 'safe_join',
    'send_file', 'send_from_directory', 'session', 'template_rendered', 'url_for',
)
