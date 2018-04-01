import asyncio
from contextlib import contextmanager
from datetime import datetime, timedelta
from http.cookies import SimpleCookie
from json import dumps
from typing import Any, AnyStr, Generator, Optional, Tuple, TYPE_CHECKING, Union
from urllib.parse import ParseResult, urlencode, urlunparse

from .datastructures import CIMultiDict
from .exceptions import BadRequest
from .utils import create_cookie
from .wrappers import Request, Response, Websocket

if TYPE_CHECKING:
    from .app import Quart  # noqa

sentinel = object()


class _TestingWebsocket:

    def __init__(self, remote_queue: asyncio.Queue) -> None:
        self.remote_queue = remote_queue
        self.local_queue: asyncio.Queue = asyncio.Queue()

    async def receive(self) -> bytes:
        return await self.local_queue.get()

    async def send(self, data: bytes) -> None:
        await self.remote_queue.put(data)
        await asyncio.sleep(0)


def make_test_headers_and_path(
        app: 'Quart',
        path: str,
        headers: Optional[Union[dict, CIMultiDict]]=None,
        query_string: Optional[dict]=None,
) -> Tuple[CIMultiDict, str]:
    """Make the headers and path with defaults for testing.

    Arguments:
        app: The application to test against.
        path: The path to request.
        headers: Initial headers to send.
        query_string: To send as a dictionary.
    """
    if headers is None:
        headers = CIMultiDict()
    elif isinstance(headers, CIMultiDict):
        headers = headers
    elif headers is not None:
        headers = CIMultiDict(headers)
    headers.setdefault('Remote-Addr', '127.0.0.1')
    headers.setdefault('User-Agent', 'Quart')
    headers.setdefault('host', app.config['SERVER_NAME'] or 'localhost')
    if query_string is not None:
        path = urlunparse(ParseResult(
            scheme='', netloc='', params='', path=path, query=urlencode(query_string),
            fragment='',
        ))
    return headers, path  # type: ignore


class TestClient:
    """A Client bound to an app for testing.

    This should be used to make requests and receive responses from
    the app for testing purposes. This is best used via
    :attr:`~quart.app.Quart.test_client` method.
    """

    def __init__(self, app: 'Quart', use_cookies: bool=True) -> None:
        if use_cookies:
            self.cookie_jar = SimpleCookie()  # type: ignore
        else:
            self.cookie_jar = None
        self.app = app

    async def open(
            self,
            path: str,
            *,
            method: str='GET',
            headers: Optional[Union[dict, CIMultiDict]]=None,
            data: AnyStr=None,
            form: Optional[dict]=None,
            query_string: Optional[dict]=None,
            json: Any=sentinel,
            scheme: str='http',
    ) -> Response:
        """Open a request to the app associated with this client.

        Arguemnts:
            path: The path to make the request too.
            method: The method to make the request with, defaults GET.
            headers: Headers to include in the request.
            data: Raw data to send in the request body.
            form: Data to send form encoded in the request body.
            query_string: Data to send via query string.
            json: Data to send json encoded in the request body.
            scheme: The scheme to use in the request, default http.

        Returns:
            The response from the app handling the request.
        """
        headers, path = make_test_headers_and_path(self.app, path, headers, query_string)

        if [json is not sentinel, form is not None, data is not None].count(True) > 1:
            raise ValueError("Quart test args 'json', 'form', and 'data' are mutually exclusive")

        request_data = b''

        if isinstance(data, str):
            request_data = data.encode('utf-8')
        elif isinstance(data, bytes):
            request_data = data

        if json is not sentinel:
            request_data = dumps(json).encode('utf-8')
            headers['Content-Type'] = 'application/json'

        if form is not None:
            request_data = urlencode(form).encode('utf-8')
            headers['Content-Type'] = 'application/x-www-form-urlencoded'

        if self.cookie_jar is not None:
            headers.add('Cookie', self.cookie_jar.output(header=''))  # type: ignore

        request = Request(method, scheme, path, headers)  # type: ignore
        request.body.set_result(request_data)
        response = await asyncio.ensure_future(self.app.handle_request(request))
        if self.cookie_jar is not None and 'Set-Cookie' in response.headers:
            self.cookie_jar.load(";".join(response.headers.getall('Set-Cookie')))
        return response

    async def delete(self, *args: Any, **kwargs: Any) -> Response:
        """Make a DELETE request.

        See :meth:`~quart.testing.TestClient.open` for argument
        details.
        """
        return await self.open(*args, method='DELETE', **kwargs)

    async def get(self, *args: Any, **kwargs: Any) -> Response:
        """Make a GET request.

        See :meth:`~quart.testing.TestClient.open` for argument
        details.
        """
        return await self.open(*args, method='GET', **kwargs)

    async def head(self, *args: Any, **kwargs: Any) -> Response:
        """Make a HEAD request.

        See :meth:`~quart.testing.TestClient.open` for argument
        details.
        """
        return await self.open(*args, method='HEAD', **kwargs)

    async def options(self, *args: Any, **kwargs: Any) -> Response:
        """Make a OPTIONS request.

        See :meth:`~quart.testing.TestClient.open` for argument
        details.
        """
        return await self.open(*args, method='OPTIONS', **kwargs)

    async def patch(self, *args: Any, **kwargs: Any) -> Response:
        """Make a PATCH request.

        See :meth:`~quart.testing.TestClient.open` for argument
        details.
        """
        return await self.open(*args, method='PATCH', **kwargs)

    async def post(self, *args: Any, **kwargs: Any) -> Response:
        """Make a POST request.

        See :meth:`~quart.testing.TestClient.open` for argument
        details.
        """
        return await self.open(*args, method='POST', **kwargs)

    async def put(self, *args: Any, **kwargs: Any) -> Response:
        """Make a PUT request.

        See :meth:`~quart.testing.TestClient.open` for argument
        details.
        """
        return await self.open(*args, method='PUT', **kwargs)

    async def trace(self, *args: Any, **kwargs: Any) -> Response:
        """Make a TRACE request.

        See :meth:`~quart.testing.TestClient.open` for argument
        details.
        """
        return await self.open(*args, method='TRACE', **kwargs)

    def set_cookie(
            self,
            key: str,
            value: str='',
            max_age: Optional[Union[int, timedelta]]=None,
            expires: Optional[datetime]=None,
            path: str='/',
            domain: Optional[str]=None,
            secure: bool=False,
            httponly: bool=False,
    ) -> None:
        """Set a cookie in the cookie jar.

        The arguments are the standard cookie morsels and this is a
        wrapper around the stdlib SimpleCookie code.
        """
        cookie = create_cookie(key, value, max_age, expires, path, domain, secure, httponly)
        self.cookie_jar = cookie

    def delete_cookie(self, key: str, path: str='/', domain: Optional[str]=None) -> None:
        """Delete a cookie (set to expire immediately)."""
        self.set_cookie(key, expires=datetime.utcnow(), max_age=0, path=path, domain=domain)

    @contextmanager
    def websocket(
            self,
            path: str,
            *,
            headers: Optional[Union[dict, CIMultiDict]]=None,
            query_string: Optional[dict]=None,
            scheme: str='http',
    ) -> Generator[_TestingWebsocket, None, None]:
        headers, path = make_test_headers_and_path(self.app, path, headers, query_string)
        queue: asyncio.Queue = asyncio.Queue()
        websocket_client = _TestingWebsocket(queue)
        websocket = Websocket(
            path, scheme, headers, queue, websocket_client.local_queue.put_nowait, lambda: None,
        )
        adapter = self.app.create_url_adapter(websocket)
        url_rule, _ = adapter.match()
        if not url_rule.is_websocket:
            raise BadRequest()

        task = asyncio.ensure_future(self.app.handle_websocket(websocket))

        try:
            yield websocket_client
        finally:
            task.cancel()
