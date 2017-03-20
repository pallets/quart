from types import TracebackType
from typing import Any, Iterator, Optional, TYPE_CHECKING

from .exceptions import MethodNotAllowed, NotFound, RedirectRequired
from .globals import _app_ctx_stack, _request_ctx_stack
from .sessions import Session  # noqa
from .wrappers import Request

if TYPE_CHECKING:
    from .app import Quart  # noqa


class RequestContext:

    def __init__(self, app: 'Quart', request: Request) -> None:
        self.app = app
        self.request = request
        self.url_adapter = app.create_url_adapter(self.request)
        self.request.routing_exception = None
        self.session: Optional[Session] = None

        self.match_request()

    def match_request(self) -> None:
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


class AppContext:

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
    return _app_ctx_stack.top is not None


def has_request_context() -> bool:
    return _request_ctx_stack.top is not None


_sentinel = object()


class _AppCtxGlobals(object):

    def get(self, name: str, default: Optional[Any]=None) -> Any:
        return self.__dict__.get(name, default)

    def pop(self, name: str, default: Any=_sentinel) -> Any:
        if default is _sentinel:
            return self.__dict__.pop(name)
        else:
            return self.__dict__.pop(name, default)

    def setdefault(self, name: str, default: Any=None) -> Any:
        return self.__dict__.setdefault(name, default)

    def __contains__(self, item: Any) -> bool:
        return item in self.__dict__

    def __iter__(self) -> Iterator:
        return iter(self.__dict__)

    def __repr__(self) -> str:
        top = _app_ctx_stack.top
        if top is not None:
            return '<quart.g of %r>' % top.app.name
        return object.__repr__(self)
