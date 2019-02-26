import asyncio
import os
import sys
import warnings
from collections import defaultdict, OrderedDict
from datetime import timedelta
from itertools import chain
from logging import Logger
from pathlib import Path
from types import TracebackType
from typing import (
    Any, AnyStr, Callable, cast, Dict, Iterable, List, Optional, Set, Tuple, Union, ValuesView,
)
from typing.io import IO

from hypercorn.asyncio import serve
from hypercorn.config import Config as HyperConfig

from .asgi import ASGIHTTPConnection, ASGILifespan, ASGIWebsocketConnection
from .blueprints import Blueprint
from .cli import AppGroup
from .config import Config, ConfigAttribute, DEFAULT_CONFIG
from .ctx import (
    _AppCtxGlobals, _request_ctx_stack, _websocket_ctx_stack, AppContext, has_request_context,
    has_websocket_context, RequestContext, WebsocketContext,
)
from .datastructures import CIMultiDict
from .debug import traceback_response
from .exceptions import all_http_exceptions, HTTPException
from .globals import g, request, session
from .helpers import (
    _endpoint_from_view_func, find_package, get_debug_flag, get_env,
    get_flashed_messages, url_for,
)
from .json import JSONDecoder, JSONEncoder, tojson_filter
from .logging import create_logger, create_serving_logger
from .routing import Map, MapAdapter, Rule
from .sessions import SecureCookieSessionInterface, Session
from .signals import (
    appcontext_tearing_down, got_request_exception, got_websocket_exception, request_finished,
    request_started, request_tearing_down, websocket_finished, websocket_started,
    websocket_tearing_down,
)
from .static import PackageStatic
from .templating import _default_template_context_processor, DispatchingJinjaLoader, Environment
from .testing import make_test_headers_path_and_query_string, QuartClient
from .typing import ResponseReturnValue
from .utils import ensure_coroutine
from .wrappers import BaseRequestWebsocket, Request, Response, Websocket

AppOrBlueprintKey = Optional[str]  # The App key is None, whereas blueprints are named


def _convert_timedelta(value: Union[float, timedelta]) -> timedelta:
    if not isinstance(value, timedelta):
        return timedelta(seconds=value)
    return value


class Quart(PackageStatic):
    """The web framework class, handles requests and returns responses.

    The primary method from a serving viewpoint is
    :meth:`~quart.app.Quart.handle_request`, from an application
    viewpoint all the other methods are vital.

    This can be extended in many ways, with most methods designed with
    this in mind. Additionally any of the classes listed as attributes
    can be replaced.

    Attributes:
        app_ctx_globals_class: The class to use for the ``g`` object
        asgi_http_class: The class to use to handle the ASGI HTTP
            protocol.
        asgi_lifespan_class: The class to use to handle the ASGI
            lifespan protocol.
        asgi_websocket_class: The class to use to handle the ASGI
            websocket protocol.
        config_class: The class to use for the configuration.
        env: The name of the environment the app is running on.
        debug: Wrapper around configuration DEBUG value, in many places
            this will result in more output if True. If unset, debug
            mode will be activated if environ is set to 'development'.
        jinja_environment: The class to use for the jinja environment.
        jinja_options: The default options to set when creating the jinja
            environment.
        json_decoder: The decoder for JSON data.
        json_encoder: The encoder for JSON data.
        permanent_session_lifetime: Wrapper around configuration
            PERMANENT_SESSION_LIFETIME value. Specifies how long the session
            data should survive.
        request_class: The class to use for requests.
        response_class: The class to user for responses.
        secret_key: Warpper around configuration SECRET_KEY value. The app
            secret for signing sessions.
        session_cookie_name: Wrapper around configuration
            SESSION_COOKIE_NAME, use to specify the cookie name for session
            data.
        session_interface: The class to use as the session interface.
        url_rule_class: The class to use for URL rules.
        websocket_class: The class to use for websockets.

    """
    app_ctx_globals_class = _AppCtxGlobals
    asgi_http_class = ASGIHTTPConnection
    asgi_lifespan_class = ASGILifespan
    asgi_websocket_class = ASGIWebsocketConnection
    config_class = Config
    debug = ConfigAttribute('DEBUG')
    env = ConfigAttribute('ENV')
    jinja_environment = Environment
    jinja_options = {
        'autoescape': True,
        'extensions': ['jinja2.ext.autoescape', 'jinja2.ext.with_'],
    }
    json_decoder = JSONDecoder
    json_encoder = JSONEncoder
    permanent_session_lifetime = ConfigAttribute(
        'PERMANENT_SESSION_LIFETIME', converter=_convert_timedelta,
    )
    request_class = Request
    response_class = Response
    secret_key = ConfigAttribute('SECRET_KEY')
    send_file_max_age_default = ConfigAttribute(
        'SEND_FILE_MAX_AGE_DEFAULT', converter=_convert_timedelta,
    )
    session_cookie_name = ConfigAttribute('SESSION_COOKIE_NAME')
    session_interface = SecureCookieSessionInterface()
    test_client_class = QuartClient
    testing = ConfigAttribute('TESTING')
    url_rule_class = Rule
    websocket_class = Websocket

    def __init__(
            self,
            import_name: str,
            static_url_path: Optional[str]=None,
            static_folder: Optional[str]='static',
            static_host: Optional[str]=None,
            host_matching: bool=False,
            template_folder: Optional[str]='templates',
            root_path: Optional[str]=None,
            instance_path: Optional[str]=None,
            instance_relative_config: bool=False,
    ) -> None:
        """Construct a Quart web application.

        Use to create a new web application to which requests should
        be handled, as specified by the various attached url
        rules. See also :class:`~quart.static.PackageStatic` for
        additional constructutor arguments.

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
            before_first_request_func: Functions to execute before the
                first request only.
            before_request_funcs: The functions to execute before handling
                a request.
            before_websocket_funcs: The functions to execute before handling
                a websocket.
        """
        super().__init__(import_name, template_folder, root_path, static_folder, static_url_path)

        if instance_path is None:
            instance_path = self.auto_find_instance_path()
        elif not os.path.isabs(instance_path):
            raise ValueError("The instance_path must be an absolute path.")
        self.instance_path = instance_path

        self.config = self.make_config(instance_relative_config)

        self.after_request_funcs: Dict[AppOrBlueprintKey, List[Callable]] = defaultdict(list)
        self.after_serving_funcs: List[Callable] = []
        self.after_websocket_funcs: Dict[AppOrBlueprintKey, List[Callable]] = defaultdict(list)
        self.before_first_request_funcs: List[Callable] = []
        self.before_request_funcs: Dict[AppOrBlueprintKey, List[Callable]] = defaultdict(list)
        self.before_serving_funcs: List[Callable] = []
        self.before_websocket_funcs: Dict[AppOrBlueprintKey, List[Callable]] = defaultdict(list)
        self.blueprints: Dict[str, Blueprint] = OrderedDict()
        self.error_handler_spec: Dict[AppOrBlueprintKey, Dict[Exception, Callable]] = defaultdict(dict)  # noqa: E501
        self.extensions: Dict[str, Any] = {}
        self.shell_context_processors: List[Callable] = []
        self.teardown_appcontext_funcs: List[Callable] = []
        self.teardown_request_funcs: Dict[AppOrBlueprintKey, List[Callable]] = defaultdict(list)  # noqa: E501
        self.teardown_websocket_funcs: Dict[AppOrBlueprintKey, List[Callable]] = defaultdict(list)  # noqa: E501
        self.template_context_processors: Dict[AppOrBlueprintKey, List[Callable]] = defaultdict(list)  # noqa: E501
        self.url_build_error_handlers: List[Callable] = []
        self.url_default_functions: Dict[AppOrBlueprintKey, List[Callable]] = defaultdict(list)
        self.url_map = Map(host_matching)
        self.url_value_preprocessors: Dict[AppOrBlueprintKey, List[Callable]] = defaultdict(list)
        self.view_functions: Dict[str, Callable] = {}

        self._got_first_request = False
        self._first_request_lock = asyncio.Lock()
        self._jinja_env: Optional[Environment] = None
        self._logger: Optional[Logger] = None

        self.cli = AppGroup(self.name)
        if self.has_static_folder:
            if static_host is None and host_matching:
                raise ValueError(
                    'static_host must be set if there is a static folder and host_matching is '
                    'enabled',
                )
            self.add_url_rule(
                f"{self.static_url_path}/<path:filename>", 'static', self.send_static_file,
                host=static_host,
            )

        self.template_context_processors[None] = [_default_template_context_processor]

    @property
    def name(self) -> str:
        """The name of this application.

        This is taken from the :attr:`import_name` and is used for
        debugging purposes.
        """
        if self.import_name == '__main__':
            path = Path(getattr(sys.modules['__main__'], '__file__', '__main__.py'))
            return path.stem
        return self.import_name

    @property
    def propagate_exceptions(self) -> bool:
        """Return true if exceptions should be propagated into debug pages.

        If false the exception will be handled. See the
        ``PROPAGATE_EXCEPTIONS`` config settin.
        """
        return self.config['PROPAGATE_EXCEPTIONS'] or (self.debug and not self.testing)

    @property
    def logger(self) -> Logger:
        """A :class:`logging.Logger` logger for the app.

        This can be used to log messages in a format as defined in the
        app configuration, for example,

        .. code-block:: python

            app.logger.debug("Request method %s", request.method)
            app.logger.error("Error, of some kind")

        """
        if self._logger is None:
            self._logger = create_logger(self)
        return self._logger

    @property
    def jinja_env(self) -> Environment:
        """The jinja environment used to load templates."""
        if self._jinja_env is None:
            self._jinja_env = self.create_jinja_environment()
        return self._jinja_env

    @property
    def got_first_request(self) -> bool:
        """Return if the app has received a request."""
        return self._got_first_request

    def auto_find_instance_path(self) -> str:
        """Locates the instace_path if it was not provided
        """
        prefix, package_path = find_package(self.import_name)
        if prefix is None:
            return os.path.join(package_path, 'instance')
        return os.path.join(prefix, 'var', self.name + '-instance')

    def make_config(self, instance_relative: bool = False) -> Config:
        """Create and return the configuration with appropriate defaults."""
        config = self.config_class(
            self.instance_path if instance_relative else self.root_path,
            DEFAULT_CONFIG,
        )
        config['ENV'] = get_env()
        config['DEBUG'] = get_debug_flag()
        return config

    def open_instance_resource(self, path: str, mode: str='rb') -> IO[AnyStr]:
        """Open a file for reading.

        Use as

        .. code-block:: python

            with app.open_instance_resouce(path) as file_:
                file_.read()
        """
        return open(os.path.join(self.instance_path, path), mode)

    def create_url_adapter(self, request: Optional[BaseRequestWebsocket]) -> Optional[MapAdapter]:
        """Create and return a URL adapter.

        This will create the adapter based on the request if present
        otherwise the app configuration.
        """
        if request is not None:
            host = request.host
            return self.url_map.bind_to_request(
                request.scheme, host, request.method, request.path, request.query_string,
            )

        if self.config['SERVER_NAME'] is not None:
            return self.url_map.bind(
                self.config['PREFERRED_URL_SCHEME'], self.config['SERVER_NAME'],
            )
        return None

    def create_jinja_environment(self) -> Environment:
        """Create and return the jinja environment.

        This will create the environment based on the
        :attr:`jinja_options` and configuration settings. The
        environment will include the Quart globals by default.
        """
        options = dict(self.jinja_options)
        if 'autoescape' not in options:
            options['autoescape'] = self.select_jinja_autoescape
        if 'auto_reload' not in options:
            options['auto_reload'] = self.config['TEMPLATES_AUTO_RELOAD'] or self.debug
        jinja_env = self.jinja_environment(self, **options)
        jinja_env.globals.update({
            'config': self.config,
            'g': g,
            'get_flashed_messages': get_flashed_messages,
            'request': request,
            'session': session,
            'url_for': url_for,
        })
        jinja_env.filters['tojson'] = tojson_filter
        return jinja_env

    def create_global_jinja_loader(self) -> DispatchingJinjaLoader:
        """Create and return a global (not blueprint specific) Jinja loader."""
        return DispatchingJinjaLoader(self)

    def select_jinja_autoescape(self, filename: str) -> bool:
        """Returns True if the filename indicates that it should be escaped."""
        if filename is None:
            return True
        return Path(filename).suffix in {'.htm', '.html', '.xhtml', '.xml'}

    async def update_template_context(self, context: dict) -> None:
        """Update the provided template context.

        This adds additional context from the various template context
        processors.

        Arguments:
            context: The context to update (mutate).
        """
        processors = self.template_context_processors[None]
        if has_request_context():
            blueprint = _request_ctx_stack.top.request.blueprint
            if blueprint is not None and blueprint in self.template_context_processors:
                processors = chain(processors, self.template_context_processors[blueprint])  # type: ignore # noqa
        extra_context: dict = {}
        for processor in processors:
            extra_context.update(await processor())
        original = context.copy()
        context.update(extra_context)
        context.update(original)

    def make_shell_context(self) -> dict:
        """Create a context for interactive shell usage.

        The :attr:`shell_context_processors` can be used to add
        additional context.
        """
        context = {'app': self, 'g': g}
        for processor in self.shell_context_processors:
            context.update(processor())
        return context

    def route(
            self,
            path: str,
            methods: Optional[List[str]]=None,
            endpoint: Optional[str]=None,
            defaults: Optional[dict]=None,
            host: Optional[str]=None,
            subdomain: Optional[str]=None,
            *,
            provide_automatic_options: Optional[bool]=None,
            strict_slashes: bool=True,
    ) -> Callable:
        """Add a route to the application.

        This is designed to be used as a decorator. An example usage,

        .. code-block:: python

            @app.route('/')
            def route():
                ...

        Arguments:
            path: The path to route on, should start with a ``/``.
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
            provide_automatic_options: Optionally False to prevent
                OPTION handling.
            strict_slashes: Strictly match the trailing slash present in the
                path. Will redirect a leaf (no slash) to a branch (with slash).
        """
        def decorator(func: Callable) -> Callable:
            self.add_url_rule(
                path, endpoint, func, methods, defaults=defaults, host=host, subdomain=subdomain,
                provide_automatic_options=provide_automatic_options, strict_slashes=strict_slashes,
            )
            return func
        return decorator

    def add_url_rule(
            self,
            path: str,
            endpoint: Optional[str]=None,
            view_func: Optional[Callable]=None,
            methods: Optional[Iterable[str]]=None,
            defaults: Optional[dict]=None,
            host: Optional[str]=None,
            subdomain: Optional[str]=None,
            *,
            provide_automatic_options: Optional[bool]=None,
            is_websocket: bool=False,
            strict_slashes: bool=True,
    ) -> None:
        """Add a route/url rule to the application.

        This is designed to be used on the application directly. An
        example usage,

        .. code-block:: python

            def route():
                ...

            app.add_url_rule('/', route)

        Arguments:
            path: The path to route on, should start with a ``/``.
            func: Callable that returns a reponse.
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
        endpoint = endpoint or _endpoint_from_view_func(view_func)
        handler = ensure_coroutine(view_func)
        if methods is None:
            methods = getattr(view_func, 'methods', ['GET'])

        methods = cast(Set[str], set(methods))
        required_methods = set(getattr(view_func, 'required_methods', set()))

        if provide_automatic_options is None:
            automatic_options = getattr(view_func, 'provide_automatic_options', None)
            if automatic_options is None:
                automatic_options = 'OPTIONS' not in methods
        else:
            automatic_options = provide_automatic_options

        if automatic_options:
            required_methods.add('OPTIONS')

        methods.update(required_methods)

        if not self.url_map.host_matching and (host is not None or subdomain is not None):
            raise RuntimeError('Cannot use host or subdomain without host matching enabled.')
        if host is not None and subdomain is not None:
            raise ValueError('Cannot set host and subdomain, please choose one or the other')

        if subdomain is not None:
            if self.config['SERVER_NAME'] is None:
                raise RuntimeError('SERVER_NAME config is required to use subdomain in a route.')
            host = f"{subdomain}.{self.config['SERVER_NAME']}"
        elif host is None and self.url_map.host_matching:
            host = self.config['SERVER_NAME']
            if host is None:
                raise RuntimeError(
                    'Cannot add a route with host matching enabled without either a specified '
                    'host or a config SERVER_NAME',
                )

        self.url_map.add(
            self.url_rule_class(
                path, methods, endpoint, host=host, provide_automatic_options=automatic_options,
                defaults=defaults, is_websocket=is_websocket, strict_slashes=strict_slashes,
            ),
        )
        if handler is not None:
            old_handler = self.view_functions.get(endpoint)
            if getattr(old_handler, '_quart_async_wrapper', False):
                old_handler = old_handler.__wrapped__  # type: ignore
            if old_handler is not None and old_handler != view_func:
                raise AssertionError(f"Handler is overwriting existing for endpoint {endpoint}")

        self.view_functions[endpoint] = handler

    def websocket(
            self,
            path: str,
            endpoint: Optional[str]=None,
            defaults: Optional[dict]=None,
            host: Optional[str]=None,
            subdomain: Optional[str]=None,
            *,
            strict_slashes: bool=True,
    ) -> Callable:
        """Add a websocket to the application.

        This is designed to be used as a decorator. An example usage,

        .. code-block:: python

            @app.websocket('/')
            def websocket_route():
                ...

        Arguments:
            path: The path to route on, should start with a ``/``.
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
        def decorator(func: Callable) -> Callable:
            self.add_websocket(
                path, endpoint, func, defaults=defaults, host=host, subdomain=subdomain,
                strict_slashes=strict_slashes,
            )
            return func
        return decorator

    def add_websocket(
            self,
            path: str,
            endpoint: Optional[str]=None,
            view_func: Optional[Callable]=None,
            defaults: Optional[dict]=None,
            host: Optional[str]=None,
            subdomain: Optional[str]=None,
            *,
            strict_slashes: bool=True,
    ) -> None:
        """Add a websocket url rule to the application.

        This is designed to be used on the application directly. An
        example usage,

        .. code-block:: python

            def websocket_route():
                ...

            app.add_websocket('/', websocket_route)

        Arguments:
            path: The path to route on, should start with a ``/``.
            func: Callable that returns a reponse.
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
        return self.add_url_rule(
            path, endpoint, view_func, {'GET'}, defaults=defaults, host=host, subdomain=subdomain,
            provide_automatic_options=False, is_websocket=True, strict_slashes=strict_slashes,
        )

    def endpoint(self, endpoint: str) -> Callable:
        """Register a function as an endpoint.

        This is designed to be used as a decorator. An example usage,

        .. code-block:: python

            @app.endpoint('name')
            def endpoint():
                ...

        Arguments:
            endpoint: The endpoint name to use.
        """
        def decorator(func: Callable) -> Callable:
            handler = ensure_coroutine(func)
            self.view_functions[endpoint] = handler
            return func
        return decorator

    def errorhandler(self, error: Union[Exception, int]) -> Callable:
        """Register a function as an error handler.

        This is designed to be used as a decorator. An example usage,

        .. code-block:: python

            @app.errorhandler(500)
            def error_handler():
                return "Error", 500

        Arguments:
            error: The error code or Exception to handle.
        """
        def decorator(func: Callable) -> Callable:
            self.register_error_handler(error, func)
            return func
        return decorator

    def register_error_handler(
            self, error: Union[Exception, int], func: Callable, name: AppOrBlueprintKey=None,
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
            name: Optional blueprint key name.
        """
        handler = ensure_coroutine(func)
        if isinstance(error, int):
            error = all_http_exceptions[error]  # type: ignore
        self.error_handler_spec[name][error] = handler  # type: ignore

    def template_filter(self, name: Optional[str]=None) -> Callable:
        """Add a template filter.

        This is designed to be used as a decorator. An example usage,

        .. code-block:: python

            @app.template_filter('name')
            def to_upper(value):
                return value.upper()

        Arguments:
            name: The filter name (defaults to function name).
        """
        def decorator(func: Callable) -> Callable:
            self.add_template_filter(func, name=name)
            return func
        return decorator

    def add_template_filter(self, func: Callable, name: Optional[str]=None) -> None:
        """Add a template filter.

        This is designed to be used on the application directly. An
        example usage,

        .. code-block:: python

            def to_upper(value):
                return value.upper()

            app.add_template_filter(to_upper)

        Arguments:
            func: The function that is the filter.
            name: The filter name (defaults to function name).
        """
        self.jinja_env.filters[name or func.__name__] = func

    def template_test(self, name: Optional[str]=None) -> Callable:
        """Add a template test.

        This is designed to be used as a decorator. An example usage,

        .. code-block:: python

            @app.template_test('name')
            def is_upper(value):
                return value.isupper()

        Arguments:
            name: The test name (defaults to function name).
        """
        def decorator(func: Callable) -> Callable:
            self.add_template_test(func, name=name)
            return func
        return decorator

    def add_template_test(self, func: Callable, name: Optional[str]=None) -> None:
        """Add a template test.

        This is designed to be used on the application directly. An
        example usage,

        .. code-block:: python

            def is_upper(value):
                return value.isupper()

            app.add_template_test(is_upper)

        Arguments:
            func: The function that is the test.
            name: The test name (defaults to function name).
        """
        self.jinja_env.tests[name or func.__name__] = func

    def template_global(self, name: Optional[str]=None) -> Callable:
        """Add a template global.

        This is designed to be used as a decorator. An example usage,

        .. code-block:: python

            @app.template_global('name')
            def five():
                return 5

        Arguments:
            name: The global name (defaults to function name).
        """
        def decorator(func: Callable) -> Callable:
            self.add_template_global(func, name=name)
            return func
        return decorator

    def add_template_global(self, func: Callable, name: Optional[str]=None) -> None:
        """Add a template global.

        This is designed to be used on the application directly. An
        example usage,

        .. code-block:: python

            def five():
                return 5

            app.add_template_global(five)

        Arguments:
            func: The function that is the global.
            name: The global name (defaults to function name).
        """
        self.jinja_env.globals[name or func.__name__] = func

    def context_processor(self, func: Callable, name: AppOrBlueprintKey=None) -> Callable:
        """Add a template context processor.

        This is designed to be used as a decorator. An example usage,

        .. code-block:: python

            @app.context_processor
            def update_context(context):
                return context

        """
        self.template_context_processors[name].append(ensure_coroutine(func))
        return func

    def shell_context_processor(self, func: Callable) -> Callable:
        """Add a shell context processor.

        This is designed to be used as a decorator. An example usage,

        .. code-block:: python

            @app.shell_context_processor
            def additional_context():
                return context

        """
        self.shell_context_processors.append(func)
        return func

    def url_defaults(self, func: Callable, name: AppOrBlueprintKey=None) -> Callable:
        """Add a url default preprocessor.

        This is designed to be used as a decorator. An example usage,

        .. code-block:: python

            @app.url_defaults
            def default(endpoint, values):
                ...
        """
        self.url_default_functions[name].append(func)
        return func

    def url_value_preprocessor(self, func: Callable, name: AppOrBlueprintKey=None) -> Callable:
        """Add a url value preprocessor.

        This is designed to be used as a decorator. An example usage,

        .. code-block:: python

            @app.url_value_preprocessor
            def value_preprocessor(endpoint, view_args):
                ...
        """
        self.url_value_preprocessors[name].append(func)
        return func

    def inject_url_defaults(self, endpoint: str, values: dict) -> None:
        """Injects default URL values into the passed values dict.

        This is used to assist when building urls, see
        :func:`~quart.helpers.url_for`.
        """
        functions = self.url_value_preprocessors[None]
        if '.' in endpoint:
            blueprint = endpoint.rsplit('.', 1)[0]
            functions = chain(functions, self.url_value_preprocessors[blueprint])  # type: ignore

        for function in functions:
            function(endpoint, values)

    def handle_url_build_error(self, error: Exception, endpoint: str, values: dict) -> str:
        """Handle a build error.

        Ideally this will return a valid url given the error endpoint
        and values.
        """
        for handler in self.url_build_error_handlers:
            result = handler(error, endpoint, values)
            if result is not None:
                return result
        raise error

    def _find_exception_handler(self, error: Exception) -> Optional[Callable]:
        if _request_ctx_stack.top is not None:
            blueprint = _request_ctx_stack.top.request.blueprint
        elif _websocket_ctx_stack.top is not None:
            blueprint = _websocket_ctx_stack.top.websocket.blueprint
        else:
            blueprint = None
        handler = _find_exception_handler(error, self.error_handler_spec.get(blueprint, {}))
        if handler is None:
            handler = _find_exception_handler(
                error, self.error_handler_spec[None],
            )
        return handler

    async def handle_http_exception(self, error: Exception) -> Response:
        """Handle a HTTPException subclass error.

        This will attempt to find a handler for the error and if fails
        will fall back to the error response.
        """
        handler = self._find_exception_handler(error)
        if handler is None:
            return error.get_response()  # type: ignore
        else:
            return await handler(error)

    def trap_http_exception(self, error: Exception) -> bool:
        """Check it error is http and should be trapped.

        Trapped errors are not handled by the
        :meth:`handle_http_exception`, but instead trapped by the
        outer most (or user handlers). This can be useful when
        debuging to allow tracebacks to be viewed by the debug page.
        """
        return self.config['TRAP_HTTP_EXCEPTIONS']

    async def handle_user_exception(self, error: Exception) -> Response:
        """Handle an exception that has been raised.

        This should forward :class:`~quart.exception.HTTPException` to
        :meth:`handle_http_exception`, then attempt to handle the
        error. If it cannot it should reraise the error.
        """
        if isinstance(error, HTTPException) and not self.trap_http_exception(error):
            return await self.handle_http_exception(error)

        handler = self._find_exception_handler(error)
        if handler is None:
            raise error
        return await handler(error)

    async def handle_exception(self, error: Exception) -> Response:
        """Handle an uncaught exception.

        By default this switches the error response to a 500 internal
        server error.
        """
        await got_request_exception.send(self, exception=error)

        self.log_exception(sys.exc_info())

        if self.propagate_exceptions:
            return await traceback_response()

        internal_server_error = all_http_exceptions[500]()
        handler = self._find_exception_handler(internal_server_error)

        if handler is None:
            return internal_server_error.get_response()
        else:
            return await self.finalize_request(await handler(error), from_error_handler=True)

    async def handle_websocket_exception(self, error: Exception) -> Optional[Response]:
        """Handle an uncaught exception.

        By default this logs the exception and then re-raises it.
        """
        await got_websocket_exception.send(self, exception=error)

        self.log_exception(sys.exc_info())

        internal_server_error = all_http_exceptions[500]()
        handler = self._find_exception_handler(internal_server_error)

        if handler is None:
            return internal_server_error.get_response()
        else:
            return await self.finalize_websocket(await handler(error), from_error_handler=True)

    def log_exception(self, exception_info: Tuple[type, BaseException, TracebackType]) -> None:
        """Log a exception to the :attr:`logger`.

        By default this is only invoked for unhandled exceptions.
        """
        if has_request_context():
            request_ = _request_ctx_stack.top.request
            self.logger.error(
                f"Exception on request {request_.method} {request_.path}",
                exc_info=exception_info,
            )
        if has_websocket_context():
            websocket_ = _websocket_ctx_stack.top.websocket
            self.logger.error(
                f"Exception on websocket {websocket_.path}",
                exc_info=exception_info,
            )

    def before_request(self, func: Callable, name: AppOrBlueprintKey=None) -> Callable:
        """Add a before request function.

        This is designed to be used as a decorator. An example usage,

        .. code-block:: python

            @app.before_request
            def func():
                ...

        Arguments:
            func: The before request function itself.
            name: Optional blueprint key name.
        """
        handler = ensure_coroutine(func)
        self.before_request_funcs[name].append(handler)
        return func

    def before_websocket(self, func: Callable, name: AppOrBlueprintKey=None) -> Callable:
        """Add a before websocket function.

        This is designed to be used as a decorator. An example usage,

        .. code-block:: python

            @app.before_websocket
            def func():
                ...

        Arguments:
            func: The before websocket function itself.
            name: Optional blueprint key name.
        """
        handler = ensure_coroutine(func)
        self.before_websocket_funcs[name].append(handler)
        return func

    def before_first_request(self, func: Callable, name: AppOrBlueprintKey=None) -> Callable:
        """Add a before **first** request function.

        This is designed to be used as a decorator. An example usage,

        .. code-block:: python

            @app.before_first_request
            def func():
                ...

        Arguments:
            func: The before first request function itself.
            name: Optional blueprint key name.
        """
        handler = ensure_coroutine(func)
        self.before_first_request_funcs.append(handler)
        return func

    def before_serving(self, func: Callable) -> Callable:
        """Add a before serving function.

        This will allow the function provided to be called once before
        anything is served (before any byte is received).

        This is designed to be used as a decorator. An example usage,

        .. code-block:: python

            @app.before_serving
            def func():
                ...

        Arguments:
            func: The function itself.
        """
        handler = ensure_coroutine(func)
        self.before_serving_funcs.append(handler)
        return func

    def after_request(self, func: Callable, name: AppOrBlueprintKey=None) -> Callable:
        """Add an after request function.

        This is designed to be used as a decorator. An example usage,

        .. code-block:: python

            @app.after_request
            def func(response):
                return response

        Arguments:
            func: The after request function itself.
            name: Optional blueprint key name.
        """
        handler = ensure_coroutine(func)
        self.after_request_funcs[name].append(handler)
        return func

    def after_websocket(self, func: Callable, name: AppOrBlueprintKey=None) -> Callable:
        """Add an after websocket function.

        This is designed to be used as a decorator. An example usage,

        .. code-block:: python

            @app.after_websocket
            def func(response):
                return response

        Arguments:
            func: The after websocket function itself.
            name: Optional blueprint key name.
        """
        handler = ensure_coroutine(func)
        self.after_websocket_funcs[name].append(handler)
        return func

    def after_serving(self, func: Callable) -> Callable:
        """Add a after serving function.

        This will allow the function provided to be called once after
        anything is served (after last byte is sent).

        This is designed to be used as a decorator. An example usage,

        .. code-block:: python

            @app.after_serving
            def func():
                ...

        Arguments:
            func: The function itself.

        """
        handler = ensure_coroutine(func)
        self.after_serving_funcs.append(handler)
        return func

    def teardown_request(self, func: Callable, name: AppOrBlueprintKey=None) -> Callable:
        """Add a teardown request function.

        This is designed to be used as a decorator. An example usage,

        .. code-block:: python

            @app.teardown_request
            def func():
                ...

        Arguments:
            func: The teardown request function itself.
            name: Optional blueprint key name.
        """
        self.teardown_request_funcs[name].append(func)
        return func

    def teardown_websocket(self, func: Callable, name: AppOrBlueprintKey=None) -> Callable:
        """Add a teardown websocket function.

        This is designed to be used as a decorator. An example usage,

        .. code-block:: python

            @app.teardown_websocket
            def func():
                ...

        Arguments:
            func: The teardown websocket function itself.
            name: Optional blueprint key name.
        """
        self.teardown_websocket_funcs[name].append(func)
        return func

    def teardown_appcontext(self, func: Callable) -> Callable:
        """Add a teardown app (context) function.

        This is designed to be used as a decorator. An example usage,

        .. code-block:: python

            @app.teardown_appcontext
            def func():
                ...

        Arguments:
            func: The teardown function itself.
            name: Optional blueprint key name.
        """
        self.teardown_appcontext_funcs.append(func)
        return func

    def register_blueprint(self, blueprint: Blueprint, url_prefix: Optional[str]=None) -> None:
        """Register a blueprint on the app.

        This results in the blueprint's routes, error handlers
        etc... being added to the app.

        Arguments:
            blueprint: The blueprint to register.
            url_prefix: Optional prefix to apply to all paths.
        """
        first_registration = False
        if blueprint.name in self.blueprints and self.blueprints[blueprint.name] is not blueprint:
            raise RuntimeError(
                f"Blueprint name '{blueprint.name}' "
                f"is already registered by {self.blueprints[blueprint.name]}. "
                "Blueprints must have unique names",
            )
        else:
            self.blueprints[blueprint.name] = blueprint
            first_registration = True
        blueprint.register(self, first_registration, url_prefix=url_prefix)

    def iter_blueprints(self) -> ValuesView[Blueprint]:
        """Return a iterator over the blueprints."""
        return self.blueprints.values()

    async def open_session(self, request: BaseRequestWebsocket) -> Session:
        """Open and return a Session using the request."""
        return await ensure_coroutine(self.session_interface.open_session)(self, request)

    async def make_null_session(self) -> Session:
        """Create and return a null session."""
        return await ensure_coroutine(self.session_interface.make_null_session)(self)

    async def save_session(self, session: Session, response: Response) -> None:
        """Saves the session to the response."""
        await ensure_coroutine(self.session_interface.save_session)(self, session, response)

    async def do_teardown_request(
            self,
            exc: Optional[BaseException],
            request_context: Optional[RequestContext]=None,
    ) -> None:
        """Teardown the request, calling the teardown functions.

        Arguments:
            exc: Any exception not handled that has caused the request
                to teardown.
            request_context: The request context, optional as Flask
                omits this argument.
        """
        request_ = (request_context or _request_ctx_stack.top).request
        functions = self.teardown_request_funcs[None]
        blueprint = request_.blueprint
        if blueprint is not None:
            functions = chain(functions, self.teardown_request_funcs[blueprint])  # type: ignore

        for function in functions:
            function(exc=exc)
        await request_tearing_down.send(self, exc=exc)

    async def do_teardown_websocket(
            self,
            exc: Optional[BaseException],
            websocket_context: Optional[WebsocketContext]=None,
    ) -> None:
        """Teardown the websocket, calling the teardown functions.

        Arguments:
            exc: Any exception not handled that has caused the websocket
                to teardown.
            websocket_context: The websocket context, optional as Flask
                omits this argument.
        """
        websocket_ = (websocket_context or _websocket_ctx_stack.top).websocket
        functions = self.teardown_websocket_funcs[None]
        blueprint = websocket_.blueprint
        if blueprint is not None:
            functions = chain(functions, self.teardown_websocket_funcs[blueprint])  # type: ignore

        for function in functions:
            function(exc=exc)
        await websocket_tearing_down.send(self, exc=exc)

    async def do_teardown_appcontext(self, exc: Optional[BaseException]) -> None:
        """Teardown the app (context), calling the teardown functions."""
        for function in self.teardown_appcontext_funcs:
            function(exc)
        await appcontext_tearing_down.send(self, exc=exc)

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

    def run(
            self,
            host: str='127.0.0.1',
            port: int=5000,
            debug: Optional[bool]=None,
            use_reloader: bool=True,
            loop: Optional[asyncio.AbstractEventLoop]=None,
            ca_certs: Optional[str]=None,
            certfile: Optional[str]=None,
            keyfile: Optional[str]=None,
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
                "uses by default. This method is meant for development and debugging."
            )

        config = HyperConfig()
        config.access_log_format = "%(h)s %(r)s %(s)s %(b)s %(D)s"
        config.access_logger = create_serving_logger()  # type: ignore
        config.bind = [f"{host}:{port}"]
        config.ca_certs = ca_certs
        config.certfile = certfile
        if debug is not None:
            self.debug = debug
        config.error_logger = config.access_logger  # type: ignore
        config.keyfile = keyfile
        config.use_reloader = use_reloader

        scheme = 'https' if config.ssl_enabled else 'http'
        print("Running on {}://{} (CTRL + C to quit)".format(scheme, config.bind[0]))  # noqa: T001

        if loop is not None:
            loop.set_debug(debug or False)
            loop.run_until_complete(serve(self, config))  # type: ignore
        else:
            asyncio.run(serve(self, config), debug=config.debug)  # type: ignore

    def test_client(self) -> QuartClient:
        """Creates and returns a test client."""
        return self.test_client_class(self)

    def test_request_context(
            self,
            path: str,
            *,
            method: str='GET',
            headers: Optional[Union[dict, CIMultiDict]]=None,
            query_string: Optional[dict]=None,
            scheme: str='http',
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
            self, path, headers, query_string,
        )
        request = self.request_class(method, scheme, path, query_string_bytes, headers)
        request.body.set_result(b'')
        return self.request_context(request)

    async def try_trigger_before_first_request_functions(self) -> None:
        """Trigger the before first request methods."""
        if self._got_first_request:
            return

        # Reverse the teardown functions, so as to match the expected usage
        self.teardown_appcontext_funcs = list(reversed(self.teardown_appcontext_funcs))
        for key, value in self.teardown_request_funcs.items():
            self.teardown_request_funcs[key] = list(reversed(value))
        for key, value in self.teardown_websocket_funcs.items():
            self.teardown_websocket_funcs[key] = list(reversed(value))

        async with self._first_request_lock:
            if self._got_first_request:
                return
            for function in self.before_first_request_funcs:
                await function()
            self._got_first_request = True

    async def make_default_options_response(self) -> Response:
        """This is the default route function for OPTIONS requests."""
        methods = _request_ctx_stack.top.url_adapter.allowed_methods()
        return self.response_class('', headers={'Allow': ', '.join(methods)})

    async def make_response(self, result: ResponseReturnValue) -> Response:
        """Make a Response from the result of the route handler.

        The result itself can either be:
          - A Response object (or subclass).
          - A tuple of a ResponseValue and a header dictionary.
          - A tuple of a ResponseValue, status code and a header dictionary.

        A ResponseValue is either a Response object (or subclass) or a str.
        """
        status_or_headers = None
        headers = None
        status = None
        if isinstance(result, tuple):
            value, status_or_headers, headers = result + (None,) * (3 - len(result))
        else:
            value = result

        if value is None:
            raise TypeError('The response value returned by the view function cannot be None')

        if isinstance(status_or_headers, (dict, list)):
            headers = status_or_headers
            status = None
        elif status_or_headers is not None:
            status = status_or_headers

        if not isinstance(value, Response):
            response = self.response_class(value, timeout=self.config['RESPONSE_TIMEOUT'])
        else:
            response = value

        if status is not None:
            response.status_code = status

        if headers is not None:
            response.headers.update(headers)

        return response

    async def handle_request(self, request: Request) -> Response:
        async with self.request_context(request) as request_context:
            try:
                return await self.full_dispatch_request(request_context)
            except asyncio.CancelledError:
                raise  # CancelledErrors should be handled by serving code.
            except Exception as error:
                return await self.handle_exception(error)

    async def full_dispatch_request(
        self, request_context: Optional[RequestContext]=None,
    ) -> Response:
        """Adds pre and post processing to the request dispatching.

        Arguments:
            request_context: The request context, optional as Flask
                omits this argument.
        """
        await self.try_trigger_before_first_request_functions()
        await request_started.send(self)
        try:
            result = await self.preprocess_request(request_context)
            if result is None:
                result = await self.dispatch_request(request_context)
        except Exception as error:
            result = await self.handle_user_exception(error)
        return await self.finalize_request(result, request_context)

    async def preprocess_request(
        self, request_context: Optional[RequestContext]=None,
    ) -> Optional[ResponseReturnValue]:
        """Preprocess the request i.e. call before_request functions.

        Arguments:
            request_context: The request context, optional as Flask
                omits this argument.
        """
        request_ = (request_context or _request_ctx_stack.top).request
        blueprint = request_.blueprint
        processors = self.url_value_preprocessors[None]
        if blueprint is not None:
            processors = chain(processors, self.url_value_preprocessors[blueprint])  # type: ignore
        for processor in processors:
            processor(request.endpoint, request.view_args)

        functions = self.before_request_funcs[None]
        if blueprint is not None:
            functions = chain(functions, self.before_request_funcs[blueprint])  # type: ignore
        for function in functions:
            result = await function()
            if result is not None:
                return result
        return None

    async def dispatch_request(
        self, request_context: Optional[RequestContext]=None,
    ) -> ResponseReturnValue:
        """Dispatch the request to the view function.

        Arguments:
            request_context: The request context, optional as Flask
                omits this argument.
        """
        request_ = (request_context or _request_ctx_stack.top).request
        if request_.routing_exception is not None:
            raise request_.routing_exception

        if request_.method == 'OPTIONS' and request_.url_rule.provide_automatic_options:
            return await self.make_default_options_response()

        handler = self.view_functions[request_.url_rule.endpoint]
        return await handler(**request_.view_args)

    async def finalize_request(
        self,
        result: ResponseReturnValue,
        request_context: Optional[RequestContext]=None,
        from_error_handler: bool=False,
    ) -> Response:
        """Turns the view response return value into a response.

        Arguments:
            result: The result of the request to finalize into a response.
            request_context: The request context, optional as Flask
                omits this argument.
        """
        response = await self.make_response(result)
        try:
            response = await self.process_response(response, request_context)
            await request_finished.send(self, response=response)
        except Exception:
            if not from_error_handler:
                raise
            self.logger.exception('Request finalizing errored')
        return response

    async def process_response(
        self,
        response: Response,
        request_context: Optional[RequestContext]=None,
    ) -> Response:
        """Postprocess the request acting on the response.

        Arguments:
            response: The response after the request is finalized.
            request_context: The request context, optional as Flask
                omits this argument.
        """
        request_ = (request_context or _request_ctx_stack.top).request
        functions = (request_context or _request_ctx_stack.top)._after_request_functions
        blueprint = request_.blueprint
        if blueprint is not None:
            functions = chain(functions, self.after_request_funcs[blueprint])
        functions = chain(functions, self.after_request_funcs[None])

        for function in functions:
            response = await function(response)

        session_ = (request_context or _request_ctx_stack.top).session
        if not self.session_interface.is_null_session(session_):
            await self.save_session(session_, response)
        return response

    async def handle_websocket(self, websocket: Websocket) -> Optional[Response]:
        async with self.websocket_context(websocket) as websocket_context:
            try:
                return await self.full_dispatch_websocket(websocket_context)
            except asyncio.CancelledError:
                raise  # CancelledErrors should be handled by serving code.
            except Exception as error:
                return await self.handle_websocket_exception(error)

    async def full_dispatch_websocket(
        self, websocket_context: Optional[WebsocketContext]=None,
    ) -> Optional[Response]:
        """Adds pre and post processing to the websocket dispatching.

        Arguments:
            websocket_context: The websocket context, optional to match
                the Flask convention.
        """
        await self.try_trigger_before_first_request_functions()
        await websocket_started.send(self)
        try:
            result = await self.preprocess_websocket(websocket_context)
            if result is None:
                result = await self.dispatch_websocket(websocket_context)
        except Exception as error:
            result = await self.handle_user_exception(error)
        return await self.finalize_websocket(result, websocket_context)

    async def preprocess_websocket(
        self, websocket_context: Optional[WebsocketContext]=None,
    ) -> Optional[ResponseReturnValue]:
        """Preprocess the websocket i.e. call before_websocket functions.

        Arguments:
            websocket_context: The websocket context, optional as Flask
                omits this argument.
        """
        websocket_ = (websocket_context or _websocket_ctx_stack.top).websocket
        blueprint = websocket_.blueprint
        processors = self.url_value_preprocessors[None]
        if blueprint is not None:
            processors = chain(processors, self.url_value_preprocessors[blueprint])  # type: ignore
        for processor in processors:
            processor(websocket_.endpoint, websocket_.view_args)

        functions = self.before_websocket_funcs[None]
        if blueprint is not None:
            functions = chain(functions, self.before_websocket_funcs[blueprint])  # type: ignore
        for function in functions:
            result = await function()
            if result is not None:
                return result
        return None

    async def dispatch_websocket(
        self, websocket_context: Optional[WebsocketContext]=None,
    ) -> None:
        """Dispatch the websocket to the view function.

        Arguments:
            websocket_context: The websocket context, optional to match
                the Flask convention.
        """
        websocket_ = (websocket_context or _websocket_ctx_stack.top).websocket
        if websocket_.routing_exception is not None:
            raise websocket_.routing_exception

        handler = self.view_functions[websocket_.url_rule.endpoint]
        return await handler(**websocket_.view_args)

    async def finalize_websocket(
        self,
        result: ResponseReturnValue,
        websocket_context: Optional[WebsocketContext]=None,
        from_error_handler: bool=False,
    ) -> Optional[Response]:
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
            await websocket_finished.send(self, response=response)
        except Exception:
            if not from_error_handler:
                raise
            self.logger.exception('Request finalizing errored')
        return response

    async def postprocess_websocket(
        self,
        response: Optional[Response],
        websocket_context: Optional[WebsocketContext]=None,
    ) -> Response:
        """Postprocess the websocket acting on the response.

        Arguments:
            response: The response after the websocket is finalized.
            webcoket_context: The websocket context, optional as Flask
                omits this argument.
        """
        websocket_ = (websocket_context or _websocket_ctx_stack.top).websocket
        functions = (websocket_context or _websocket_ctx_stack.top)._after_websocket_functions
        blueprint = websocket_.blueprint
        if blueprint is not None:
            functions = chain(functions, self.after_websocket_funcs[blueprint])
        functions = chain(functions, self.after_websocket_funcs[None])

        for function in functions:
            response = await function(response)

        return response

    def __call__(self, scope: dict) -> Callable:
        if scope['type'] == 'http':
            return self.asgi_http_class(self, scope)
        elif scope['type'] == 'websocket':
            return self.asgi_websocket_class(self, scope)
        elif scope['type'] == 'lifespan':
            return self.asgi_lifespan_class(self, scope)
        else:
            raise RuntimeError('ASGI Scope type is unknown')

    async def startup(self) -> None:
        self._got_first_request = False

        async with self.app_context():
            for func in self.before_serving_funcs:
                await func()

    async def shutdown(self) -> None:
        async with self.app_context():
            for func in self.after_serving_funcs:
                await func()


def _find_exception_handler(
        error: Exception, exception_handlers: Dict[Exception, Callable],
) -> Optional[Callable]:
    for exception, handler in exception_handlers.items():
        if isinstance(error, exception):  # type: ignore
            return handler
    return None
