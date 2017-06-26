import asyncio
from datetime import datetime, timedelta
from http.cookies import SimpleCookie
from json import dumps
from typing import Any, Optional, TYPE_CHECKING, Union
from urllib.parse import urlencode

from multidict import CIMultiDict

from .utils import create_cookie
from .wrappers import Request, Response

if TYPE_CHECKING:
    from .app import Quart  # noqa

sentinel = object()


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
        form: Optional[dict]=None,
        query_string: Optional[dict]=None,
        json: Any=sentinel,
    ) -> Response:
        """Open a request to the app associated with this client.

        Arguemnts:
            path: The path to make the request too.
            method: The method to make the request with, defaults GET.
            headers: Headers to include in the request.
            form: Data to send form encoded in the request body.
            query_string: Data to send via query string.
            json: Data to send json encoded in the request body.

        Returns:
            The response from the app handling the request.
        """
        if headers is None:
            headers = CIMultiDict()
        elif isinstance(headers, CIMultiDict):
            headers = headers
        elif headers is not None:
            headers = CIMultiDict(headers)
        body: asyncio.Future = asyncio.Future()
        if json is not sentinel and form is not None:
            raise ValueError('Cannot send JSON and form data in the body')
        elif json is not sentinel:
            data = dumps(json).encode('utf-8')
            headers['Content-Type'] = 'application/json'
        elif form is not None:
            data = urlencode(form).encode('utf-8')
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
        else:
            data = b''
        body.set_result(data)
        if query_string is not None:
            path = f"{path}?{urlencode(query_string)}"
        if self.cookie_jar is not None:
            headers.add('Cookie', self.cookie_jar.output(header=''))  # type: ignore
        request = Request(method, path, headers, body)
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
