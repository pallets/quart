from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from http.cookiejar import CookieJar
from typing import Any, AnyStr, AsyncGenerator, List, Optional, Tuple, TYPE_CHECKING, Union
from urllib.parse import unquote, urlencode
from urllib.request import Request as U2Request

from werkzeug.datastructures import Headers
from werkzeug.exceptions import BadRequest as WBadRequest
from werkzeug.http import dump_cookie

from .exceptions import BadRequest
from .json import dumps
from .wrappers import Request, Response

if TYPE_CHECKING:
    from .app import Quart  # noqa

sentinel = object()


class WebsocketResponse(Exception):
    def __init__(self, response: Response) -> None:
        super().__init__()
        self.response = response


class _TestingWebsocket:
    def __init__(self, remote_queue: asyncio.Queue) -> None:
        self.remote_queue = remote_queue
        self.local_queue: asyncio.Queue = asyncio.Queue()
        self.accepted = False
        self.task: Optional[asyncio.Future] = None

    async def receive(self) -> AnyStr:
        await self._check_for_response()
        return await self.local_queue.get()

    async def send(self, data: AnyStr) -> None:
        await self._check_for_response()
        await self.remote_queue.put(data)

    async def accept(self, headers: Headers, subprotocol: Optional[str]) -> None:
        self.accepted = True
        self.accept_headers = headers
        self.accept_subprotocol = subprotocol

    async def _check_for_response(self) -> None:
        await asyncio.sleep(0)  # Give serving task an opportunity to respond
        if self.task.done() and self.task.result() is not None:
            raise WebsocketResponse(self.task.result())


class _TestWrapper:
    def __init__(self, headers: Headers) -> None:
        self.headers = headers

    def get_all(self, name: str, default: Optional[Any] = None) -> List[str]:
        name = name.lower()
        result = []
        for key, value in self.headers:
            if key.lower() == name:
                result.append(value)
        return result or default or []


class _TestCookieJarResponse:
    def __init__(self, headers: Headers) -> None:
        self.headers = headers

    def info(self) -> _TestWrapper:
        return _TestWrapper(self.headers)


def make_test_headers_path_and_query_string(
    app: "Quart",
    path: str,
    headers: Optional[Union[dict, Headers]] = None,
    query_string: Optional[dict] = None,
) -> Tuple[Headers, str, bytes]:
    """Make the headers and path with defaults for testing.

    Arguments:
        app: The application to test against.
        path: The path to request. If the query_string argument is not
            defined this argument will be partitioned on a '?' with
            the following part being considered the query_string.
        headers: Initial headers to send.
        query_string: To send as a dictionary, alternatively the
            query_string can be determined from the path.
    """
    if headers is None:
        headers = Headers()
    elif isinstance(headers, Headers):
        headers = headers
    elif headers is not None:
        headers = Headers(headers)
    headers.setdefault("Remote-Addr", "127.0.0.1")
    headers.setdefault("User-Agent", "Quart")
    headers.setdefault("host", app.config["SERVER_NAME"] or "localhost")
    if "?" in path and query_string is not None:
        raise ValueError("Query string is defined in the path and as an argument")
    if query_string is None:
        path, _, query_string_raw = path.partition("?")
    else:
        query_string_raw = urlencode(query_string, doseq=True)
    query_string_bytes = query_string_raw.encode("ascii")
    return headers, unquote(path), query_string_bytes


def make_test_body_with_headers(
    data: Optional[AnyStr] = None,
    form: Optional[dict] = None,
    json: Any = sentinel,
    app: Optional["Quart"] = None,
) -> Tuple[bytes, Headers]:
    """Make the body bytes with associated headers.

    Arguments:
        data: Raw data to send in the request body.
        form: Data to send form encoded in the request body.
        json: Data to send json encoded in the request body.
    """
    if [json is not sentinel, form is not None, data is not None].count(True) > 1:
        raise ValueError("Quart test args 'json', 'form', and 'data' are mutually exclusive")

    request_data = b""

    headers = Headers()

    if isinstance(data, str):
        request_data = data.encode("utf-8")
    elif isinstance(data, bytes):
        request_data = data

    if json is not sentinel:
        request_data = dumps(json, app=app).encode("utf-8")
        headers["Content-Type"] = "application/json"

    if form is not None:
        request_data = urlencode(form).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"

    return request_data, headers


async def no_op_push(path: str, headers: Headers) -> None:
    """A push promise sender that does nothing.

    This is best used when creating Request instances for testing
    outside of the QuartClient. The Request instance must know what to
    do with push promises, and this gives it the option of doing
    nothing.
    """
    pass


class QuartClient:
    """A Client bound to an app for testing.

    This should be used to make requests and receive responses from
    the app for testing purposes. This is best used via
    :attr:`~quart.app.Quart.test_client` method.
    """

    def __init__(self, app: "Quart", use_cookies: bool = True) -> None:
        self.cookie_jar: Optional[CookieJar]
        if use_cookies:
            self.cookie_jar = CookieJar()
        else:
            self.cookie_jar = None
        self.app = app
        self.push_promises: List[Tuple[str, Headers]] = []

    async def open(
        self,
        path: str,
        *,
        method: str = "GET",
        headers: Optional[Union[dict, Headers]] = None,
        data: Optional[AnyStr] = None,
        form: Optional[dict] = None,
        query_string: Optional[dict] = None,
        json: Any = sentinel,
        scheme: str = "http",
        follow_redirects: bool = False,
        root_path: str = "",
        http_version: str = "1.1",
    ) -> Response:
        """Open a request to the app associated with this client.

        Arguments:
            path:
                The path to request. If the query_string argument is not
                defined this argument will be partitioned on a '?' with the
                following part being considered the query_string.
            method:
                The method to make the request with, defaults to 'GET'.
            headers:
                Headers to include in the request.
            data:
                Raw data to send in the request body.
            form:
                Data to send form encoded in the request body.
            query_string:
                To send as a dictionary, alternatively the query_string can be
                determined from the path.
            json:
                Data to send json encoded in the request body.
            scheme:
                The scheme to use in the request, default http.
            follow_redirects:
                Whether or not a redirect response should be followed, defaults
                to False.

        Returns:
            The response from the app handling the request.
        """
        response = await self._make_request(
            path, method, headers, data, form, query_string, json, scheme, root_path, http_version
        )
        if follow_redirects:
            while response.status_code >= 300 and response.status_code <= 399:
                # Most browsers respond to an HTTP 302 with a GET request to the new location,
                # despite what the HTTP spec says. HTTP 303 should always be responded to with
                # a GET request.
                if response.status_code == 302 or response.status_code == 303:
                    method = "GET"
                response = await self._make_request(
                    response.location,
                    method,
                    headers,
                    data,
                    form,
                    query_string,
                    json,
                    scheme,
                    root_path,
                    http_version,
                )
        return response

    async def _make_request(
        self,
        path: str,
        method: str = "GET",
        headers: Optional[Union[dict, Headers]] = None,
        data: Optional[AnyStr] = None,
        form: Optional[dict] = None,
        query_string: Optional[dict] = None,
        json: Any = sentinel,
        scheme: str = "http",
        root_path: str = "",
        http_version: str = "1.1",
    ) -> Response:
        headers, path, query_string_bytes = make_test_headers_path_and_query_string(
            self.app, path, headers, query_string
        )

        request_data, body_headers = make_test_body_with_headers(data, form, json, self.app)
        # Replace with headers.update(**body_headers) when Werkzeug
        # supports https://github.com/pallets/werkzeug/pull/1687
        for key, value in body_headers.items():
            headers[key] = value

        if self.cookie_jar is not None:
            for cookie in self.cookie_jar:
                headers.add("cookie", f"{cookie.name}={cookie.value}")

        request = self.app.request_class(
            method,
            scheme,
            path,
            query_string_bytes,
            headers,
            root_path,
            http_version,
            send_push_promise=self._send_push_promise,
        )
        request.body.set_result(request_data)
        response = await self._handle_request(request)
        if self.cookie_jar is not None:
            self.cookie_jar.extract_cookies(
                _TestCookieJarResponse(response.headers),  # type: ignore
                U2Request(request.url),
            )
        return response

    async def _handle_request(self, request: Request) -> Response:
        return await asyncio.ensure_future(self.app.handle_request(request))

    async def _send_push_promise(self, path: str, headers: Headers) -> None:
        self.push_promises.append((path, headers))

    async def delete(self, *args: Any, **kwargs: Any) -> Response:
        """Make a DELETE request.

        See :meth:`~quart.testing.QuartClient.open` for argument
        details.
        """
        return await self.open(*args, method="DELETE", **kwargs)

    async def get(self, *args: Any, **kwargs: Any) -> Response:
        """Make a GET request.

        See :meth:`~quart.testing.QuartClient.open` for argument
        details.
        """
        return await self.open(*args, method="GET", **kwargs)

    async def head(self, *args: Any, **kwargs: Any) -> Response:
        """Make a HEAD request.

        See :meth:`~quart.testing.QuartClient.open` for argument
        details.
        """
        return await self.open(*args, method="HEAD", **kwargs)

    async def options(self, *args: Any, **kwargs: Any) -> Response:
        """Make a OPTIONS request.

        See :meth:`~quart.testing.QuartClient.open` for argument
        details.
        """
        return await self.open(*args, method="OPTIONS", **kwargs)

    async def patch(self, *args: Any, **kwargs: Any) -> Response:
        """Make a PATCH request.

        See :meth:`~quart.testing.QuartClient.open` for argument
        details.
        """
        return await self.open(*args, method="PATCH", **kwargs)

    async def post(self, *args: Any, **kwargs: Any) -> Response:
        """Make a POST request.

        See :meth:`~quart.testing.QuartClient.open` for argument
        details.
        """
        return await self.open(*args, method="POST", **kwargs)

    async def put(self, *args: Any, **kwargs: Any) -> Response:
        """Make a PUT request.

        See :meth:`~quart.testing.QuartClient.open` for argument
        details.
        """
        return await self.open(*args, method="PUT", **kwargs)

    async def trace(self, *args: Any, **kwargs: Any) -> Response:
        """Make a TRACE request.

        See :meth:`~quart.testing.QuartClient.open` for argument
        details.
        """
        return await self.open(*args, method="TRACE", **kwargs)

    def set_cookie(
        self,
        server_name: str,
        key: str,
        value: str = "",
        max_age: Optional[Union[int, timedelta]] = None,
        expires: Optional[Union[int, float, datetime]] = None,
        path: str = "/",
        domain: Optional[str] = None,
        secure: bool = False,
        httponly: bool = False,
        samesite: str = None,
        charset: str = "utf-8",
    ) -> None:
        """Set a cookie in the cookie jar.

        The arguments are the standard cookie morsels and this is a
        wrapper around the stdlib SimpleCookie code.
        """
        cookie = dump_cookie(  # type: ignore
            key,
            value=value,
            max_age=max_age,
            expires=expires,
            path=path,
            domain=domain,
            secure=secure,
            httponly=httponly,
            charset=charset,
            samesite=samesite,
        )
        self.cookie_jar.extract_cookies(
            _TestCookieJarResponse(Headers([("set-cookie", cookie)])),  # type: ignore
            U2Request(f"http://{server_name}{path}"),
        )

    def delete_cookie(
        self, server_name: str, key: str, path: str = "/", domain: Optional[str] = None
    ) -> None:
        """Delete a cookie (set to expire immediately)."""
        self.set_cookie(server_name, key, expires=0, max_age=0, path=path, domain=domain)

    @asynccontextmanager
    async def websocket(
        self,
        path: str,
        *,
        headers: Optional[Union[dict, Headers]] = None,
        query_string: Optional[dict] = None,
        scheme: str = "ws",
        subprotocols: Optional[List[str]] = None,
        root_path: str = "",
        http_version: str = "1.1",
    ) -> AsyncGenerator[_TestingWebsocket, None]:
        headers, path, query_string_bytes = make_test_headers_path_and_query_string(
            self.app, path, headers, query_string
        )
        queue: asyncio.Queue = asyncio.Queue()
        websocket_client = _TestingWebsocket(queue)

        subprotocols = subprotocols or []
        websocket = self.app.websocket_class(
            path,
            query_string_bytes,
            scheme,
            headers,
            root_path,
            http_version,
            subprotocols,
            queue.get,
            websocket_client.local_queue.put,
            websocket_client.accept,
        )
        adapter = self.app.create_url_adapter(websocket)
        try:
            adapter.match()
        except WBadRequest:
            raise BadRequest()

        websocket_client.task = asyncio.ensure_future(self.app.handle_websocket(websocket))

        try:
            yield websocket_client
        finally:
            websocket_client.task.cancel()
