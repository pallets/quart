from __future__ import annotations

from contextvars import ContextVar
from typing import Protocol
from typing import TYPE_CHECKING
from typing import TypeVar

from werkzeug.local import LocalProxy

if TYPE_CHECKING:
    from .app import Quart
    from .ctx import _AppCtxGlobals
    from .ctx import AppContext
    from .sessions import SessionMixin
    from .wrappers import Request
    from .wrappers import Websocket

    T = TypeVar("T", covariant=True)

    class ProxyMixin(Protocol[T]):
        def _get_current_object(self) -> T: ...

    # These subclasses inform type checkers that the proxy objects look like the
    # proxied type along with the _get_current_object method.
    class QuartProxy(ProxyMixin[Quart], Quart): ...

    class AppContextProxy(ProxyMixin[AppContext], AppContext): ...

    class _AppCtxGlobalsProxy(ProxyMixin[_AppCtxGlobals], _AppCtxGlobals): ...

    class RequestProxy(ProxyMixin[Request], Request): ...

    class SessionMixinProxy(ProxyMixin[SessionMixin], SessionMixin): ...

    class WebsocketProxy(ProxyMixin[Websocket], Websocket): ...


_no_app_msg = "Not within an app context"
_cv_app: ContextVar[AppContext] = ContextVar("quart.app_ctx")
app_ctx: AppContextProxy = LocalProxy(  # type: ignore[assignment]
    _cv_app, unbound_message=_no_app_msg
)
current_app: QuartProxy = LocalProxy(  # type: ignore[assignment]
    _cv_app, "app", unbound_message=_no_app_msg
)
g: _AppCtxGlobalsProxy = LocalProxy(  # type: ignore[assignment]
    _cv_app, "g", unbound_message=_no_app_msg
)

request: RequestProxy = LocalProxy(  # type: ignore[assignment]
    _cv_app, "request", unbound_message="Not within a request context"
)
session: SessionMixinProxy = LocalProxy(  # type: ignore[assignment]
    _cv_app, "session", unbound_message="Not within a request nor websocket context"
)
websocket: WebsocketProxy = LocalProxy(  # type: ignore[assignment]
    _cv_app, "websocket", unbound_message="Not within a websocket context"
)
