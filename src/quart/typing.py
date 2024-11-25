from __future__ import annotations

import os
import sys
from collections.abc import AsyncGenerator
from collections.abc import Awaitable
from collections.abc import Iterator
from collections.abc import Mapping
from collections.abc import Sequence
from contextlib import AbstractAsyncContextManager
from datetime import datetime
from datetime import timedelta
from http.cookiejar import CookieJar
from types import TracebackType
from typing import Any
from typing import AnyStr
from typing import Callable
from typing import Optional
from typing import TYPE_CHECKING
from typing import Union

from hypercorn.typing import ASGIReceiveCallable
from hypercorn.typing import ASGISendCallable
from hypercorn.typing import HTTPScope
from hypercorn.typing import LifespanScope
from hypercorn.typing import WebsocketScope

from .datastructures import FileStorage

if sys.version_info >= (3, 10):
    from typing import Protocol
else:
    from typing_extensions import Protocol

if TYPE_CHECKING:
    from werkzeug.datastructures import Authorization  # noqa: F401
    from werkzeug.datastructures import Headers  # noqa: F401
    from werkzeug.wrappers import Response as WerkzeugResponse

    from .app import Quart
    from .sessions import SessionMixin
    from .wrappers.response import Response  # noqa: F401

FilePath = Union[bytes, str, os.PathLike]

# The possible types that are directly convertible or are a Response object.
ResponseValue = Union[
    "Response",
    "WerkzeugResponse",
    bytes,
    str,
    Mapping[str, Any],  # any jsonify-able dict
    list[Any],  # any jsonify-able list
    Iterator[bytes],
    Iterator[str],
]
StatusCode = int

# the possible types for an individual HTTP header
HeaderName = str
HeaderValue = Union[str, list[str], tuple[str, ...]]

# the possible types for HTTP headers
HeadersValue = Union[
    "Headers",
    Mapping[HeaderName, HeaderValue],
    Sequence[tuple[HeaderName, HeaderValue]],
]

# The possible types returned by a route function.
ResponseReturnValue = Union[
    ResponseValue,
    tuple[ResponseValue, HeadersValue],
    tuple[ResponseValue, StatusCode],
    tuple[ResponseValue, StatusCode, HeadersValue],
]

ResponseTypes = Union["Response", "WerkzeugResponse"]

AppOrBlueprintKey = Optional[str]  # The App key is None, whereas blueprints are named
AfterRequestCallable = Union[
    Callable[[ResponseTypes], ResponseTypes],
    Callable[[ResponseTypes], Awaitable[ResponseTypes]],
]
AfterServingCallable = Union[Callable[[], None], Callable[[], Awaitable[None]]]
AfterWebsocketCallable = Union[
    Callable[[Optional[ResponseTypes]], Optional[ResponseTypes]],
    Callable[[Optional[ResponseTypes]], Awaitable[Optional[ResponseTypes]]],
]
BeforeRequestCallable = Union[
    Callable[[], Optional[ResponseReturnValue]],
    Callable[[], Awaitable[Optional[ResponseReturnValue]]],
]
BeforeServingCallable = Union[Callable[[], None], Callable[[], Awaitable[None]]]
BeforeWebsocketCallable = Union[
    Callable[[], Optional[ResponseReturnValue]],
    Callable[[], Awaitable[Optional[ResponseReturnValue]]],
]
ErrorHandlerCallable = Union[
    Callable[[Any], ResponseReturnValue],
    Callable[[Any], Awaitable[ResponseReturnValue]],
]
ShellContextProcessorCallable = Callable[[], dict[str, Any]]
TeardownCallable = Union[
    Callable[[Optional[BaseException]], None],
    Callable[[Optional[BaseException]], Awaitable[None]],
]
TemplateContextProcessorCallable = Union[
    Callable[[], dict[str, Any]], Callable[[], Awaitable[dict[str, Any]]]
]
TemplateFilterCallable = Callable[[Any], Any]
TemplateGlobalCallable = Callable[[Any], Any]
TemplateTestCallable = Callable[[Any], bool]
URLDefaultCallable = Callable[[str, dict], None]
URLValuePreprocessorCallable = Callable[[Optional[str], Optional[dict]], None]
WhileServingCallable = Callable[[], AsyncGenerator[None, None]]

RouteCallable = Union[
    Callable[..., ResponseReturnValue],
    Callable[..., Awaitable[ResponseReturnValue]],
]
WebsocketCallable = Union[
    Callable[..., Optional[ResponseReturnValue]],
    Callable[..., Awaitable[Optional[ResponseReturnValue]]],
]


class ASGIHTTPProtocol(Protocol):
    def __init__(self, app: Quart, scope: HTTPScope) -> None: ...

    async def __call__(
        self, receive: ASGIReceiveCallable, send: ASGISendCallable
    ) -> None: ...


class ASGILifespanProtocol(Protocol):
    def __init__(self, app: Quart, scope: LifespanScope) -> None: ...

    async def __call__(
        self, receive: ASGIReceiveCallable, send: ASGISendCallable
    ) -> None: ...


class ASGIWebsocketProtocol(Protocol):
    def __init__(self, app: Quart, scope: WebsocketScope) -> None: ...

    async def __call__(
        self, receive: ASGIReceiveCallable, send: ASGISendCallable
    ) -> None: ...


class TestHTTPConnectionProtocol(Protocol):
    push_promises: list[tuple[str, Headers]]

    def __init__(
        self, app: Quart, scope: HTTPScope, _preserve_context: bool = False
    ) -> None: ...

    async def send(self, data: bytes) -> None: ...

    async def send_complete(self) -> None: ...

    async def receive(self) -> bytes: ...

    async def disconnect(self) -> None: ...

    async def __aenter__(self) -> TestHTTPConnectionProtocol: ...

    async def __aexit__(
        self, exc_type: type, exc_value: BaseException, tb: TracebackType
    ) -> None: ...

    async def as_response(self) -> Response: ...


class TestWebsocketConnectionProtocol(Protocol):
    def __init__(self, app: Quart, scope: WebsocketScope) -> None: ...

    async def __aenter__(self) -> TestWebsocketConnectionProtocol: ...

    async def __aexit__(
        self, exc_type: type, exc_value: BaseException, tb: TracebackType
    ) -> None: ...

    async def receive(self) -> AnyStr: ...

    async def send(self, data: AnyStr) -> None: ...

    async def receive_json(self) -> Any: ...

    async def send_json(self, data: Any) -> None: ...

    async def close(self, code: int) -> None: ...

    async def disconnect(self) -> None: ...


class TestClientProtocol(Protocol):
    app: Quart
    cookie_jar: CookieJar | None
    http_connection_class: type[TestHTTPConnectionProtocol]
    push_promises: list[tuple[str, Headers]]
    websocket_connection_class: type[TestWebsocketConnectionProtocol]

    def __init__(self, app: Quart, use_cookies: bool = True) -> None: ...

    async def open(
        self,
        path: str,
        *,
        method: str = "GET",
        headers: dict | Headers | None = None,
        data: AnyStr | None = None,
        form: dict | None = None,
        files: dict[str, FileStorage] | None = None,
        query_string: dict | None = None,
        json: Any,
        scheme: str = "http",
        follow_redirects: bool = False,
        root_path: str = "",
        http_version: str = "1.1",
        scope_base: dict | None = None,
        auth: Authorization | tuple[str, str] | None = None,
        subdomain: str | None = None,
    ) -> Response: ...

    def request(
        self,
        path: str,
        *,
        method: str = "GET",
        headers: dict | Headers | None = None,
        query_string: dict | None = None,
        scheme: str = "http",
        root_path: str = "",
        http_version: str = "1.1",
        scope_base: dict | None = None,
        auth: Authorization | tuple[str, str] | None = None,
        subdomain: str | None = None,
    ) -> TestHTTPConnectionProtocol: ...

    def websocket(
        self,
        path: str,
        *,
        headers: dict | Headers | None = None,
        query_string: dict | None = None,
        scheme: str = "ws",
        subprotocols: list[str] | None = None,
        root_path: str = "",
        http_version: str = "1.1",
        scope_base: dict | None = None,
        auth: Authorization | tuple[str, str] | None = None,
        subdomain: str | None = None,
    ) -> TestWebsocketConnectionProtocol: ...

    async def delete(self, *args: Any, **kwargs: Any) -> Response: ...

    async def get(self, *args: Any, **kwargs: Any) -> Response: ...

    async def head(self, *args: Any, **kwargs: Any) -> Response: ...

    async def options(self, *args: Any, **kwargs: Any) -> Response: ...

    async def patch(self, *args: Any, **kwargs: Any) -> Response: ...

    async def post(self, *args: Any, **kwargs: Any) -> Response: ...

    async def put(self, *args: Any, **kwargs: Any) -> Response: ...

    async def trace(self, *args: Any, **kwargs: Any) -> Response: ...

    def set_cookie(
        self,
        server_name: str,
        key: str,
        value: str = "",
        max_age: int | timedelta | None = None,
        expires: int | float | datetime | None = None,
        path: str = "/",
        domain: str | None = None,
        secure: bool = False,
        httponly: bool = False,
        samesite: str = None,
        charset: str = "utf-8",
    ) -> None: ...

    def delete_cookie(
        self, server_name: str, key: str, path: str = "/", domain: str | None = None
    ) -> None: ...

    def session_transaction(
        self,
        path: str = "/",
        *,
        method: str = "GET",
        headers: dict | Headers | None = None,
        query_string: dict | None = None,
        scheme: str = "http",
        data: AnyStr | None = None,
        form: dict | None = None,
        json: Any = None,
        root_path: str = "",
        http_version: str = "1.1",
    ) -> AbstractAsyncContextManager[SessionMixin]: ...

    async def __aenter__(self) -> TestClientProtocol: ...

    async def __aexit__(
        self, exc_type: type, exc_value: BaseException, tb: TracebackType
    ) -> None: ...


class TestAppProtocol(Protocol):
    def __init__(self, app: Quart) -> None: ...

    def test_client(self) -> TestClientProtocol: ...

    async def startup(self) -> None: ...

    async def shutdown(self) -> None: ...

    async def __aenter__(self) -> TestAppProtocol: ...

    async def __aexit__(
        self, exc_type: type, exc_value: BaseException, tb: TracebackType
    ) -> None: ...


class Event(Protocol):
    def is_set(self) -> bool: ...

    def set(self) -> None: ...
