from types import TracebackType
from typing import Any, Iterator, Optional, TYPE_CHECKING

from .exceptions import MethodNotAllowed, NotFound, RedirectRequired
from .globals import _app_ctx_stack, _request_ctx_stack
from .sessions import Session  # noqa
from .wrappers import Request

if TYPE_CHECKING:
    from .app import Quart  # noqa


class RequestContext:
    """The context relating to the specific request, bound to the current task.

    Do not use directly, prefer the
    :func:`~quart.Quart.request_context` or
    :func:`~quart.Quart.test_request_context` instead.

    Attributes:
        app: The app itself.
        request: The request itself.
        url_adapter: An adapter bound to this request.
        session: The session information relating to this request.
    """

    def __init__(self, app: 'Quart', request: Request) -> None:
        self.app = app
        self.request = request
        self.url_adapter = app.create_url_adapter(self.request)
        self.request.routing_exception = None
        self.session: Optional[Session] = None

        self.match_request()

    def match_request(self) -> None:
        """Match the request against the adapter.

        Override this method to configure request matching, it should
        set the request url_rule and view_args and optionally a
        routing_exception.
        """
        try:
            self.request.url_rule, self.request.view_args = self.url_adapter.match()
        except (NotFound, MethodNotAllowed, RedirectRequired) as error:
            self.request.routing_exception = error

    def __enter__(self) -> None:
        if _app_ctx_stack.top is None:
            app_ctx = self.app.app_context()
            app_ctx.push()
        _request_ctx_stack.push(self)

        self.session = self.app.open_session(self.request)
        if self.session is None:
            self.session = self.app.make_null_session()

    def __exit__(self, exc_type: type, exc_value: BaseException, tb: TracebackType) -> None:
        _request_ctx_stack.pop()
        self.app.app_context().pop()


class AppContext:

    """The context relating to the app bound to the current task.

    Do not use directly, prefer the
    :func:`~quart.Quart.app_context` instead.

    Attributes:
        app: The app itself.
        url_adapter: An adapter bound to the server, but not a
            specific task, useful for route building.
        g: An instance of the ctx globals class.
    """

    def __init__(self, app: 'Quart') -> None:
        self.app = app
        self.url_adapter = app.create_url_adapter(None)
        self.g = app.app_ctx_globals_class()

    def push(self) -> None:
        _app_ctx_stack.push(self)

    def pop(self) -> None:
        _app_ctx_stack.pop()

    def __enter__(self) -> 'AppContext':
        self.push()
        return self

    def __exit__(self, exc_type: type, exc_value: BaseException, tb: TracebackType) -> None:
        self.pop()


def has_app_context() -> bool:
    """Check if execution is within an app context.

    This allows a controlled way to act if there is an app context
    available, or silently not act if not. For example,

    .. code-block:: python

        if has_app_context():
            log.info("Executing in %s context", current_app.name)

    See also :func:`has_request_context`
    """
    return _app_ctx_stack.top is not None


def has_request_context() -> bool:
    """Check if execution is within a request context.

    This allows a controlled way to act if there is a request context
    available, or silently not act if not. For example,

    .. code-block:: python

        if has_request_context():
            log.info("Request endpoint %s", request.endpoint)

    See also :func:`has_app_context`.
    """
    return _request_ctx_stack.top is not None


_sentinel = object()


class _AppCtxGlobals(object):
    """The g class, a plain object with some mapping methods."""

    def get(self, name: str, default: Optional[Any]=None) -> Any:
        """Get a named attribute of this instance, or return the default."""
        return self.__dict__.get(name, default)

    def pop(self, name: str, default: Any=_sentinel) -> Any:
        """Pop, get and remove the named attribute of this instance."""
        if default is _sentinel:
            return self.__dict__.pop(name)
        else:
            return self.__dict__.pop(name, default)

    def setdefault(self, name: str, default: Any=None) -> Any:
        """Set an attribute with a default value."""
        return self.__dict__.setdefault(name, default)

    def __contains__(self, item: Any) -> bool:
        return item in self.__dict__

    def __iter__(self) -> Iterator:
        return iter(self.__dict__)

    def __repr__(self) -> str:
        top = _app_ctx_stack.top
        if top is not None:
            return f"<quart.g of {top.app.name}>"
        return object.__repr__(self)
