from __future__ import annotations

from markupsafe import escape as escape, Markup as Markup

from .app import Quart as Quart
from .blueprints import Blueprint as Blueprint
from .config import Config as Config
from .ctx import (
    after_this_request as after_this_request,
    copy_current_app_context as copy_current_app_context,
    copy_current_request_context as copy_current_request_context,
    copy_current_websocket_context as copy_current_websocket_context,
    has_app_context as has_app_context,
    has_request_context as has_request_context,
    has_websocket_context as has_websocket_context,
)
from .globals import (
    current_app as current_app,
    g as g,
    request as request,
    session as session,
    websocket as websocket,
)
from .helpers import (
    abort as abort,
    flash as flash,
    get_flashed_messages as get_flashed_messages,
    get_template_attribute as get_template_attribute,
    make_push_promise as make_push_promise,
    make_response as make_response,
    redirect as redirect,
    send_file as send_file,
    send_from_directory as send_from_directory,
    stream_with_context as stream_with_context,
    url_for as url_for,
)
from .json import jsonify as jsonify
from .signals import (
    appcontext_popped as appcontext_popped,
    appcontext_pushed as appcontext_pushed,
    appcontext_tearing_down as appcontext_tearing_down,
    before_render_template as before_render_template,
    got_request_exception as got_request_exception,
    got_websocket_exception as got_websocket_exception,
    message_flashed as message_flashed,
    request_finished as request_finished,
    request_started as request_started,
    request_tearing_down as request_tearing_down,
    signals_available as signals_available,
    template_rendered as template_rendered,
    websocket_finished as websocket_finished,
    websocket_started as websocket_started,
    websocket_tearing_down as websocket_tearing_down,
)
from .templating import (
    render_template as render_template,
    render_template_string as render_template_string,
    stream_template as stream_template,
    stream_template_string as stream_template_string,
)
from .typing import ResponseReturnValue as ResponseReturnValue
from .wrappers import Request as Request, Response as Response, Websocket as Websocket
