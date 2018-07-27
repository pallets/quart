import asyncio
from contextlib import contextmanager
from datetime import datetime, timedelta
from http.cookies import SimpleCookie
from json import dumps
from typing import Any, AnyStr, Generator, Optional, Tuple, TYPE_CHECKING, Union
from urllib.parse import urlencode

from .datastructures import CIMultiDict
from .exceptions import BadRequest
from .utils import create_cookie
from .wrappers import Request, Response, Websocket

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

    async def receive(self) -> bytes:
        await self._check_for_response()
        return await self.local_queue.get()

    async def send(self, data: bytes) -> None:
        await self._check_for_response()
        await self.remote_queue.put(data)

    async def accept(self) -> None:
        self.accepted = True

    async def _check_for_response(self) -> None:
        await asyncio.sleep(0)  # Give serving task an opportunity to respond
        if self.task.done() and self.task.result() is not None:
            raise WebsocketResponse(self.task.result())


def make_test_headers_path_and_query_string(
        app: 'Quart',
        path: str,
        headers: Optional[Union[dict, CIMultiDict]]=None,
        query_string: Optional[dict]=None,
) -> Tuple[CIMultiDict, str, bytes]:
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
        headers = CIMultiDict()
    elif isinstance(headers, CIMultiDict):
        headers = headers
    elif headers is not None:
        headers = CIMultiDict(headers)
    headers.setdefault('Remote-Addr', '127.0.0.1')
    headers.setdefault('User-Agent', 'Quart')
    headers.setdefault('host', app.config['SERVER_NAME'] or 'localhost')
    if '?' in path and query_string is not None:
        raise ValueError('Query string is defined in the path and as an argument')
    if query_string is None:
        path, _, query_string_raw = path.partition('?')
    else:
        query_string_raw = urlencode(query_string, doseq=True)
    query_string_bytes = query_string_raw.encode('ascii')
    return headers, path, query_string_bytes  # type: ignore


class QuartClient:
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
            path: The path to request. If the query_string argument is
                not defined this argument will be partitioned on a '?'
                with the following part being considered the
                query_string.
            method: The method to make the request with, defaults GET.
            headers: Headers to include in the request.
            data: Raw data to send in the request body.
            form: Data to send form encoded in the request body.
            query_string: To send as a dictionary, alternatively the
                query_string can be determined from the path.
            json: Data to send json encoded in the request body.
            scheme: The scheme to use in the request, default http.

        Returns:
            The response from the app handling the request.
        """
        headers, path, query_string_bytes = make_test_headers_path_and_query_string(
            self.app, path, headers, query_string,
        )

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

        request = Request(method, scheme, path, query_string_bytes, headers)  # type: ignore
        request.body.set_result(request_data)
        response = await asyncio.ensure_future(self.app.handle_request(request))
        if self.cookie_jar is not None and 'Set-Cookie' in response.headers:
            self.cookie_jar.load(";".join(response.headers.getall('Set-Cookie')))
        return response

    async def delete(self, *args: Any, **kwargs: Any) -> Response:
        """Make a DELETE request.

        See :meth:`~quart.testing.QuartClient.open` for argument
        details.
        """
        return await self.open(*args, method='DELETE', **kwargs)

    async def get(self, *args: Any, **kwargs: Any) -> Response:
        """Make a GET request.

        See :meth:`~quart.testing.QuartClient.open` for argument
        details.
        """
        return await self.open(*args, method='GET', **kwargs)

    async def head(self, *args: Any, **kwargs: Any) -> Response:
        """Make a HEAD request.

        See :meth:`~quart.testing.QuartClient.open` for argument
        details.
        """
        return await self.open(*args, method='HEAD', **kwargs)

    async def options(self, *args: Any, **kwargs: Any) -> Response:
        """Make a OPTIONS request.

        See :meth:`~quart.testing.QuartClient.open` for argument
        details.
        """
        return await self.open(*args, method='OPTIONS', **kwargs)

    async def patch(self, *args: Any, **kwargs: Any) -> Response:
        """Make a PATCH request.

        See :meth:`~quart.testing.QuartClient.open` for argument
        details.
        """
        return await self.open(*args, method='PATCH', **kwargs)

    async def post(self, *args: Any, **kwargs: Any) -> Response:
        """Make a POST request.

        See :meth:`~quart.testing.QuartClient.open` for argument
        details.
        """
        return await self.open(*args, method='POST', **kwargs)

    async def put(self, *args: Any, **kwargs: Any) -> Response:
        """Make a PUT request.

        See :meth:`~quart.testing.QuartClient.open` for argument
        details.
        """
        return await self.open(*args, method='PUT', **kwargs)

    async def trace(self, *args: Any, **kwargs: Any) -> Response:
        """Make a TRACE request.

        See :meth:`~quart.testing.QuartClient.open` for argument
        details.
        """
        return await self.open(*args, method='TRACE', **kwargs)

    def set_cookie(
            self,
            key: str,
            value: str='',
            max_age: Optional[Union[int, timedelta]]=None,
            expires: Optional[Union[int, float, datetime]]=None,
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
        headers, path, query_string_bytes = make_test_headers_path_and_query_string(
            self.app, path, headers, query_string,
        )
        queue: asyncio.Queue = asyncio.Queue()
        websocket_client = _TestingWebsocket(queue)

        websocket = Websocket(
            path, query_string_bytes, scheme, headers, queue, websocket_client.local_queue.put,
            websocket_client.accept,
        )
        adapter = self.app.create_url_adapter(websocket)
        url_rule, _ = adapter.match()
        if not url_rule.is_websocket:
            raise BadRequest()

        websocket_client.task = asyncio.ensure_future(self.app.handle_websocket(websocket))

        try:
            yield websocket_client
        finally:
            websocket_client.task.cancel()
