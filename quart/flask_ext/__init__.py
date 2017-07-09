import sys

from quart import (
    abort, appcontext_popped, appcontext_pushed, appcontext_tearing_down, before_render_template,
    Blueprint, Config, flash, get_flashed_messages, got_request_exception, has_app_context,
    has_request_context, jsonify, message_flashed, Quart, redirect, request_finished,
    request_started, request_tearing_down, Response, ResponseReturnValue, template_rendered,
    url_for,
)
from quart.flask_ext.globals import (
    _app_ctx_stack, _request_ctx_stack, current_app, g, request, session,
)
from quart.flask_ext.templating import render_template, render_template_string

if 'flask' in sys.modules:
    raise ImportError('Cannot mock flask, already imported')

# Create a set of Flask modules, prioritising those within the
# flask_ext namespace over simple references to the Quart versions.
flask_modules = {}
for name, module in sys.modules.items():
    if name.startswith('quart.flask_ext'):
        flask_modules[name.replace('quart.flask_ext', 'flask')] = module
    if name.startswith('quart.'):
        flask_name = name.replace('quart.', 'flask.')
        if flask_name not in flask_modules:
            flask_modules[flask_name] = module

sys.modules.update(flask_modules)

Flask = Quart

old_handle_request = Quart.handle_request


async def new_handle_request(self, request):  # type: ignore
    request._flask_data = await request._body  # type: ignore
    await request.form
    return await old_handle_request(self, request)

Flask.handle_request = new_handle_request  # type: ignore

__all__ = (
    '_app_ctx_stack', '_request_ctx_stack', 'abort', 'appcontext_popped', 'appcontext_pushed',
    'appcontext_tearing_down', 'before_render_template', 'Blueprint', 'Config', 'current_app',
    'flash', 'g', 'get_flashed_messages', 'got_request_exception', 'has_app_context',
    'has_request_context', 'jsonify', 'message_flashed', 'Quart', 'redirect', 'render_template',
    'render_template_string', 'request', 'request_finished', 'request_started',
    'request_tearing_down', 'Response', 'ResponseReturnValue', 'session', 'template_rendered',
    'url_for',
)
