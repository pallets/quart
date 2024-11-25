from __future__ import annotations

from contextvars import ContextVar
from typing import TYPE_CHECKING

from werkzeug.local import LocalProxy

if TYPE_CHECKING:
    from .app import Quart
    from .ctx import _AppCtxGlobals
    from .ctx import AppContext
    from .ctx import RequestContext
    from .ctx import WebsocketContext
    from .sessions import SessionMixin
    from .wrappers import Request
    from .wrappers import Websocket

_no_app_msg = "Not within an app context"
_cv_app: ContextVar[AppContext] = ContextVar("quart.app_ctx")
app_ctx: _AppCtxGlobals = LocalProxy(  # type: ignore[assignment]
    _cv_app, unbound_message=_no_app_msg
)
current_app: Quart = LocalProxy(  # type: ignore[assignment]
    _cv_app, "app", unbound_message=_no_app_msg
)
g: _AppCtxGlobals = LocalProxy(  # type: ignore[assignment]
    _cv_app, "g", unbound_message=_no_app_msg
)

_no_req_msg = "Not within a request context"
_cv_request: ContextVar[RequestContext] = ContextVar("quart.request_ctx")
request_ctx: RequestContext = LocalProxy(  # type: ignore[assignment]
    _cv_request, unbound_message=_no_req_msg
)
request: Request = LocalProxy(  # type: ignore[assignment]
    _cv_request, "request", unbound_message=_no_req_msg
)

_no_websocket_msg = "Not within a websocket context"
_cv_websocket: ContextVar[WebsocketContext] = ContextVar("quart.websocket_ctx")
websocket_ctx: WebsocketContext = LocalProxy(  # type: ignore[assignment]
    _cv_websocket, unbound_message=_no_websocket_msg
)
websocket: Websocket = LocalProxy(  # type: ignore[assignment]
    _cv_websocket, "websocket", unbound_message=_no_websocket_msg
)


def _session_lookup() -> RequestContext | WebsocketContext:
    try:
        return _cv_request.get()
    except LookupError:
        try:
            return _cv_websocket.get()
        except LookupError:
            raise RuntimeError("Not within a request nor websocket context") from None


session: SessionMixin = LocalProxy(_session_lookup, "session")  # type: ignore[assignment]
