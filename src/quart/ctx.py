from __future__ import annotations

from collections.abc import Callable
from contextvars import Token
from functools import update_wrapper
from types import TracebackType
from typing import Any
from typing import Self
from typing import TYPE_CHECKING

from flask.ctx import _AppCtxGlobals as _AppCtxGlobals  # noqa: F401
from werkzeug.exceptions import HTTPException
from werkzeug.routing import MapAdapter

from .globals import _cv_app
from .helpers import _CollectErrors
from .sessions import SessionMixin  # noqa
from .signals import appcontext_popped
from .signals import appcontext_pushed
from .typing import AfterRequestCallable
from .typing import AfterWebsocketCallable
from .wrappers import Request
from .wrappers import Websocket

if TYPE_CHECKING:
    from .app import Quart  # noqa


class AppContext:
    def __init__(
        self,
        app: Quart,
        *,
        request: Request | None = None,
        session: SessionMixin | None = None,
        websocket: Websocket | None = None,
    ) -> None:
        self.app = app

        self.g: _AppCtxGlobals = app.app_ctx_globals_class()

        self.url_adapter: MapAdapter | None = None

        self._request: Request | None = request
        self._session: SessionMixin | None = session
        self._websocket: Websocket | None = websocket
        self._flashes: list[tuple[str, str]] | None = None
        self._after_request_functions: list[AfterRequestCallable] = []
        self._after_websocket_functions: list[AfterWebsocketCallable] = []

        try:
            self.url_adapter = app.create_url_adapter(self._request_websocket)
        except HTTPException as error:
            self._request_websocket.routing_exception = error

        self._cv_token: Token[AppContext] | None = None

        self._push_count: int = 0

    @property
    def has_request(self) -> bool:
        """True if this context was created with request data."""
        return self._request is not None

    @property
    def has_websocket(self) -> bool:
        """True if this context was created with request data."""
        return self._websocket is not None

    def copy(self) -> Self:
        """Create a new context with the same data objects as this context. See
        :func:`.copy_current_request_context`.
        """
        return self.__class__(
            self.app,
            request=self._request,
            session=self._session,
            websocket=self._websocket,
        )

    @property
    def request(self) -> Request:
        """The request object associated with this context. Accessed through
        :data:`.request`. Only available in request contexts, otherwise raises
        :exc:`RuntimeError`.
        """
        if self._request is None:
            raise RuntimeError("There is no request in this context.")

        return self._request

    @property
    def websocket(self) -> Websocket:
        """The websocket object associated with this context. Accessed through
        :data:`.websocket`. Only available in websocket contexts, otherwise raises
        :exc:`RuntimeError`.
        """
        if self._websocket is None:
            raise RuntimeError("There is no websocket in this context.")

        return self._websocket

    @property
    def _request_websocket(self) -> Request | Websocket:
        if self._request is not None:
            return self._request
        elif self._websocket is not None:
            return self._websocket
        else:
            return None

    async def _open_session(self) -> None:
        """Open the session if it is not already open for this request context."""
        if self._request_websocket is None:
            return

        if self._session is None:
            interface = self.app.session_interface
            self._session = await self.app.ensure_async(interface.open_session)(
                self.app, self._request_websocket
            )

            if self._session is None:
                self._session = await interface.make_null_session(self.app)

    @property
    def session(self) -> SessionMixin:
        """The session object associated with this context. Accessed through
        :data:`.session`. Only available in request contexts, otherwise raises
        :exc:`RuntimeError`. Accessing this sets :attr:`.SessionMixin.accessed`.
        """
        self._session.accessed = True
        return self._session

    def match_request(self) -> None:
        """Apply routing to the current request, storing either the matched
        endpoint and args, or a routing exception.
        """
        if self._request_websocket is None:
            raise RuntimeError("There is no request nor websocket in this context.")

        try:
            result = self.url_adapter.match(return_rule=True)
        except HTTPException as error:
            self._request_websocket.routing_exception = error
        else:
            self._request_websocket.url_rule, self._request_websocket.view_args = result  # type: ignore[assignment]

    async def push(self) -> None:
        """Push this context so that it is the active context. If this is a
        request context, calls :meth:`match_request` to perform routing with
        the context active.

        Typically, this is not used directly. Instead, use a ``with`` block
        to manage the context.

        In some situations, such as streaming or testing, the context may be
        pushed multiple times. It will only trigger matching and signals if it
        is not currently pushed.
        """
        self._push_count += 1

        if self._cv_token is not None:
            return

        self._cv_token = _cv_app.set(self)
        await appcontext_pushed.send_async(
            self.app, _async_wrapper=self.app.ensure_async
        )

        if self._request_websocket is not None:
            await self._open_session()

            if self.url_adapter is not None:
                self.match_request()

    async def pop(self, exc: BaseException | None = None) -> None:
        """Pop this context so that it is no longer the active context. Then
        call teardown functions and signals.

        Typically, this is not used directly. Instead, use a ``with`` block
        to manage the context.

        This context must currently be the active context, otherwise a
        :exc:`RuntimeError` is raised. In some situations, such as streaming or
        testing, the context may have been pushed multiple times. It will only
        trigger cleanup once it has been popped as many times as it was pushed.
        Until then, it will remain the active context.

        :param exc: An unhandled exception that was raised while the context was
            active. Passed to teardown functions.

        .. versionchanged:: 0.9
            Added the ``exc`` argument.
        """
        if self._cv_token is None:
            raise RuntimeError(f"Cannot pop this context ({self!r}), it is not pushed.")

        ctx = _cv_app.get(None)

        if ctx is None or self._cv_token is None:
            raise RuntimeError(
                f"Cannot pop this context ({self!r}), there is no active context."
            )

        if ctx is not self:
            raise RuntimeError(
                f"Cannot pop this context ({self!r}), it is not the active"
                f" context ({ctx!r})."
            )

        self._push_count -= 1

        if self._push_count > 0:
            return

        collect_errors = _CollectErrors()

        if self._request is not None:
            with collect_errors:
                await self.app.do_teardown_request(self, exc)

            with collect_errors:
                await self._request.close()

        if self._websocket is not None:
            with collect_errors:
                await self.app.do_teardown_websocket(self, exc)

        with collect_errors:
            await self.app.do_teardown_appcontext(self, exc)

        _cv_app.reset(self._cv_token)
        self._cv_token = None

        with collect_errors:
            await appcontext_popped.send_async(
                self.app, _async_wrapper=self.app.ensure_async
            )

        collect_errors.raise_any("Errors during context teardown")

    async def __aenter__(self) -> Self:
        await self.push()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.pop(exc_value)

    def __repr__(self) -> str:
        if self._request is not None:
            return (
                f"<{type(self).__name__} {id(self)} of {self.app.name},"
                f" {self.request.method} {self.request.url!r}>"
            )

        return f"<{type(self).__name__} {id(self)} of {self.app.name}>"


def after_this_request(func: AfterRequestCallable) -> AfterRequestCallable:
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
    ctx = _cv_app.get(None)
    if ctx is None:
        raise RuntimeError("Not within a request context")
    ctx._after_request_functions.append(func)
    return func


def after_this_websocket(func: AfterWebsocketCallable) -> AfterWebsocketCallable:
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
    ctx = _cv_app.get(None)
    if ctx is None:
        raise RuntimeError("Not within a websocket context")
    ctx._after_websocket_functions.append(func)
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
    original = _cv_app.get(None)

    if original is None:
        raise RuntimeError(
            "'copy_current_app_context' can only be used when a"
            " context is active, such as in a view function."
        )

    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        # Copy the context before pushing, so each worker acts independently.
        async with original.copy() as ctx:
            return await ctx.app.ensure_async(func)(*args, **kwargs)

    return update_wrapper(wrapper, func)


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
    original = _cv_app.get(None)

    if original is None:
        raise RuntimeError(
            "'copy_current_request_context' can only be used when a"
            " request context is active, such as in a view function."
        )

    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        # Copy the context before pushing, so each worker acts independently.
        async with original.copy() as ctx:
            return await ctx.app.ensure_async(func)(*args, **kwargs)

    return update_wrapper(wrapper, func)


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
    original = _cv_app.get(None)

    if original is None:
        raise RuntimeError(
            "'copy_current_websocket_context' can only be used when a"
            " websocket context is active, such as in a view function."
        )

    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        # Copy the context before pushing, so each worker acts independently.
        async with original.copy() as ctx:
            return await ctx.app.ensure_async(func)(*args, **kwargs)

    return update_wrapper(wrapper, func)


def has_app_context() -> bool:
    """Check if execution is within an app context.

    This allows a controlled way to act if there is an app context
    available, or silently not act if not. For example,

    .. code-block:: python

        if has_app_context():
            log.info("Executing in %s context", current_app.name)

    See also :func:`has_request_context`
    """
    return _cv_app.get(None) is not None


def has_request_context() -> bool:
    """Check if execution is within a request context.

    This allows a controlled way to act if there is a request context
    available, or silently not act if not. For example,

    .. code-block:: python

        if has_request_context():
            log.info("Request endpoint %s", request.endpoint)

    See also :func:`has_app_context`.
    """
    return (ctx := _cv_app.get(None)) is not None and ctx.has_request


def has_websocket_context() -> bool:
    """Check if execution is within a websocket context.

    This allows a controlled way to act if there is a websocket
    context available, or silently not act if not. For example,

    .. code-block:: python

        if has_websocket_context():
            log.info("Websocket endpoint %s", websocket.endpoint)

    See also :func:`has_app_context`.
    """
    return (ctx := _cv_app.get(None)) is not None and ctx.has_websocket
