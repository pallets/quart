from __future__ import annotations

import os
from collections import defaultdict
from functools import wraps
from pathlib import Path
from typing import Any, Callable, cast, Iterable, TYPE_CHECKING, TypeVar

from aiofiles import open as async_open
from aiofiles.base import AiofilesContextManager
from aiofiles.threadpool.binary import AsyncBufferedReader
from jinja2 import FileSystemLoader
from werkzeug.exceptions import default_exceptions, HTTPException

from .cli import AppGroup
from .globals import current_app
from .helpers import get_root_path, send_from_directory
from .templating import _default_template_ctx_processor
from .typing import (
    AfterRequestCallable,
    AfterWebsocketCallable,
    AppOrBlueprintKey,
    BeforeRequestCallable,
    BeforeWebsocketCallable,
    ErrorHandlerCallable,
    FilePath,
    RouteCallable,
    TeardownCallable,
    TemplateContextProcessorCallable,
    URLDefaultCallable,
    URLValuePreprocessorCallable,
    WebsocketCallable,
)
from .utils import file_path_to_path

if TYPE_CHECKING:
    from .wrappers import Response


F = TypeVar("F", bound=Callable)
T_after_request = TypeVar("T_after_request", bound=AfterRequestCallable)
T_after_websocket = TypeVar("T_after_websocket", bound=AfterWebsocketCallable)
T_before_request = TypeVar("T_before_request", bound=BeforeRequestCallable)
T_before_websocket = TypeVar("T_before_websocket", bound=BeforeWebsocketCallable)
T_error_handler = TypeVar("T_error_handler", bound=ErrorHandlerCallable)
T_teardown = TypeVar("T_teardown", bound=TeardownCallable)
T_template_context_processor = TypeVar(
    "T_template_context_processor", bound=TemplateContextProcessorCallable
)
T_url_defaults = TypeVar("T_url_defaults", bound=URLDefaultCallable)
T_url_value_preprocessor = TypeVar("T_url_value_preprocessor", bound=URLValuePreprocessorCallable)
T_route = TypeVar("T_route", bound=RouteCallable)
T_websocket = TypeVar("T_websocket", bound=WebsocketCallable)


def setupmethod(func: F) -> F:
    @wraps(func)
    def wrapper(self: Scaffold, *args: Any, **kwargs: Any) -> Any:
        self._check_setup_finished(func.__name__)
        return func(self, *args, **kwargs)

    return cast(F, wrapper)


class Scaffold:
    """Base class for Quart and Blueprint classes."""

    name: str

    def __init__(
        self,
        import_name: str,
        static_folder: str | None = None,
        static_url_path: str | None = None,
        template_folder: str | None = None,
        root_path: str | None = None,
    ) -> None:
        self.import_name = import_name
        self.template_folder = Path(template_folder) if template_folder is not None else None

        if root_path is None:
            self.root_path = Path(get_root_path(import_name))
        else:
            self.root_path = Path(root_path)

        self._static_folder: Path | None = None
        self._static_url_path: str | None = None
        self.static_folder = static_folder  # type: ignore
        self.static_url_path = static_url_path

        self.cli = AppGroup()

        # Functions that are called after a HTTP view function has
        # handled a request and returned a response.
        self.after_request_funcs: dict[AppOrBlueprintKey, list[AfterRequestCallable]] = defaultdict(
            list
        )

        # Functions that are called after a WebSocket view function
        # handled a websocket request and has returned (possibly
        # returning a response).
        self.after_websocket_funcs: dict[
            AppOrBlueprintKey, list[AfterWebsocketCallable]
        ] = defaultdict(list)

        # Called before a HTTP view function handles a request.
        self.before_request_funcs: dict[
            AppOrBlueprintKey, list[BeforeRequestCallable]
        ] = defaultdict(list)

        # Called before a WebSocket view function handles a websocket
        # request.
        self.before_websocket_funcs: dict[
            AppOrBlueprintKey, list[BeforeWebsocketCallable]
        ] = defaultdict(list)

        # The registered error handlers, keyed by blueprint (None for
        # app) then by Exception type.
        self.error_handler_spec: dict[
            AppOrBlueprintKey,
            dict[int | None, dict[type[Exception], ErrorHandlerCallable]],
        ] = defaultdict(lambda: defaultdict(dict))

        # Called after a HTTP request has been handled, even if the
        # handling results in an exception.
        self.teardown_request_funcs: dict[AppOrBlueprintKey, list[TeardownCallable]] = defaultdict(
            list
        )

        # Called after a WebSocket request has been handled, even if
        # the handling results in an exception.
        self.teardown_websocket_funcs: dict[
            AppOrBlueprintKey, list[TeardownCallable]
        ] = defaultdict(list)

        # Template context processors keyed by blueprint (None for
        # app).
        self.template_context_processors: dict[
            AppOrBlueprintKey, list[TemplateContextProcessorCallable]
        ] = defaultdict(list, {None: [_default_template_ctx_processor]})

        # View functions keyed by endpoint.
        self.view_functions: dict[str, Callable] = {}

        # The URL value preprocessor functions keyed by blueprint
        # (None for app) as used when matching
        self.url_value_preprocessors: dict[
            AppOrBlueprintKey,
            list[URLValuePreprocessorCallable],
        ] = defaultdict(list)

        # The URL value default injector functions keyed by blueprint
        # (None for app) as used when building urls.
        self.url_default_functions: dict[AppOrBlueprintKey, list[URLDefaultCallable]] = defaultdict(
            list
        )

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {self.name!r}>"

    @property
    def static_folder(self) -> Path | None:
        if self._static_folder is not None:
            return self.root_path / self._static_folder
        else:
            return None

    @static_folder.setter
    def static_folder(self, static_folder: FilePath | None) -> None:
        if static_folder is not None:
            self._static_folder = file_path_to_path(static_folder)
        else:
            self._static_folder = None

    @property
    def static_url_path(self) -> str | None:
        if self._static_url_path is not None:
            return self._static_url_path
        if self.static_folder is not None:
            return "/" + self.static_folder.name
        else:
            return None

    @static_url_path.setter
    def static_url_path(self, static_url_path: str) -> None:
        self._static_url_path = static_url_path

    @property
    def has_static_folder(self) -> bool:
        return self.static_folder is not None

    def get_send_file_max_age(self, filename: str) -> int | None:
        if current_app.send_file_max_age_default is not None:
            return int(current_app.send_file_max_age_default.total_seconds())
        return None

    async def send_static_file(self, filename: str) -> Response:
        if not self.has_static_folder:
            raise RuntimeError("No static folder for this object")
        return await send_from_directory(self.static_folder, filename)

    @property
    def jinja_loader(self) -> FileSystemLoader | None:
        if self.template_folder is not None:
            return FileSystemLoader(os.fspath(self.root_path / self.template_folder))
        else:
            return None

    async def open_resource(
        self,
        path: FilePath,
        mode: str = "rb",
    ) -> AiofilesContextManager[None, None, AsyncBufferedReader]:
        """Open a file for reading.

        Use as

        .. code-block:: python

            async with await app.open_resource(path) as file_:
                await file_.read()
        """
        if mode not in {"r", "rb"}:
            raise ValueError("Files can only be opened for reading")
        return async_open(self.root_path / file_path_to_path(path), mode)  # type: ignore

    def _method_route(self, method: str, rule: str, options: dict) -> Callable[[T_route], T_route]:
        if "methods" in options:
            raise TypeError("Methods cannot be supplied, use the 'route' decorator instead.")

        return self.route(rule, methods=[method], **options)

    @setupmethod
    def get(self, rule: str, **options: Any) -> Callable[[T_route], T_route]:
        """Syntactic sugar for :meth:`route` with ``methods=["GET"]``."""
        return self._method_route("GET", rule, options)

    @setupmethod
    def post(self, rule: str, **options: Any) -> Callable[[T_route], T_route]:
        """Syntactic sugar for :meth:`route` with ``methods=["POST"]``."""
        return self._method_route("POST", rule, options)

    @setupmethod
    def put(self, rule: str, **options: Any) -> Callable[[T_route], T_route]:
        """Syntactic sugar for :meth:`route` with ``methods=["PUT"]``."""
        return self._method_route("PUT", rule, options)

    @setupmethod
    def delete(self, rule: str, **options: Any) -> Callable[[T_route], T_route]:
        """Syntactic sugar for :meth:`route` with ``methods=["DELETE"]``."""
        return self._method_route("DELETE", rule, options)

    @setupmethod
    def patch(self, rule: str, **options: Any) -> Callable[[T_route], T_route]:
        """Syntactic sugar for :meth:`route` with ``methods=["PATCH"]``."""
        return self._method_route("PATCH", rule, options)

    @setupmethod
    def route(
        self,
        rule: str,
        methods: list[str] | None = None,
        endpoint: str | None = None,
        defaults: dict | None = None,
        host: str | None = None,
        subdomain: str | None = None,
        *,
        provide_automatic_options: bool | None = None,
        strict_slashes: bool | None = None,
    ) -> Callable[[T_route], T_route]:
        """Add a HTTP request handling route.

        This is designed to be used as a decorator, if used to
        decorate a synchronous function, the function will be wrapped
        in :func:`~quart.utils.run_sync` and run in a thread executor
        (with the wrapped function returned). An example usage,

        .. code-block:: python

            @app.route('/')
            async def route():
                ...

        Arguments:
            rule: The path to route on, should start with a ``/``.
            methods: List of HTTP verbs the function routes.
            endpoint: Optional endpoint name, if not present the
                function name is used.
            defaults: A dictionary of variables to provide automatically, use
                to provide a simpler default path for a route, e.g. to allow
                for ``/book`` rather than ``/book/0``,

                .. code-block:: python

                    @app.route('/book', defaults={'page': 0})
                    @app.route('/book/<int:page>')
                    def book(page):
                        ...

            host: The full host name for this route (should include subdomain
                if needed) - cannot be used with subdomain.
            subdomain: A subdomain for this specific route.
            provide_automatic_options: Optionally False to prevent
                OPTION handling.
            strict_slashes: Strictly match the trailing slash present in the
                path. Will redirect a leaf (no slash) to a branch (with slash).
        """

        def decorator(func: T_route) -> T_route:
            self.add_url_rule(
                rule,
                endpoint,
                func,
                provide_automatic_options=provide_automatic_options,
                methods=methods,
                defaults=defaults,
                host=host,
                subdomain=subdomain,
                strict_slashes=strict_slashes,
            )
            return func

        return decorator

    @setupmethod
    def add_url_rule(
        self,
        rule: str,
        endpoint: str | None = None,
        view_func: RouteCallable | None = None,
        provide_automatic_options: bool | None = None,
        *,
        methods: Iterable[str] | None = None,
        defaults: dict | None = None,
        host: str | None = None,
        subdomain: str | None = None,
        is_websocket: bool = False,
        strict_slashes: bool | None = None,
        merge_slashes: bool | None = None,
    ) -> None:
        """Add a route/url rule to the application.

        This is designed to be used on the application directly. An
        example usage,

        .. code-block:: python

            def route():
                ...

            app.add_url_rule('/', route)

        Arguments:
            rule: The path to route on, should start with a ``/``.
            endpoint: Optional endpoint name, if not present the
                function name is used.
            view_func: Callable that returns a response.
            provide_automatic_options: Optionally False to prevent
                OPTION handling.
            methods: List of HTTP verbs the function routes.
            defaults: A dictionary of variables to provide automatically, use
                to provide a simpler default path for a route, e.g. to allow
                for ``/book`` rather than ``/book/0``,

                .. code-block:: python

                    @app.route('/book', defaults={'page': 0})
                    @app.route('/book/<int:page>')
                    def book(page):
                        ...

            host: The full host name for this route (should include subdomain
                if needed) - cannot be used with subdomain.
            subdomain: A subdomain for this specific route.
            strict_slashes: Strictly match the trailing slash present in the
                path. Will redirect a leaf (no slash) to a branch (with slash).
            is_websocket: Whether or not the view_func is a websocket.
            merge_slashes: Merge consecutive slashes to a single slash (unless
                as part of the path variable).
        """
        raise NotImplementedError()

    def websocket(
        self,
        rule: str,
        endpoint: str | None = None,
        defaults: dict | None = None,
        host: str | None = None,
        subdomain: str | None = None,
        *,
        strict_slashes: bool | None = None,
    ) -> Callable[[T_websocket], T_websocket]:
        """Add a websocket to the application.

        This is designed to be used as a decorator, if used to
        decorate a synchronous function, the function will be wrapped
        in :func:`~quart.utils.run_sync` and run in a thread executor
        (with the wrapped function returned). An example usage,

        .. code-block:: python

            @app.websocket('/')
            async def websocket_route():
                ...

        Arguments:
            rule: The path to route on, should start with a ``/``.
            endpoint: Optional endpoint name, if not present the
                function name is used.
            defaults: A dictionary of variables to provide automatically, use
                to provide a simpler default path for a route, e.g. to allow
                for ``/book`` rather than ``/book/0``,

                .. code-block:: python

                    @app.websocket('/book', defaults={'page': 0})
                    @app.websocket('/book/<int:page>')
                    def book(page):
                        ...

            host: The full host name for this route (should include subdomain
                if needed) - cannot be used with subdomain.
            subdomain: A subdomain for this specific route.
            strict_slashes: Strictly match the trailing slash present in the
                path. Will redirect a leaf (no slash) to a branch (with slash).
        """

        def decorator(func: T_websocket) -> T_websocket:
            self.add_websocket(
                rule,
                endpoint,
                func,
                defaults=defaults,
                host=host,
                subdomain=subdomain,
                strict_slashes=strict_slashes,
            )
            return func

        return decorator

    def add_websocket(
        self,
        rule: str,
        endpoint: str | None = None,
        view_func: WebsocketCallable | None = None,
        defaults: dict | None = None,
        host: str | None = None,
        subdomain: str | None = None,
        *,
        strict_slashes: bool | None = None,
    ) -> None:
        """Add a websocket url rule to the application.

        This is designed to be used on the application directly. An
        example usage,

        .. code-block:: python

            def websocket_route():
                ...

            app.add_websocket('/', websocket_route)

        Arguments:
            rule: The path to route on, should start with a ``/``.
            endpoint: Optional endpoint name, if not present the
                function name is used.
            view_func: Callable that returns a response.
            defaults: A dictionary of variables to provide automatically, use
                to provide a simpler default path for a route, e.g. to allow
                for ``/book`` rather than ``/book/0``,

                .. code-block:: python

                    @app.websocket('/book', defaults={'page': 0})
                    @app.websocket('/book/<int:page>')
                    def book(page):
                        ...

            host: The full host name for this route (should include subdomain
                if needed) - cannot be used with subdomain.
            subdomain: A subdomain for this specific route.
            strict_slashes: Strictly match the trailing slash present in the
                path. Will redirect a leaf (no slash) to a branch (with slash).
        """
        return self.add_url_rule(
            rule,
            endpoint,
            view_func,
            methods={"GET"},
            defaults=defaults,
            host=host,
            subdomain=subdomain,
            provide_automatic_options=False,
            is_websocket=True,
            strict_slashes=strict_slashes,
        )

    @setupmethod
    def endpoint(self, endpoint: str) -> Callable[[F], F]:
        """Register a function as an endpoint.

        This is designed to be used as a decorator, if used to
        decorate a synchronous function, the function will be wrapped
        in :func:`~quart.utils.run_sync` and run in a thread executor
        (with the wrapped function returned). An example usage,

        .. code-block:: python

            @app.endpoint('name')
            async def endpoint():
                ...

        Arguments:
            endpoint: The endpoint name to use.
        """

        def decorator(func: F) -> F:
            self.view_functions[endpoint] = func
            return func

        return decorator

    @setupmethod
    def before_request(
        self,
        func: T_before_request,
    ) -> T_before_request:
        """Add a before request function.

        This is designed to be used as a decorator, if used to
        decorate a synchronous function, the function will be wrapped
        in :func:`~quart.utils.run_sync` and run in a thread executor
        (with the wrapped function returned). An example usage,

        .. code-block:: python

            @app.before_request
            async def func():
                ...

        Arguments:
            func: The before request function itself.
        """
        self.before_request_funcs[None].append(func)
        return func

    @setupmethod
    def after_request(
        self,
        func: T_after_request,
    ) -> T_after_request:
        """Add an after request function.

        This is designed to be used as a decorator, if used to
        decorate a synchronous function, the function will be wrapped
        in :func:`~quart.utils.run_sync` and run in a thread executor
        (with the wrapped function returned). An example usage,

        .. code-block:: python

            @app.after_request
            async def func(response):
                return response

        Arguments:
            func: The after request function itself.
        """
        self.after_request_funcs[None].append(func)
        return func

    @setupmethod
    def before_websocket(
        self,
        func: T_before_websocket,
    ) -> T_before_websocket:
        """Add a before websocket function.

        This is designed to be used as a decorator, if used to
        decorate a synchronous function, the function will be wrapped
        in :func:`~quart.utils.run_sync` and run in a thread executor
        (with the wrapped function returned). An example usage,

        .. code-block:: python

            @app.before_websocket
            async def func():
                ...

        Arguments:
            func: The before websocket function itself.
        """
        self.before_websocket_funcs[None].append(func)
        return func

    @setupmethod
    def after_websocket(
        self,
        func: T_after_websocket,
    ) -> T_after_websocket:
        """Add an after websocket function.

        This is designed to be used as a decorator, if used to
        decorate a synchronous function, the function will be wrapped
        in :func:`~quart.utils.run_sync` and run in a thread executor
        (with the wrapped function returned). An example usage,

        .. code-block:: python

            @app.after_websocket
            async def func(response):
                return response

        Arguments:
            func: The after websocket function itself.
        """
        self.after_websocket_funcs[None].append(func)
        return func

    @setupmethod
    def teardown_request(
        self,
        func: T_teardown,
    ) -> T_teardown:
        """Add a teardown request function.

        This is designed to be used as a decorator, if used to
        decorate a synchronous function, the function will be wrapped
        in :func:`~quart.utils.run_sync` and run in a thread executor
        (with the wrapped function returned). An example usage,

        .. code-block:: python

            @app.teardown_request
            async def func():
                ...

        Arguments:
            func: The teardown request function itself.
        """
        self.teardown_request_funcs[None].append(func)
        return func

    @setupmethod
    def teardown_websocket(
        self,
        func: T_teardown,
    ) -> T_teardown:
        """Add a teardown websocket function.

        This is designed to be used as a decorator, if used to
        decorate a synchronous function, the function will be wrapped
        in :func:`~quart.utils.run_sync` and run in a thread executor
        (with the wrapped function returned). An example usage,

        .. code-block:: python

            @app.teardown_websocket
            async def func():
                ...

        Arguments:
            func: The teardown websocket function itself.
            name: Optional blueprint key name.
        """
        self.teardown_websocket_funcs[None].append(func)
        return func

    @setupmethod
    def context_processor(
        self,
        func: T_template_context_processor,
    ) -> T_template_context_processor:
        """Add a template context processor.

        This is designed to be used as a decorator, if used to
        decorate a synchronous function, the function will be wrapped
        in :func:`~quart.utils.run_sync` and run in a thread executor
        (with the wrapped function returned). An example usage,

        .. code-block:: python

            @app.context_processor
            async def update_context(context):
                return context

        """
        self.template_context_processors[None].append(func)
        return func

    @setupmethod
    def url_value_preprocessor(
        self,
        func: T_url_value_preprocessor,
    ) -> T_url_value_preprocessor:
        """Add a url value preprocessor.

        This is designed to be used as a decorator. An example usage,

        .. code-block:: python

            @app.url_value_preprocessor
            def value_preprocessor(endpoint, view_args):
                ...
        """
        self.url_value_preprocessors[None].append(func)
        return func

    @setupmethod
    def url_defaults(self, func: T_url_defaults) -> T_url_defaults:
        """Add a url default preprocessor.

        This is designed to be used as a decorator. An example usage,

        .. code-block:: python

            @app.url_defaults
            def default(endpoint, values):
                ...
        """
        self.url_default_functions[None].append(func)
        return func

    @setupmethod
    def errorhandler(
        self, error: type[Exception] | int
    ) -> Callable[[T_error_handler], T_error_handler]:
        """Register a function as an error handler.

        This is designed to be used as a decorator. An example usage,

        .. code-block:: python

            @app.errorhandler(500)
            def error_handler():
                return "Error", 500

        Arguments:
            error: The error code or Exception to handle.
        """

        def decorator(func: T_error_handler) -> T_error_handler:
            self.register_error_handler(error, func)
            return func

        return decorator

    @setupmethod
    def register_error_handler(
        self,
        error: type[Exception] | int,
        func: ErrorHandlerCallable,
    ) -> None:
        """Register a function as an error handler.

        This is designed to be used on the application directly. An
        example usage,

        .. code-block:: python

            def error_handler():
                return "Error", 500

            app.register_error_handler(500, error_handler)

        Arguments:
            error: The error code or Exception to handle.
            func: The function to handle the error.
        """
        if isinstance(error, HTTPException):
            raise ValueError(
                "error must be an exception Type or int, not an instance of an exception"
            )

        try:
            error_type, code = self._get_error_type_and_code(error)
        except KeyError:
            raise KeyError(f"{error} is not a recognised HTTP error code or HTTPException subclass")

        handlers = self.error_handler_spec[None].setdefault(code, {})
        handlers[error_type] = func

    def _get_error_type_and_code(
        self, error: type[Exception] | int
    ) -> tuple[type[Exception], int | None]:
        error_type: type[Exception]
        if isinstance(error, int):
            error_type = default_exceptions[error]
        else:
            error_type = error

        if not issubclass(error_type, Exception):
            raise KeyError("Custom exceptions must be subclasses of Exception.")

        if issubclass(error_type, HTTPException):
            return error_type, error_type.code
        else:
            return error_type, None

    def _check_setup_finished(self, f_name: str) -> None:
        raise NotImplementedError()


def _endpoint_from_view_func(view_func: Callable) -> str:
    assert view_func is not None
    return view_func.__name__
