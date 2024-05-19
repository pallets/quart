from __future__ import annotations

import asyncio
import os
import signal
import sys
import warnings
from collections import defaultdict
from datetime import timedelta
from inspect import isasyncgen, isgenerator
from types import TracebackType
from typing import (
    Any,
    AnyStr,
    AsyncGenerator,
    Awaitable,
    Callable,
    cast,
    Coroutine,
    NoReturn,
    Optional,
    overload,
    Set,
    TypeVar,
    Union,
)
from urllib.parse import quote

from aiofiles import open as async_open
from aiofiles.base import AiofilesContextManager
from aiofiles.threadpool.binary import AsyncBufferedReader
from flask.sansio.app import App
from flask.sansio.scaffold import setupmethod
from hypercorn.asyncio import serve
from hypercorn.config import Config as HyperConfig
from hypercorn.typing import ASGIReceiveCallable, ASGISendCallable, Scope
from werkzeug.datastructures import Authorization, Headers, ImmutableDict
from werkzeug.exceptions import Aborter, BadRequestKeyError, HTTPException, InternalServerError
from werkzeug.routing import BuildError, MapAdapter, RoutingException
from werkzeug.wrappers import Response as WerkzeugResponse

from .asgi import ASGIHTTPConnection, ASGILifespan, ASGIWebsocketConnection
from .cli import AppGroup
from .config import Config
from .ctx import (
    _AppCtxGlobals,
    AppContext,
    has_request_context,
    has_websocket_context,
    RequestContext,
    WebsocketContext,
)
from .globals import (
    _cv_app,
    _cv_request,
    _cv_websocket,
    g,
    request,
    request_ctx,
    session,
    websocket,
    websocket_ctx,
)
from .helpers import get_debug_flag, get_flashed_messages, send_from_directory
from .routing import QuartMap, QuartRule
from .sessions import SecureCookieSessionInterface
from .signals import (
    appcontext_tearing_down,
    got_background_exception,
    got_request_exception,
    got_serving_exception,
    got_websocket_exception,
    request_finished,
    request_started,
    request_tearing_down,
    websocket_finished,
    websocket_started,
    websocket_tearing_down,
)
from .templating import _default_template_ctx_processor, Environment
from .testing import (
    make_test_body_with_headers,
    make_test_headers_path_and_query_string,
    make_test_scope,
    no_op_push,
    QuartClient,
    QuartCliRunner,
    sentinel,
    TestApp,
)
from .typing import (
    AfterServingCallable,
    AfterWebsocketCallable,
    ASGIHTTPProtocol,
    ASGILifespanProtocol,
    ASGIWebsocketProtocol,
    BeforeServingCallable,
    BeforeWebsocketCallable,
    Event,
    FilePath,
    HeadersValue,
    ResponseReturnValue,
    ResponseTypes,
    ShellContextProcessorCallable,
    StatusCode,
    TeardownCallable,
    TemplateFilterCallable,
    TemplateGlobalCallable,
    TemplateTestCallable,
    TestAppProtocol,
    TestClientProtocol,
    WebsocketCallable,
    WhileServingCallable,
)
from .utils import (
    cancel_tasks,
    file_path_to_path,
    MustReloadError,
    observe_changes,
    restart,
    run_sync,
)
from .wrappers import BaseRequestWebsocket, Request, Response, Websocket

try:
    from typing import ParamSpec
except ImportError:
    from typing_extensions import ParamSpec  # type: ignore

AppOrBlueprintKey = Optional[str]  # The App key is None, whereas blueprints are named
T_after_serving = TypeVar("T_after_serving", bound=AfterServingCallable)
T_after_websocket = TypeVar("T_after_websocket", bound=AfterWebsocketCallable)
T_before_serving = TypeVar("T_before_serving", bound=BeforeServingCallable)
T_before_websocket = TypeVar("T_before_websocket", bound=BeforeWebsocketCallable)
T_shell_context_processor = TypeVar(
    "T_shell_context_processor", bound=ShellContextProcessorCallable
)
T_teardown = TypeVar("T_teardown", bound=TeardownCallable)
T_template_filter = TypeVar("T_template_filter", bound=TemplateFilterCallable)
T_template_global = TypeVar("T_template_global", bound=TemplateGlobalCallable)
T_template_test = TypeVar("T_template_test", bound=TemplateTestCallable)
T_websocket = TypeVar("T_websocket", bound=WebsocketCallable)
T_while_serving = TypeVar("T_while_serving", bound=WhileServingCallable)

T = TypeVar("T")
P = ParamSpec("P")


def _make_timedelta(value: timedelta | int | None) -> timedelta | None:
    if value is None or isinstance(value, timedelta):
        return value

    return timedelta(seconds=value)


class Quart(App):
    """The web framework class, handles requests and returns responses.

    The primary method from a serving viewpoint is
    :meth:`~quart.app.Quart.handle_request`, from an application
    viewpoint all the other methods are vital.

    This can be extended in many ways, with most methods designed with
    this in mind. Additionally any of the classes listed as attributes
    can be replaced.

    Attributes:
        aborter_class: The class to use to raise HTTP error via the abort
            helper function.
        app_ctx_globals_class: The class to use for the ``g`` object
        asgi_http_class: The class to use to handle the ASGI HTTP
            protocol.
        asgi_lifespan_class: The class to use to handle the ASGI
            lifespan protocol.
        asgi_websocket_class: The class to use to handle the ASGI
            websocket protocol.
        config_class: The class to use for the configuration.
        env: The name of the environment the app is running on.
        event_class: The class to use to signal an event in an async
            manner.
        debug: Wrapper around configuration DEBUG value, in many places
            this will result in more output if True. If unset, debug
            mode will be activated if environ is set to 'development'.
        jinja_environment: The class to use for the jinja environment.
        jinja_options: The default options to set when creating the jinja
            environment.
        permanent_session_lifetime: Wrapper around configuration
            PERMANENT_SESSION_LIFETIME value. Specifies how long the session
            data should survive.
        request_class: The class to use for requests.
        response_class: The class to user for responses.
        secret_key: Warpper around configuration SECRET_KEY value. The app
            secret for signing sessions.
        session_interface: The class to use as the session interface.
        shutdown_event: This event is set when the app starts to
            shutdown allowing waiting tasks to know when to stop.
        url_map_class: The class to map rules to endpoints.
        url_rule_class: The class to use for URL rules.
        websocket_class: The class to use for websockets.

    """

    asgi_http_class: type[ASGIHTTPProtocol]
    asgi_lifespan_class: type[ASGILifespanProtocol]
    asgi_websocket_class: type[ASGIWebsocketProtocol]
    shutdown_event: Event
    test_app_class: type[TestAppProtocol]
    test_client_class: type[TestClientProtocol]  # type: ignore[assignment]

    aborter_class = Aborter
    app_ctx_globals_class = _AppCtxGlobals
    asgi_http_class = ASGIHTTPConnection
    asgi_lifespan_class = ASGILifespan
    asgi_websocket_class = ASGIWebsocketConnection
    config_class = Config
    event_class = asyncio.Event
    jinja_environment = Environment  # type: ignore[assignment]
    lock_class = asyncio.Lock
    request_class = Request
    response_class = Response
    session_interface = SecureCookieSessionInterface()
    test_app_class = TestApp
    test_client_class = QuartClient  # type: ignore[assignment]
    test_cli_runner_class = QuartCliRunner  # type: ignore
    url_map_class = QuartMap
    url_rule_class = QuartRule  # type: ignore[assignment]
    websocket_class = Websocket

    default_config = ImmutableDict(
        {
            "APPLICATION_ROOT": "/",
            "BACKGROUND_TASK_SHUTDOWN_TIMEOUT": 5,  # Second
            "BODY_TIMEOUT": 60,  # Second
            "DEBUG": None,
            "ENV": None,
            "EXPLAIN_TEMPLATE_LOADING": False,
            "MAX_CONTENT_LENGTH": 16 * 1024 * 1024,  # 16 MB Limit
            "MAX_COOKIE_SIZE": 4093,
            "PERMANENT_SESSION_LIFETIME": timedelta(days=31),
            # Replaces PREFERRED_URL_SCHEME to allow for WebSocket scheme
            "PREFER_SECURE_URLS": False,
            "PRESERVE_CONTEXT_ON_EXCEPTION": None,
            "PROPAGATE_EXCEPTIONS": None,
            "RESPONSE_TIMEOUT": 60,  # Second
            "SECRET_KEY": None,
            "SEND_FILE_MAX_AGE_DEFAULT": timedelta(hours=12),
            "SERVER_NAME": None,
            "SESSION_COOKIE_DOMAIN": None,
            "SESSION_COOKIE_HTTPONLY": True,
            "SESSION_COOKIE_NAME": "session",
            "SESSION_COOKIE_PATH": None,
            "SESSION_COOKIE_SAMESITE": None,
            "SESSION_COOKIE_SECURE": False,
            "SESSION_REFRESH_EACH_REQUEST": True,
            "TEMPLATES_AUTO_RELOAD": None,
            "TESTING": False,
            "TRAP_BAD_REQUEST_ERRORS": None,
            "TRAP_HTTP_EXCEPTIONS": False,
        }
    )

    def __init__(
        self,
        import_name: str,
        static_url_path: str | None = None,
        static_folder: str | None = "static",
        static_host: str | None = None,
        host_matching: bool = False,
        subdomain_matching: bool = False,
        template_folder: str | None = "templates",
        instance_path: str | None = None,
        instance_relative_config: bool = False,
        root_path: str | None = None,
    ) -> None:
        """Construct a Quart web application.

        Use to create a new web application to which requests should
        be handled, as specified by the various attached url
        rules. See also :class:`~quart.static.PackageStatic` for
        additional constructor arguments.

        Arguments:
            import_name: The name at import of the application, use
                ``__name__`` unless there is a specific issue.
            host_matching: Optionally choose to match the host to the
                configured host on request (404 if no match).
            instance_path: Optional path to an instance folder, for
                deployment specific settings and files.
            instance_relative_config: If True load the config from a
                path relative to the instance path.
        Attributes:
            after_request_funcs: The functions to execute after a
                request has been handled.
            after_websocket_funcs: The functions to execute after a
                websocket has been handled.
            before_request_funcs: The functions to execute before handling
                a request.
            before_websocket_funcs: The functions to execute before handling
                a websocket.
        """
        super().__init__(
            import_name,
            static_url_path,
            static_folder,
            static_host,
            host_matching,
            subdomain_matching,
            template_folder,
            instance_path,
            instance_relative_config,
            root_path,
        )

        self.after_serving_funcs: list[Callable[[], Awaitable[None]]] = []
        self.after_websocket_funcs: dict[AppOrBlueprintKey, list[AfterWebsocketCallable]] = (
            defaultdict(list)
        )
        self.background_tasks: Set[asyncio.Task] = set()
        self.before_serving_funcs: list[Callable[[], Awaitable[None]]] = []
        self.before_websocket_funcs: dict[AppOrBlueprintKey, list[BeforeWebsocketCallable]] = (
            defaultdict(list)
        )
        self.teardown_websocket_funcs: dict[AppOrBlueprintKey, list[TeardownCallable]] = (
            defaultdict(list)
        )
        self.while_serving_gens: list[AsyncGenerator[None, None]] = []

        self.template_context_processors[None] = [_default_template_ctx_processor]

        self.cli = AppGroup()
        self.cli.name = self.name

        if self.has_static_folder:
            assert (
                bool(static_host) == host_matching
            ), "Invalid static_host/host_matching combination"

            self.add_url_rule(
                f"{self.static_url_path}/<path:filename>",
                "static",
                self.send_static_file,
                host=static_host,
            )

    def get_send_file_max_age(self, filename: str | None) -> int | None:
        """Used by :func:`send_file` to determine the ``max_age`` cache
        value for a given file path if it wasn't passed.

        By default, this returns :data:`SEND_FILE_MAX_AGE_DEFAULT` from
        the configuration of :data:`~flask.current_app`. This defaults
        to ``None``, which tells the browser to use conditional requests
        instead of a timed cache, which is usually preferable.

        Note this is a duplicate of the same method in the Quart
        class.

        """
        value = self.config["SEND_FILE_MAX_AGE_DEFAULT"]

        if value is None:
            return None

        if isinstance(value, timedelta):
            return int(value.total_seconds())

        return value
        return None

    async def send_static_file(self, filename: str) -> Response:
        if not self.has_static_folder:
            raise RuntimeError("No static folder for this object")
        return await send_from_directory(self.static_folder, filename)

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
        if mode not in {"r", "rb", "rt"}:
            raise ValueError("Files can only be opened for reading")

        return async_open(os.path.join(self.root_path, path), mode)  # type: ignore

    async def open_instance_resource(
        self, path: FilePath, mode: str = "rb"
    ) -> AiofilesContextManager[None, None, AsyncBufferedReader]:
        """Open a file for reading.

        Use as

        .. code-block:: python

            async with await app.open_instance_resource(path) as file_:
                await file_.read()
        """
        return async_open(self.instance_path / file_path_to_path(path), mode)  # type: ignore

    def create_jinja_environment(self) -> Environment:  # type: ignore
        """Create and return the jinja environment.

        This will create the environment based on the
        :attr:`jinja_options` and configuration settings. The
        environment will include the Quart globals by default.
        """
        options = dict(self.jinja_options)
        if "autoescape" not in options:
            options["autoescape"] = self.select_jinja_autoescape
        if "auto_reload" not in options:
            options["auto_reload"] = self.config["TEMPLATES_AUTO_RELOAD"]
        jinja_env = self.jinja_environment(self, **options)  # type: ignore
        jinja_env.globals.update(
            {
                "config": self.config,
                "g": g,
                "get_flashed_messages": get_flashed_messages,
                "request": request,
                "session": session,
                "url_for": self.url_for,
            }
        )
        jinja_env.policies["json.dumps_function"] = self.json.dumps
        return jinja_env

    async def update_template_context(self, context: dict) -> None:
        """Update the provided template context.

        This adds additional context from the various template context
        processors.

        Arguments:
            context: The context to update (mutate).
        """
        names = [None]
        if has_request_context():
            names.extend(reversed(request_ctx.request.blueprints))  # type: ignore
        elif has_websocket_context():
            names.extend(reversed(websocket_ctx.websocket.blueprints))  # type: ignore

        extra_context: dict = {}
        for name in names:
            for processor in self.template_context_processors[name]:
                extra_context.update(await self.ensure_async(processor)())  # type: ignore

        original = context.copy()
        context.update(extra_context)
        context.update(original)

    @setupmethod
    def before_serving(
        self,
        func: T_before_serving,
    ) -> T_before_serving:
        """Add a before serving function.

        This will allow the function provided to be called once before
        anything is served (before any byte is received).

        This is designed to be used as a decorator, if used to
        decorate a synchronous function, the function will be wrapped
        in :func:`~quart.utils.run_sync` and run in a thread executor
        (with the wrapped function returned). An example usage,

        .. code-block:: python

            @app.before_serving
            async def func():
                ...

        Arguments:
            func: The function itself.
        """
        self.before_serving_funcs.append(func)
        return func

    @setupmethod
    def while_serving(
        self,
        func: T_while_serving,
    ) -> T_while_serving:
        """Add a while serving generator function.

        This will allow the generator provided to be invoked at
        startup and then again at shutdown.

        This is designed to be used as a decorator. An example usage,

        .. code-block:: python

            @app.while_serving
            async def func():
                ...  # Startup
                yield
                ...  # Shutdown

        Arguments:
            func: The function itself.

        """
        self.while_serving_gens.append(func())
        return func

    @setupmethod
    def after_serving(
        self,
        func: T_after_serving,
    ) -> T_after_serving:
        """Add a after serving function.

        This will allow the function provided to be called once after
        anything is served (after last byte is sent).

        This is designed to be used as a decorator, if used to
        decorate a synchronous function, the function will be wrapped
        in :func:`~quart.utils.run_sync` and run in a thread executor
        (with the wrapped function returned). An example usage,

        .. code-block:: python

            @app.after_serving
            async def func():
                ...

        Arguments:
            func: The function itself.
        """
        self.after_serving_funcs.append(func)
        return func

    def create_url_adapter(self, request: BaseRequestWebsocket | None) -> MapAdapter | None:
        """Create and return a URL adapter.

        This will create the adapter based on the request if present
        otherwise the app configuration.
        """
        if request is not None:
            subdomain = (
                (self.url_map.default_subdomain or None) if not self.subdomain_matching else None
            )

            return self.url_map.bind_to_request(  # type: ignore[attr-defined]
                request, subdomain, self.config["SERVER_NAME"]
            )

        if self.config["SERVER_NAME"] is not None:
            scheme = "https" if self.config["PREFER_SECURE_URLS"] else "http"
            return self.url_map.bind(self.config["SERVER_NAME"], url_scheme=scheme)
        return None

    def websocket(
        self,
        rule: str,
        **options: Any,
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
            endpoint = options.pop("endpoint", None)
            self.add_websocket(
                rule,
                endpoint,
                func,
                **options,
            )
            return func

        return decorator

    def add_websocket(
        self,
        rule: str,
        endpoint: str | None = None,
        view_func: WebsocketCallable | None = None,
        **options: Any,
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
            websocket=True,
            **options,
        )

    def url_for(
        self,
        endpoint: str,
        *,
        _anchor: str | None = None,
        _external: bool | None = None,
        _method: str | None = None,
        _scheme: str | None = None,
        **values: Any,
    ) -> str:
        """Return the url for a specific endpoint.

        This is most useful in templates and redirects to create a URL
        that can be used in the browser.

        Arguments:
            endpoint: The endpoint to build a url for, if prefixed with
                ``.`` it targets endpoint's in the current blueprint.
            _anchor: Additional anchor text to append (i.e. #text).
            _external: Return an absolute url for external (to app) usage.
            _method: The method to consider alongside the endpoint.
            _scheme: A specific scheme to use.
            values: The values to build into the URL, as specified in
                the endpoint rule.
        """

        app_context = _cv_app.get(None)
        request_context = _cv_request.get(None)
        websocket_context = _cv_websocket.get(None)

        if request_context is not None:
            url_adapter = request_context.url_adapter
            if endpoint.startswith("."):
                if request.blueprint is not None:
                    endpoint = request.blueprint + endpoint
                else:
                    endpoint = endpoint[1:]
            if _external is None:
                _external = _scheme is not None
        elif websocket_context is not None:
            url_adapter = websocket_context.url_adapter
            if endpoint.startswith("."):
                if websocket.blueprint is not None:
                    endpoint = websocket.blueprint + endpoint
                else:
                    endpoint = endpoint[1:]
            if _external is None:
                _external = _scheme is not None
        elif app_context is not None:
            url_adapter = app_context.url_adapter
            if _external is None:
                _external = True
        else:
            url_adapter = self.create_url_adapter(None)
            if _external is None:
                _external = True

        if url_adapter is None:
            raise RuntimeError(
                "Unable to create a url adapter, try setting the SERVER_NAME config variable."
            )
        if _scheme is not None and not _external:
            raise ValueError("External must be True for scheme usage")

        self.inject_url_defaults(endpoint, values)

        old_scheme = None
        if _scheme is not None:
            old_scheme = url_adapter.url_scheme
            url_adapter.url_scheme = _scheme

        try:
            url = url_adapter.build(endpoint, values, method=_method, force_external=_external)
        except BuildError as error:
            return self.handle_url_build_error(error, endpoint, values)
        finally:
            if old_scheme is not None:
                url_adapter.url_scheme = old_scheme

        if _anchor is not None:
            quoted_anchor = quote(_anchor, safe="%!#$&'()*+,/:;=?@")
            url = f"{url}#{quoted_anchor}"
        return url

    def make_shell_context(self) -> dict:
        """Create a context for interactive shell usage.

        The :attr:`shell_context_processors` can be used to add
        additional context.
        """
        context = {"app": self, "g": g}
        for processor in self.shell_context_processors:
            context.update(processor())
        return context

    def run(
        self,
        host: str | None = None,
        port: int | None = None,
        debug: bool | None = None,
        use_reloader: bool = True,
        loop: asyncio.AbstractEventLoop | None = None,
        ca_certs: str | None = None,
        certfile: str | None = None,
        keyfile: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Run this application.

        This is best used for development only, see Hypercorn for
        production servers.

        Arguments:
            host: Hostname to listen on. By default this is loopback
                only, use 0.0.0.0 to have the server listen externally.
            port: Port number to listen on.
            debug: If set enable (or disable) debug mode and debug output.
            use_reloader: Automatically reload on code changes.
            loop: Asyncio loop to create the server in, if None, take default one.
                If specified it is the caller's responsibility to close and cleanup the
                loop.
            ca_certs: Path to the SSL CA certificate file.
            certfile: Path to the SSL certificate file.
            keyfile: Path to the SSL key file.
        """
        if kwargs:
            warnings.warn(
                f"Additional arguments, {','.join(kwargs.keys())}, are not supported.\n"
                "They may be supported by Hypercorn, which is the ASGI server Quart "
                "uses by default. This method is meant for development and debugging.",
                stacklevel=2,
            )

        if loop is None:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        if "QUART_DEBUG" in os.environ:
            self.debug = get_debug_flag()

        if debug is not None:
            self.debug = debug

        loop.set_debug(self.debug)

        shutdown_event = asyncio.Event()

        def _signal_handler(*_: Any) -> None:
            shutdown_event.set()

        for signal_name in {"SIGINT", "SIGTERM", "SIGBREAK"}:
            if hasattr(signal, signal_name):
                try:
                    loop.add_signal_handler(getattr(signal, signal_name), _signal_handler)
                except NotImplementedError:
                    # Add signal handler may not be implemented on Windows
                    signal.signal(getattr(signal, signal_name), _signal_handler)

        server_name = self.config.get("SERVER_NAME")
        sn_host = None
        sn_port = None
        if server_name is not None:
            sn_host, _, sn_port = server_name.partition(":")

        if host is None:
            host = sn_host or "127.0.0.1"

        if port is None:
            port = int(sn_port or "5000")

        task = self.run_task(
            host,
            port,
            debug,
            ca_certs,
            certfile,
            keyfile,
            shutdown_trigger=shutdown_event.wait,  # type: ignore
        )
        print(f" * Serving Quart app '{self.name}'")  # noqa: T201
        print(f" * Debug mode: {self.debug or False}")  # noqa: T201
        print(" * Please use an ASGI server (e.g. Hypercorn) directly in production")  # noqa: T201
        scheme = "https" if certfile is not None and keyfile is not None else "http"
        print(f" * Running on {scheme}://{host}:{port} (CTRL + C to quit)")  # noqa: T201

        tasks = [loop.create_task(task)]

        if use_reloader:
            tasks.append(loop.create_task(observe_changes(asyncio.sleep, shutdown_event)))

        reload_ = False
        try:
            loop.run_until_complete(asyncio.gather(*tasks))
        except MustReloadError:
            reload_ = True
        finally:
            try:
                _cancel_all_tasks(loop)
                loop.run_until_complete(loop.shutdown_asyncgens())
            finally:
                asyncio.set_event_loop(None)
                loop.close()

        if reload_:
            restart()

    def run_task(
        self,
        host: str = "127.0.0.1",
        port: int = 5000,
        debug: bool | None = None,
        ca_certs: str | None = None,
        certfile: str | None = None,
        keyfile: str | None = None,
        shutdown_trigger: Callable[..., Awaitable[None]] | None = None,
    ) -> Coroutine[None, None, None]:
        """Return a task that when awaited runs this application.

        This is best used for development only, see Hypercorn for
        production servers.

        Arguments:
            host: Hostname to listen on. By default this is loopback
                only, use 0.0.0.0 to have the server listen externally.
            port: Port number to listen on.
            debug: If set enable (or disable) debug mode and debug output.
            ca_certs: Path to the SSL CA certificate file.
            certfile: Path to the SSL certificate file.
            keyfile: Path to the SSL key file.

        """
        config = HyperConfig()
        config.access_log_format = "%(h)s %(r)s %(s)s %(b)s %(D)s"
        config.accesslog = "-"
        config.bind = [f"{host}:{port}"]
        config.ca_certs = ca_certs
        config.certfile = certfile
        if debug is not None:
            self.debug = debug
        config.errorlog = config.accesslog
        config.keyfile = keyfile

        return serve(self, config, shutdown_trigger=shutdown_trigger)

    def test_client(self, use_cookies: bool = True, **kwargs: Any) -> TestClientProtocol:
        """Creates and returns a test client."""
        return self.test_client_class(self, use_cookies=use_cookies, **kwargs)

    def test_cli_runner(self, **kwargs: Any) -> QuartCliRunner:
        """Creates and returns a CLI test runner."""
        return self.test_cli_runner_class(self, **kwargs)  # type: ignore

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
        """
        self.teardown_websocket_funcs[None].append(func)
        return func

    async def handle_http_exception(
        self, error: HTTPException
    ) -> HTTPException | ResponseReturnValue:
        """Handle a HTTPException subclass error.

        This will attempt to find a handler for the error and if fails
        will fall back to the error response.
        """
        if error.code is None:
            return error

        if isinstance(error, RoutingException):
            return error

        blueprints = []
        if has_request_context():
            blueprints = request.blueprints
        elif has_websocket_context():
            blueprints = websocket.blueprints

        handler = self._find_error_handler(error, blueprints)
        if handler is None:
            return error
        else:
            return await self.ensure_async(handler)(error)  # type: ignore

    async def handle_user_exception(self, error: Exception) -> HTTPException | ResponseReturnValue:
        """Handle an exception that has been raised.

        This should forward :class:`~quart.exception.HTTPException` to
        :meth:`handle_http_exception`, then attempt to handle the
        error. If it cannot it should reraise the error.
        """
        if isinstance(error, BadRequestKeyError) and (
            self.debug or self.config["TRAP_BAD_REQUEST_ERRORS"]
        ):
            error.show_exception = True

        if isinstance(error, HTTPException) and not self.trap_http_exception(error):
            return await self.handle_http_exception(error)

        blueprints = []
        if has_request_context():
            blueprints = request.blueprints
        elif has_websocket_context():
            blueprints = websocket.blueprints

        handler = self._find_error_handler(error, blueprints)
        if handler is None:
            raise error
        return await self.ensure_async(handler)(error)  # type: ignore

    async def handle_exception(self, error: Exception) -> ResponseTypes:
        """Handle an uncaught exception.

        By default this switches the error response to a 500 internal
        server error.
        """
        exc_info = sys.exc_info()
        await got_request_exception.send_async(
            self, _sync_wrapper=self.ensure_async, exception=error  # type: ignore
        )
        propagate = self.config["PROPAGATE_EXCEPTIONS"]

        if propagate is None:
            propagate = self.testing or self.debug

        if propagate:
            # Re-raise if called with an active exception, otherwise
            # raise the passed in exception.
            if exc_info[1] is error:
                raise

            raise error

        self.log_exception(exc_info)
        server_error: InternalServerError | ResponseReturnValue
        server_error = InternalServerError(original_exception=error)
        handler = self._find_error_handler(server_error, request.blueprints)

        if handler is not None:
            server_error = await self.ensure_async(handler)(server_error)  # type: ignore

        return await self.finalize_request(server_error, from_error_handler=True)

    async def handle_websocket_exception(self, error: Exception) -> ResponseTypes | None:
        """Handle an uncaught exception.

        By default this logs the exception and then re-raises it.
        """
        exc_info = sys.exc_info()
        await got_websocket_exception.send_async(
            self, _sync_wrapper=self.ensure_async, exception=error  # type: ignore
        )
        propagate = self.config["PROPAGATE_EXCEPTIONS"]

        if propagate is None:
            propagate = self.testing or self.debug

        if propagate:
            # Re-raise if called with an active exception, otherwise
            # raise the passed in exception.
            if exc_info[1] is error:
                raise

            raise error

        self.log_exception(exc_info)
        server_error: InternalServerError | ResponseReturnValue
        server_error = InternalServerError(original_exception=error)
        handler = self._find_error_handler(server_error, websocket.blueprints)

        if handler is not None:
            server_error = await self.ensure_async(handler)(server_error)  # type: ignore

        return await self.finalize_websocket(server_error, from_error_handler=True)

    def log_exception(
        self,
        exception_info: tuple[type, BaseException, TracebackType] | tuple[None, None, None],
    ) -> None:
        """Log a exception to the :attr:`logger`.

        By default this is only invoked for unhandled exceptions.
        """
        if has_request_context():
            request_ = request_ctx.request
            self.logger.error(
                f"Exception on request {request_.method} {request_.path}", exc_info=exception_info
            )
        elif has_websocket_context():
            websocket_ = websocket_ctx.websocket
            self.logger.error(f"Exception on websocket {websocket_.path}", exc_info=exception_info)
        else:
            self.logger.error("Exception", exc_info=exception_info)

    @overload
    def ensure_async(self, func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]: ...

    @overload
    def ensure_async(self, func: Callable[P, T]) -> Callable[P, Awaitable[T]]: ...

    def ensure_async(
        self, func: Union[Callable[P, Awaitable[T]], Callable[P, T]]
    ) -> Callable[P, Awaitable[T]]:
        """Ensure that the returned func is async and calls the func.

        .. versionadded:: 0.11

        Override if you wish to change how synchronous functions are
        run. Before Quart 0.11 this did not run the synchronous code
        in an executor.
        """
        if asyncio.iscoroutinefunction(func):
            return func
        else:
            return self.sync_to_async(cast(Callable[P, T], func))

    def sync_to_async(self, func: Callable[P, T]) -> Callable[P, Awaitable[T]]:
        """Return a async function that will run the synchronous function *func*.

        This can be used as so,::

            result = await app.sync_to_async(func)(*args, **kwargs)

        Override this method to change how the app converts sync code
        to be asynchronously callable.
        """
        return run_sync(func)

    async def do_teardown_request(
        self, exc: BaseException | None, request_context: RequestContext | None = None
    ) -> None:
        """Teardown the request, calling the teardown functions.

        Arguments:
            exc: Any exception not handled that has caused the request
                to teardown.
            request_context: The request context, optional as Flask
                omits this argument.
        """
        names = [*(request_context or request_ctx).request.blueprints, None]
        for name in names:
            for function in reversed(self.teardown_request_funcs[name]):
                await self.ensure_async(function)(exc)

        await request_tearing_down.send_async(
            self, _sync_wrapper=self.ensure_async, exc=exc  # type: ignore
        )

    async def do_teardown_websocket(
        self, exc: BaseException | None, websocket_context: WebsocketContext | None = None
    ) -> None:
        """Teardown the websocket, calling the teardown functions.

        Arguments:
            exc: Any exception not handled that has caused the websocket
                to teardown.
            websocket_context: The websocket context, optional as Flask
                omits this argument.
        """
        names = [*(websocket_context or websocket_ctx).websocket.blueprints, None]
        for name in names:
            for function in reversed(self.teardown_websocket_funcs[name]):
                await self.ensure_async(function)(exc)

        await websocket_tearing_down.send_async(
            self, _sync_wrapper=self.ensure_async, exc=exc  # type: ignore
        )

    async def do_teardown_appcontext(self, exc: BaseException | None) -> None:
        """Teardown the app (context), calling the teardown functions."""
        for function in self.teardown_appcontext_funcs:
            await self.ensure_async(function)(exc)
        await appcontext_tearing_down.send_async(
            self, _sync_wrapper=self.ensure_async, exc=exc  # type: ignore
        )

    def app_context(self) -> AppContext:
        """Create and return an app context.

        This is best used within a context, i.e.

        .. code-block:: python

            async with app.app_context():
                ...
        """
        return AppContext(self)

    def request_context(self, request: Request) -> RequestContext:
        """Create and return a request context.

        Use the :meth:`test_request_context` whilst testing. This is
        best used within a context, i.e.

        .. code-block:: python

            async with app.request_context(request):
                ...

        Arguments:
            request: A request to build a context around.
        """
        return RequestContext(self, request)

    def websocket_context(self, websocket: Websocket) -> WebsocketContext:
        """Create and return a websocket context.

        Use the :meth:`test_websocket_context` whilst testing. This is
        best used within a context, i.e.

        .. code-block:: python

            async with app.websocket_context(websocket):
                ...

        Arguments:
            websocket: A websocket to build a context around.
        """
        return WebsocketContext(self, websocket)

    def test_app(self) -> TestAppProtocol:
        return self.test_app_class(self)

    def test_request_context(
        self,
        path: str,
        *,
        method: str = "GET",
        headers: dict | Headers | None = None,
        query_string: dict | None = None,
        scheme: str = "http",
        send_push_promise: Callable[[str, Headers], Awaitable[None]] = no_op_push,
        data: AnyStr | None = None,
        form: dict | None = None,
        json: Any = sentinel,
        root_path: str = "",
        http_version: str = "1.1",
        scope_base: dict | None = None,
        auth: Authorization | tuple[str, str] | None = None,
        subdomain: str | None = None,
    ) -> RequestContext:
        """Create a request context for testing purposes.

        This is best used for testing code within request contexts. It
        is a simplified wrapper of :meth:`request_context`. It is best
        used in a with block, i.e.

        .. code-block:: python

            async with app.test_request_context("/", method="GET"):
                ...

        Arguments:
            path: Request path.
            method: HTTP verb
            headers: Headers to include in the request.
            query_string: To send as a dictionary, alternatively the
                query_string can be determined from the path.
            scheme: Scheme for the request, default http.
        """
        headers, path, query_string_bytes = make_test_headers_path_and_query_string(
            self,
            path,
            headers,
            query_string,
            auth,
            subdomain,
        )
        request_body, body_headers = make_test_body_with_headers(data=data, form=form, json=json)
        headers.update(**body_headers)
        scope = make_test_scope(
            "http",
            path,
            method,
            headers,
            query_string_bytes,
            scheme,
            root_path,
            http_version,
            scope_base,
        )
        request = self.request_class(
            method,
            scheme,
            path,
            query_string_bytes,
            headers,
            root_path,
            http_version,
            send_push_promise=send_push_promise,
            scope=scope,
        )
        request.body.set_result(request_body)
        return self.request_context(request)

    def add_background_task(self, func: Callable, *args: Any, **kwargs: Any) -> None:
        async def _wrapper() -> None:
            try:
                async with self.app_context():
                    await self.ensure_async(func)(*args, **kwargs)
            except Exception as error:
                await self.handle_background_exception(error)

        task = asyncio.get_event_loop().create_task(_wrapper())
        self.background_tasks.add(task)
        task.add_done_callback(self.background_tasks.discard)

    async def handle_background_exception(self, error: Exception) -> None:
        await got_background_exception.send_async(
            self, _sync_wrapper=self.ensure_async, exception=error  # type: ignore
        )

        self.log_exception(sys.exc_info())

    async def make_default_options_response(self) -> Response:
        """This is the default route function for OPTIONS requests."""
        methods = request_ctx.url_adapter.allowed_methods()
        return self.response_class("", headers={"Allow": ", ".join(methods)})

    async def make_response(self, result: ResponseReturnValue | HTTPException) -> ResponseTypes:
        """Make a Response from the result of the route handler.

        The result itself can either be:
          - A Response object (or subclass).
          - A tuple of a ResponseValue and a header dictionary.
          - A tuple of a ResponseValue, status code and a header dictionary.

        A ResponseValue is either a Response object (or subclass) or a str.
        """
        headers: HeadersValue | None = None
        status: StatusCode | None = None
        if isinstance(result, tuple):
            if len(result) == 3:
                value, status, headers = result
            elif len(result) == 2:
                value, status_or_headers = result

                if isinstance(status_or_headers, (Headers, dict, list)):
                    headers = status_or_headers
                    status = None
                elif status_or_headers is not None:
                    status = status_or_headers  # type: ignore[assignment]
            else:
                raise TypeError(
                    """The response value returned must be either (body, status), (body,
                    headers), or (body, status, headers)"""
                )
        else:
            value = result  # type: ignore[assignment]

        if value is None:
            raise TypeError("The response value returned by the view function cannot be None")

        response: ResponseTypes
        if isinstance(value, HTTPException):
            response = value.get_response()  # type: ignore
        elif not isinstance(value, (Response, WerkzeugResponse)):
            if (
                isinstance(value, (str, bytes, bytearray))
                or isgenerator(value)
                or isasyncgen(value)
            ):
                response = self.response_class(value)
            elif isinstance(value, (list, dict)):
                response = self.json.response(value)  # type: ignore[assignment]
            else:
                raise TypeError(f"The response value type ({type(value).__name__}) is not valid")
        else:
            response = value

        if status is not None:
            response.status_code = int(status)

        if headers is not None:
            response.headers.update(headers)  # type: ignore[arg-type]

        return response

    async def handle_request(self, request: Request) -> ResponseTypes:
        async with self.request_context(request) as request_context:
            try:
                return await self.full_dispatch_request(request_context)
            except asyncio.CancelledError:
                raise  # CancelledErrors should be handled by serving code.
            except Exception as error:
                return await self.handle_exception(error)
            finally:
                if request.scope.get("_quart._preserve_context", False):
                    self._preserved_context = request_context.copy()

    async def handle_websocket(self, websocket: Websocket) -> ResponseTypes | None:
        async with self.websocket_context(websocket) as websocket_context:
            try:
                return await self.full_dispatch_websocket(websocket_context)
            except asyncio.CancelledError:
                raise  # CancelledErrors should be handled by serving code.
            except Exception as error:
                return await self.handle_websocket_exception(error)
            finally:
                if websocket.scope.get("_quart._preserve_context", False):
                    self._preserved_context = websocket_context.copy()

    async def full_dispatch_request(
        self, request_context: RequestContext | None = None
    ) -> ResponseTypes:
        """Adds pre and post processing to the request dispatching.

        Arguments:
            request_context: The request context, optional as Flask
                omits this argument.
        """
        try:
            await request_started.send_async(self, _sync_wrapper=self.ensure_async)  # type: ignore

            result: ResponseReturnValue | HTTPException | None
            result = await self.preprocess_request(request_context)
            if result is None:
                result = await self.dispatch_request(request_context)
        except Exception as error:
            result = await self.handle_user_exception(error)
        return await self.finalize_request(result, request_context)

    async def full_dispatch_websocket(
        self, websocket_context: WebsocketContext | None = None
    ) -> ResponseTypes | None:
        """Adds pre and post processing to the websocket dispatching.

        Arguments:
            websocket_context: The websocket context, optional to match
                the Flask convention.
        """
        try:
            await websocket_started.send_async(
                self, _sync_wrapper=self.ensure_async  # type: ignore
            )

            result: ResponseReturnValue | HTTPException | None
            result = await self.preprocess_websocket(websocket_context)
            if result is None:
                result = await self.dispatch_websocket(websocket_context)
        except Exception as error:
            result = await self.handle_user_exception(error)
        return await self.finalize_websocket(result, websocket_context)

    async def preprocess_request(
        self, request_context: RequestContext | None = None
    ) -> ResponseReturnValue | None:
        """Preprocess the request i.e. call before_request functions.

        Arguments:
            request_context: The request context, optional as Flask
                omits this argument.
        """
        names = [None, *reversed((request_context or request_ctx).request.blueprints)]

        for name in names:
            for processor in self.url_value_preprocessors[name]:
                processor(request.endpoint, request.view_args)

        for name in names:
            for function in self.before_request_funcs[name]:
                result = await self.ensure_async(function)()
                if result is not None:
                    return result  # type: ignore

        return None

    async def preprocess_websocket(
        self, websocket_context: WebsocketContext | None = None
    ) -> ResponseReturnValue | None:
        """Preprocess the websocket i.e. call before_websocket functions.

        Arguments:
            websocket_context: The websocket context, optional as Flask
                omits this argument.
        """
        names = [
            None,
            *reversed((websocket_context or websocket_ctx).websocket.blueprints),
        ]

        for name in names:
            for processor in self.url_value_preprocessors[name]:
                processor(request.endpoint, request.view_args)

        for name in names:
            for function in self.before_websocket_funcs[name]:
                result = await self.ensure_async(function)()
                if result is not None:
                    return result  # type: ignore

        return None

    def raise_routing_exception(self, request: BaseRequestWebsocket) -> NoReturn:
        raise request.routing_exception

    async def dispatch_request(
        self, request_context: RequestContext | None = None
    ) -> ResponseReturnValue:
        """Dispatch the request to the view function.

        Arguments:
            request_context: The request context, optional as Flask
                omits this argument.
        """
        request_ = (request_context or request_ctx).request
        if request_.routing_exception is not None:
            self.raise_routing_exception(request_)

        if request_.method == "OPTIONS" and request_.url_rule.provide_automatic_options:
            return await self.make_default_options_response()

        handler = self.view_functions[request_.url_rule.endpoint]
        return await self.ensure_async(handler)(**request_.view_args)  # type: ignore

    async def dispatch_websocket(
        self, websocket_context: WebsocketContext | None = None
    ) -> ResponseReturnValue | None:
        """Dispatch the websocket to the view function.

        Arguments:
            websocket_context: The websocket context, optional to match
                the Flask convention.
        """
        websocket_ = (websocket_context or websocket_ctx).websocket
        if websocket_.routing_exception is not None:
            self.raise_routing_exception(websocket_)

        handler = self.view_functions[websocket_.url_rule.endpoint]
        return await self.ensure_async(handler)(**websocket_.view_args)  # type: ignore

    async def finalize_request(
        self,
        result: ResponseReturnValue | HTTPException,
        request_context: RequestContext | None = None,
        from_error_handler: bool = False,
    ) -> ResponseTypes:
        """Turns the view response return value into a response.

        Arguments:
            result: The result of the request to finalize into a response.
            request_context: The request context, optional as Flask
                omits this argument.
        """
        response = await self.make_response(result)
        try:
            response = await self.process_response(response, request_context)
            await request_finished.send_async(
                self, _sync_wrapper=self.ensure_async, response=response  # type: ignore
            )
        except Exception:
            if not from_error_handler:
                raise
            self.logger.exception("Request finalizing errored")
        return response

    async def finalize_websocket(
        self,
        result: ResponseReturnValue | HTTPException,
        websocket_context: WebsocketContext | None = None,
        from_error_handler: bool = False,
    ) -> ResponseTypes | None:
        """Turns the view response return value into a response.

        Arguments:
            result: The result of the websocket to finalize into a response.
            websocket_context: The websocket context, optional as Flask
                omits this argument.
        """
        if result is not None:
            response = await self.make_response(result)
        else:
            response = None
        try:
            response = await self.postprocess_websocket(response, websocket_context)
            await websocket_finished.send_async(
                self, _sync_wrapper=self.ensure_async, response=response  # type: ignore
            )
        except Exception:
            if not from_error_handler:
                raise
            self.logger.exception("Request finalizing errored")
        return response

    async def process_response(
        self,
        response: ResponseTypes,
        request_context: RequestContext | None = None,
    ) -> ResponseTypes:
        """Postprocess the request acting on the response.

        Arguments:
            response: The response after the request is finalized.
            request_context: The request context, optional as Flask
                omits this argument.
        """
        names = [*(request_context or request_ctx).request.blueprints, None]

        for function in (request_context or request_ctx)._after_request_functions:
            response = await self.ensure_async(function)(response)  # type: ignore

        for name in names:
            for function in reversed(self.after_request_funcs[name]):
                response = await self.ensure_async(function)(response)

        session_ = (request_context or request_ctx).session
        if not self.session_interface.is_null_session(session_):
            await self.ensure_async(self.session_interface.save_session)(self, session_, response)
        return response

    async def postprocess_websocket(
        self,
        response: ResponseTypes | None,
        websocket_context: WebsocketContext | None = None,
    ) -> ResponseTypes:
        """Postprocess the websocket acting on the response.

        Arguments:
            response: The response after the websocket is finalized.
            websocket_context: The websocket context, optional as Flask
                omits this argument.
        """
        names = [*(websocket_context or websocket_ctx).websocket.blueprints, None]

        for function in (websocket_context or websocket_ctx)._after_websocket_functions:
            response = await self.ensure_async(function)(response)  # type: ignore

        for name in names:
            for function in reversed(self.after_websocket_funcs[name]):
                response = await self.ensure_async(function)(response)  # type: ignore

        session_ = (websocket_context or websocket_ctx).session
        if not self.session_interface.is_null_session(session_):
            await self.session_interface.save_session(self, session_, response)
        return response

    async def __call__(
        self, scope: Scope, receive: ASGIReceiveCallable, send: ASGISendCallable
    ) -> None:
        """Called by ASGI servers.

        The related :meth:`~quart.app.Quart.asgi_app` is called,
        allowing for middleware usage whilst keeping the top level app
        a :class:`~quart.app.Quart` instance.
        """
        await self.asgi_app(scope, receive, send)

    async def asgi_app(
        self, scope: Scope, receive: ASGIReceiveCallable, send: ASGISendCallable
    ) -> None:
        """This handles ASGI calls, it can be wrapped in middleware.

        When using middleware with Quart it is preferable to wrap this
        method rather than the app itself. This is to ensure that the
        app is an instance of this class - which allows the quart cli
        to work correctly. To use this feature simply do,

        .. code-block:: python

            app.asgi_app = middleware(app.asgi_app)

        """
        asgi_handler: ASGIHTTPProtocol | ASGILifespanProtocol | ASGIWebsocketProtocol
        if scope["type"] == "http":
            asgi_handler = self.asgi_http_class(self, scope)
        elif scope["type"] == "websocket":
            asgi_handler = self.asgi_websocket_class(self, scope)
        elif scope["type"] == "lifespan":
            asgi_handler = self.asgi_lifespan_class(self, scope)
        else:
            raise RuntimeError("ASGI Scope type is unknown")
        await asgi_handler(receive, send)

    async def startup(self) -> None:
        self.shutdown_event = self.event_class()
        try:
            async with self.app_context():
                for func in self.before_serving_funcs:
                    await self.ensure_async(func)()
                for gen in self.while_serving_gens:
                    await gen.__anext__()
        except Exception as error:
            await got_serving_exception.send_async(
                self, _sync_wrapper=self.ensure_async, exception=error  # type: ignore
            )
            self.log_exception(sys.exc_info())
            raise

    async def shutdown(self) -> None:
        self.shutdown_event.set()
        try:
            await asyncio.wait_for(
                asyncio.gather(*self.background_tasks),
                timeout=self.config["BACKGROUND_TASK_SHUTDOWN_TIMEOUT"],
            )
        except asyncio.TimeoutError:
            await cancel_tasks(self.background_tasks)

        try:
            async with self.app_context():
                for func in self.after_serving_funcs:
                    await self.ensure_async(func)()
                for gen in self.while_serving_gens:
                    try:
                        await gen.__anext__()
                    except StopAsyncIteration:
                        pass
                    else:
                        raise RuntimeError("While serving generator didn't terminate")
        except Exception as error:
            await got_serving_exception.send_async(
                self, _sync_wrapper=self.ensure_async, exception=error  # type: ignore
            )
            self.log_exception(sys.exc_info())
            raise


def _cancel_all_tasks(loop: asyncio.AbstractEventLoop) -> None:
    tasks = [task for task in asyncio.all_tasks(loop) if not task.done()]
    if not tasks:
        return

    for task in tasks:
        task.cancel()
    loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))

    for task in tasks:
        if not task.cancelled() and task.exception() is not None:
            loop.call_exception_handler(
                {
                    "message": "unhandled exception during shutdown",
                    "exception": task.exception(),
                    "task": task,
                }
            )
