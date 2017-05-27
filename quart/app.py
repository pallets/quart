import asyncio
import sys
from collections import defaultdict, OrderedDict
from datetime import timedelta
from itertools import chain
from logging import Logger
from pathlib import Path
from ssl import SSLContext
from types import TracebackType
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple, Union, ValuesView  # noqa

from multidict import CIMultiDict

from .blueprints import Blueprint
from .config import Config, ConfigAttribute, DEFAULT_CONFIG
from .ctx import (
    _AppCtxGlobals, _request_ctx_stack, AppContext, has_request_context, RequestContext,
)
from .exceptions import all_http_exceptions, HTTPException
from .globals import g, request, session
from .helpers import get_flashed_messages, url_for
from .logging import create_logger
from .routing import Map, MapAdapter, Rule
from .serving import run_app
from .sessions import SecureCookieSessionInterface, Session
from .static import PackageStatic
from .templating import _default_template_context_processor, DispatchingJinjaLoader, Environment
from .testing import TestClient
from .typing import ResponseReturnValue
from .wrappers import Request, Response

# There seems to be a mypy bug, this should be Optional[str] but that
# is an invalid type.
AppOrBlueprintKey = str  # The App key is None, whereas blueprints are named


def _convert_timedelta(value: Union[float, timedelta]) -> timedelta:
    if not isinstance(value, timedelta):
        return timedelta(seconds=value)
    return value


class Quart(PackageStatic):

    app_ctx_globals_class = _AppCtxGlobals
    config_class = Config

    debug = ConfigAttribute('DEBUG')
    jinja_options = {
        'autoescape': True,
        'extensions': ['jinja2.ext.autoescape', 'jinja2.ext.with_'],
    }
    logger_name = ConfigAttribute('LOGGER_NAME')
    permanent_session_lifetime = ConfigAttribute(
        'PERMANENT_SESSION_LIFETIME', converter=_convert_timedelta,
    )
    request_class = Request
    response_class = Response
    secret_key = ConfigAttribute('SECRET_KEY')
    session_cookie_name = ConfigAttribute('SESSION_COOKIE_NAME')
    session_interface = SecureCookieSessionInterface()
    testing = ConfigAttribute('TESTING')

    def __init__(
            self,
            import_name: str,
            static_url_path: Optional[str]=None,
            static_folder: Optional[str]='static',
            template_folder: Optional[str]='templates',
            root_path: Optional[str]=None,
    ) -> None:
        super().__init__(import_name, template_folder, root_path)

        self.config = self.make_config()

        self.after_request_funcs: Dict[AppOrBlueprintKey, List[Callable]] = defaultdict(list)
        self.before_first_request_funcs: List[Callable] = []
        self.before_request_funcs: Dict[AppOrBlueprintKey, List[Callable]] = defaultdict(list)
        self.blueprints: Dict[str, Blueprint] = OrderedDict()
        self.error_handler_spec: Dict[AppOrBlueprintKey, Dict[Exception, Callable]] = defaultdict(dict)  # noqa: E501
        self.static_folder = static_folder
        self.static_url_path = static_url_path
        self.template_context_processors: Dict[AppOrBlueprintKey, List[Callable]] = defaultdict(list)  # noqa: E501
        self.url_map = Map()
        self.view_functions: Dict[str, Callable] = {}

        self._got_first_request = False
        self._first_request_lock = asyncio.Lock()
        self._jinja_env: Optional[Environment] = None
        self._logger: Optional[Logger] = None

        if self.has_static_folder:
            self.add_url_rule(
                f"{self.static_url_path}/<path:filename>", self.send_static_file,
                endpoint='static',
            )

        self.template_context_processors[None] = [_default_template_context_processor]

    @property
    def logger(self) -> Logger:
        if self._logger is not None:
            return self._logger
        else:
            self._logger = create_logger(self)
            return self._logger

    @property
    def jinja_env(self) -> Environment:
        if self._jinja_env is None:
            self._jinja_env = self.create_jinja_environment()
        return self._jinja_env

    def make_config(self) -> Config:
        return self.config_class(self.root_path, DEFAULT_CONFIG)

    def create_jinja_environment(self) -> Environment:
        options = dict(self.jinja_options)
        if 'autoescape' not in options:
            options['autoescape'] = self.select_jinja_autoescape
        if 'auto_reload' not in options:
            options['auto_reload'] = self.config['TEMPLATES_AUTO_RELOAD'] or self.debug
        jinja_env = Environment(self, **options)
        jinja_env.globals.update({
            'config': self.config,
            'g': g,
            'get_flashed_messages': get_flashed_messages,
            'request': request,
            'session': session,
            'url_for': url_for,
        })
        return jinja_env

    def create_global_jinja_loader(self) -> DispatchingJinjaLoader:
        return DispatchingJinjaLoader(self)

    def select_jinja_autoescape(self, filename: str) -> bool:
        """Returns True if the filename indicates that it should be escaped."""
        if filename is None:
            return True
        return Path(filename).suffix in {'.htm', '.html', '.xhtml', '.xml'}

    def update_template_context(self, context: dict) -> None:
        processors = self.template_context_processors[None]
        if has_request_context():
            blueprint = _request_ctx_stack.top.request.blueprint
            if blueprint is not None and blueprint in self.template_context_processors:
                processors.extend(self.template_context_processors[blueprint])
        extra_context: dict = {}
        for processor in processors:
            extra_context.update(processor())
        original = context.copy()
        context.update(extra_context)
        context.update(original)

    def route(
            self,
            path: str,
            methods: List[str]=['GET'],
            *,
            provide_automatic_options: bool=True
    ) -> Callable:

        def decorator(func: Callable) -> Callable:
            self.add_url_rule(
                path, func, methods, provide_automatic_options=provide_automatic_options,
            )
            return func
        return decorator

    def add_url_rule(
            self,
            path: str,
            func: Callable,
            methods: List[str]=['GET'],
            endpoint: Optional[str]=None,
            *,
            provide_automatic_options: bool=True
    ) -> None:
        endpoint = endpoint or func.__name__
        handler = _ensure_coroutine(func)
        automatic_options = 'OPTIONS' not in methods and provide_automatic_options
        self.url_map.add(
            Rule(path, methods, endpoint, provide_automatic_options=automatic_options),
        )
        self.view_functions[endpoint] = handler

    def errorhandler(self, error: Union[Exception, int]) -> Callable:

        def decorator(func: Callable) -> Callable:
            self.register_error_handler(error, func)
            return func
        return decorator

    def register_error_handler(
            self, error: Union[Exception, int], func: Callable, name: AppOrBlueprintKey=None,
    ) -> None:
        handler = _ensure_coroutine(func)
        if isinstance(error, int):
            error = all_http_exceptions[error]  # type: ignore
        self.error_handler_spec[name][error] = handler  # type: ignore

    def _find_exception_handler(self, error: Exception) -> Optional[Callable]:
        handler = _find_exception_handler(
            error, self.error_handler_spec.get(_request_ctx_stack.top.request.blueprint, {}),
        )
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
        return await handler(error)

    async def handle_user_exception(self, error: Exception) -> Response:
        """Handle an exception that has been raised.

        This should forward :class:`~quart.exception.HTTPException` to
        :meth:`handle_http_exception`, then attempt to handle the
        error. If it cannot it should reraise the error.
        """
        if isinstance(error, HTTPException):
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
        internal_server_error = all_http_exceptions[500]()
        handler = self._find_exception_handler(internal_server_error)

        self.log_exception(sys.exc_info())
        if handler is None:
            return internal_server_error.get_response()
        else:
            return await handler(error)

    def log_exception(self, exception_info: Tuple[type, BaseException, TracebackType]) -> None:
        request_ = _request_ctx_stack.top.request
        self.logger.error(
            f"Exception on {request_.method} {request_.path}",
            exc_info=exception_info,
        )

    def before_request(self, func: Callable, name: AppOrBlueprintKey=None) -> Callable:
        handler = _ensure_coroutine(func)
        self.before_request_funcs[name].append(handler)
        return func

    def before_first_request(self, func: Callable, name: AppOrBlueprintKey=None) -> Callable:
        handler = _ensure_coroutine(func)
        self.before_first_request_funcs.append(handler)
        return func

    def after_request(self, func: Callable, name: AppOrBlueprintKey=None) -> Callable:
        handler = _ensure_coroutine(func)
        self.after_request_funcs[name].append(handler)
        return func

    def context_processor(self, func: Callable, name: AppOrBlueprintKey=None) -> Callable:
        self.template_context_processors[name].append(func)
        return func

    def register_blueprint(self, blueprint: Blueprint, url_prefix: Optional[str]=None) -> None:
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
        return self.blueprints.values()

    def open_session(self, request: Request) -> Session:
        return self.session_interface.open_session(self, request)

    def make_null_session(self) -> Session:
        return self.session_interface.make_null_session(self)

    def save_session(self, session: Session, response: Response) -> Response:
        return self.session_interface.save_session(self, session, response)

    def app_context(self) -> AppContext:
        return AppContext(self)

    def request_context(self, request: Request) -> RequestContext:
        return RequestContext(self, request)

    def run(
            self,
            host: str='127.0.0.1',
            port: int=5000,
            ssl: Optional[SSLContext]=None,
    ) -> None:
        run_app(self, host=host, port=port, ssl=ssl)

    def test_client(self) -> TestClient:
        return TestClient(self)

    def test_request_context(self, method: str, path: str) -> RequestContext:
        body: asyncio.Future = asyncio.Future()
        body.set_result(b'')
        return RequestContext(self, self.request_class(method, path, CIMultiDict(), body))

    def create_url_adapter(self, request: Optional[Request]) -> Optional[MapAdapter]:
        if request is not None:
            return self.url_map.bind_to_request(
                request.scheme, request.server_name, request.method, request.path,
            )

        if self.config['SERVER_NAME'] is not None:
            return self.url_map.bind(
                self.config['PREFERRED_URL_SCHEME'], self.config['SERVER_NAME'],
            )
        return None

    async def try_trigger_before_first_request_functions(self) -> None:
        if self._got_first_request:
            return
        with await self._first_request_lock:
            if self._got_first_request:
                return
            for function in self.before_first_request_funcs:
                await function()
            self._got_first_request = True

    async def make_default_options_response(self) -> Response:
        methods = _request_ctx_stack.top.url_adapter.allowed_methods()
        return self.response_class('', headers={'Allow': ', '.join(methods)})

    async def full_dispatch_request(
        self, request_context: Optional[RequestContext]=None,
    ) -> Response:
        """Adds pre and post processing to the request dispatching.

        Arguments:
            request_context: The request context, optional as Flask
                omits this argument.
        """
        await self.try_trigger_before_first_request_functions()
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
        functions = self.before_request_funcs[None]
        blueprint = request_.blueprint
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
    ) -> Response:
        """Turns the view response return value into a response.

        Arguments:
            result: The result of the request to finalize into a response.
            request_context: The request context, optional as Flask
                omits this argument.
        """
        response = await self.make_response(result)
        return await self.process_response(response, request_context)

    async def make_response(self, result: ResponseReturnValue) -> Response:
        """Make a Response from the result of the route handler.

        The result itself can either be:
          - A Response object (or subclass) .
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

        if isinstance(status_or_headers, (dict, list)):
            headers = status_or_headers
            status = None
        elif status_or_headers is not None:
            status = status_or_headers

        if not isinstance(value, Response):
            response = self.response_class(value, content_type='text/html')
        else:
            response = value

        if status is not None:
            response.status_code = status

        if headers is not None:
            response.headers.update(headers)

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
        functions = self.after_request_funcs[None]
        blueprint = request_.blueprint
        if blueprint is not None:
            functions = chain(functions, self.after_request_funcs[blueprint])  # type: ignore

        for function in functions:
            response = await function(response)

        session_ = (request_context or _request_ctx_stack.top).session
        if not self.session_interface.is_null_session(session_):
            response = self.save_session(session_, response)  # type: ignore
        return response

    async def handle_request(self, request: Request) -> Response:
        with self.request_context(request) as request_context:
            try:
                return await self.full_dispatch_request(request_context)
            except Exception as error:
                return await self.handle_exception(error)

    def __call__(self) -> 'Quart':
        # Required for Gunicorn compatibility.
        return self


def _ensure_coroutine(func: Callable) -> Callable:
    return func if asyncio.iscoroutinefunction(func) else asyncio.coroutine(func)


def _find_exception_handler(
        error: Exception, exception_handlers: Dict[Exception, Callable],
) -> Optional[Callable]:
    for exception, handler in exception_handlers.items():
        if isinstance(error, exception):  # type: ignore
            return handler
    return None


async def _default_error_handler(error: HTTPException) -> Response:
    return error.get_response()
