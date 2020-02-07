from functools import wraps
from types import TracebackType
from typing import Any, Callable, cast, Iterator, List, Optional, TYPE_CHECKING  # noqa: F401

from werkzeug.exceptions import (
    BadRequest as WBadRequest,
    MethodNotAllowed as WMethodNotAllowed,
    NotFound as WNotFound,
)
from werkzeug.routing import RequestRedirect as WRequestRedirect

from .exceptions import BadRequest, MethodNotAllowed, NotFound, RedirectRequired
from .globals import _app_ctx_stack, _request_ctx_stack, _websocket_ctx_stack
from .sessions import Session  # noqa
from .signals import appcontext_popped, appcontext_pushed
from .wrappers import BaseRequestWebsocket, Request, Websocket

if TYPE_CHECKING:
    from .app import Quart  # noqa


class _BaseRequestWebsocketContext:
    """A base context relating to either request or websockets, bound to the current task.

    Attributes:
        app: The app itself.
        request_websocket: The request or websocket itself.
        url_adapter: An adapter bound to this request.
        session: The session information relating to this request.
    """

    def __init__(self, app: "Quart", request_websocket: BaseRequestWebsocket) -> None:
        self.app = app
        self.request_websocket = request_websocket
        self.url_adapter = app.create_url_adapter(self.request_websocket)
        self.request_websocket.routing_exception = None
        self.session: Optional[Session] = None

        self.match_request()

    def copy(self) -> "_BaseRequestWebsocketContext":
        return self.__class__(self.app, self.request_websocket)

    def match_request(self) -> None:
        """Match the request against the adapter.

        Override this method to configure request matching, it should
        set the request url_rule and view_args and optionally a
        routing_exception.
        """
        try:
            (
                self.request_websocket.url_rule,
                self.request_websocket.view_args,
            ) = self.url_adapter.match(
                return_rule=True
            )  # noqa
        except WBadRequest:
            self.request_websocket.routing_exception = BadRequest()
        except WNotFound:
            self.request_websocket.routing_exception = NotFound()
        except WMethodNotAllowed as error:
            new_error = MethodNotAllowed(error.valid_methods)
            self.request_websocket.routing_exception = new_error
        except WRequestRedirect as error:
            new_error = RedirectRequired(error.new_url)  # type: ignore
            self.request_websocket.routing_exception = new_error

    async def __aenter__(self) -> "_BaseRequestWebsocketContext":
        app_ctx = _app_ctx_stack.top
        if app_ctx is None:
            app_ctx = self.app.app_context()
        await app_ctx.push()

        self.session = await self.app.open_session(self.request_websocket)
        if self.session is None:
            self.session = await self.app.make_null_session()
        return self

    async def __aexit__(self, exc_type: type, exc_value: BaseException, tb: TracebackType) -> None:
        await _app_ctx_stack.top.pop(exc_value)


class RequestContext(_BaseRequestWebsocketContext):
    """The context relating to the specific request, bound to the current task.

    Do not use directly, prefer the
    :func:`~quart.Quart.request_context` or
    :func:`~quart.Quart.test_request_context` instead.

    Attributes:
        _after_request_functions: List of functions to execute after the curret
            request, see :func:`after_this_request`.
    """

    def __init__(self, app: "Quart", request: Request) -> None:
        super().__init__(app, request)
        self._after_request_functions: List[Callable] = []

    @property
    def request(self) -> Request:
        return cast(Request, self.request_websocket)

    async def __aenter__(self) -> "RequestContext":
        await super().__aenter__()
        _request_ctx_stack.push(self)
        return self

    async def __aexit__(self, exc_type: type, exc_value: BaseException, tb: TracebackType) -> None:
        await self.app.do_teardown_request(exc_value, self)
        _request_ctx_stack.pop()
        await super().__aexit__(exc_type, exc_value, tb)


class WebsocketContext(_BaseRequestWebsocketContext):
    """The context relating to the specific websocket, bound to the current task.

    Do not use directly, prefer the
    :func:`~quart.Quart.websocket_context` or
    :func:`~quart.Quart.test_websocket_context` instead.

    Attributes:
        _after_websocket_functions: List of functions to execute after the curret
            websocket, see :func:`after_this_websocket`.
    """

    def __init__(self, app: "Quart", request: Websocket) -> None:
        super().__init__(app, request)
        self._after_websocket_functions: List[Callable] = []

    @property
    def websocket(self) -> Websocket:
        return cast(Websocket, self.request_websocket)

    async def __aenter__(self) -> "WebsocketContext":
        await super().__aenter__()
        _websocket_ctx_stack.push(self)
        return self

    async def __aexit__(self, exc_type: type, exc_value: BaseException, tb: TracebackType) -> None:
        await self.app.do_teardown_websocket(exc_value, self)
        _websocket_ctx_stack.pop()
        await super().__aexit__(exc_type, exc_value, tb)


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

    def __init__(self, app: "Quart") -> None:
        self.app = app
        self.url_adapter = app.create_url_adapter(None)
        self.g = app.app_ctx_globals_class()
        self._app_reference_count = 0

    def copy(self) -> "AppContext":
        app_context = self.__class__(self.app)
        app_context.g = self.g
        return app_context

    async def push(self) -> None:
        self._app_reference_count += 1
        _app_ctx_stack.push(self)
        await appcontext_pushed.send(self.app)

    async def pop(self, exc: Optional[BaseException]) -> None:
        self._app_reference_count -= 1
        try:
            if self._app_reference_count <= 0:
                await self.app.do_teardown_appcontext(exc)
        finally:
            _app_ctx_stack.pop()
        await appcontext_popped.send(self.app)

    async def __aenter__(self) -> "AppContext":
        await self.push()
        return self

    async def __aexit__(self, exc_type: type, exc_value: BaseException, tb: TracebackType) -> None:
        await self.pop(exc_value)


def after_this_request(func: Callable) -> Callable:
    """Schedule the func to be called after the current request.

    This is useful in situations whereby you want an after request
    function for a specific route or circumstance only, for example,

    .. code-block:: python

        def index():
            @after_this_request
            def set_cookie(response):
                response.set_cookie('special', 'value')
                return response

            ...
    """
    _request_ctx_stack.top._after_request_functions.append(func)
    return func


def after_this_websocket(func: Callable) -> Callable:
    """Schedule the func to be called after the current websocket.

    This is useful in situations whereby you want an after websocket
    function for a specific route or circumstance only, for example,

    .. note::
        The response is an optional argument, and will only be
        passed if the websocket was not active (i.e. there was an
        error).

    .. code-block:: python

        def index():
            @after_this_websocket
            def set_cookie(response: Optional[Response]):
                response.set_cookie('special', 'value')
                return response

            ...

    """
    _websocket_ctx_stack.top._after_websocket_functions.append(func)
    return func


def copy_current_app_context(func: Callable) -> Callable:
    """Share the current app context with the function decorated.

    The app context is local per task and hence will not be available
    in any other task. This decorator can be used to make the context
    available,

    .. code-block:: python

        @copy_current_app_context
        async def within_context() -> None:
            name = current_app.name
            ...

    """
    if not has_app_context():
        raise RuntimeError("Attempt to copy app context outside of a app context")

    app_context = _app_ctx_stack.top.copy()

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        async with app_context:
            return await func(*args, **kwargs)

    return wrapper


def copy_current_request_context(func: Callable) -> Callable:
    """Share the current request context with the function decorated.

    The request context is local per task and hence will not be
    available in any other task. This decorator can be used to make
    the context available,

    .. code-block:: python

        @copy_current_request_context
        async def within_context() -> None:
            method = request.method
            ...

    """
    if not has_request_context():
        raise RuntimeError("Attempt to copy request context outside of a request context")

    request_context = _request_ctx_stack.top.copy()

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        async with request_context:
            return await func(*args, **kwargs)

    return wrapper


def copy_current_websocket_context(func: Callable) -> Callable:
    """Share the current websocket context with the function decorated.

    The websocket context is local per task and hence will not be
    available in any other task. This decorator can be used to make
    the context available,

    .. code-block:: python

        @copy_current_websocket_context
        async def within_context() -> None:
            method = websocket.method
            ...

    """
    if not has_websocket_context():
        raise RuntimeError("Attempt to copy websocket context outside of a websocket context")

    websocket_context = _websocket_ctx_stack.top.copy()

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        async with websocket_context:
            return await func(*args, **kwargs)

    return wrapper


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


def has_websocket_context() -> bool:
    """Check if execution is within a websocket context.

    This allows a controlled way to act if there is a websocket
    context available, or silently not act if not. For example,

    .. code-block:: python

        if has_websocket_context():
            log.info("Websocket endpoint %s", websocket.endpoint)

    See also :func:`has_app_context`.
    """
    return _websocket_ctx_stack.top is not None


_sentinel = object()


class _AppCtxGlobals:
    """The g class, a plain object with some mapping methods."""

    def get(self, name: str, default: Optional[Any] = None) -> Any:
        """Get a named attribute of this instance, or return the default."""
        return self.__dict__.get(name, default)

    def pop(self, name: str, default: Any = _sentinel) -> Any:
        """Pop, get and remove the named attribute of this instance."""
        if default is _sentinel:
            return self.__dict__.pop(name)
        else:
            return self.__dict__.pop(name, default)

    def setdefault(self, name: str, default: Any = None) -> Any:
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
