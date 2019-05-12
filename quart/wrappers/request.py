import asyncio
import io
from cgi import FieldStorage, parse_header
from typing import (
    Any, AnyStr, Awaitable, Callable, Generator, List, Optional, TYPE_CHECKING, Union,
)
from urllib.parse import parse_qs

from ._base import BaseRequestWebsocket, JSONMixin
from ..datastructures import CIMultiDict, FileStorage, Headers, MultiDict

if TYPE_CHECKING:
    from ..routing import Rule  # noqa

SERVER_PUSH_HEADERS_TO_COPY = {
    "accept", "accept-encoding", "accept-language", "cache-control", "user-agent",
}


class Body:
    """A request body container.

    The request body can either be iterated over and consumed in parts
    (without building up memory usage) or awaited.

    .. code-block:: python

        async for data in body:
            ...
        # or simply
        complete = await body

    Note: It is not possible to iterate over the data and then await
    it.
    """

    def __init__(
            self, expected_content_length: Optional[int], max_content_length: Optional[int],
    ) -> None:
        self._data = bytearray()
        self._complete: asyncio.Event = asyncio.Event()
        self._has_data: asyncio.Event = asyncio.Event()
        self._max_content_length = max_content_length
        # Exceptions must be raised within application (not ASGI)
        # calls, this is achieved by having the ASGI methods set this
        # to an exception on error.
        self._must_raise: Optional[Exception] = None
        if (
                expected_content_length is not None and max_content_length is not None
                and expected_content_length > max_content_length
        ):
            from ..exceptions import RequestEntityTooLarge  # noqa Avoiding circular import
            self._must_raise = RequestEntityTooLarge()

    def __aiter__(self) -> 'Body':
        return self

    async def __anext__(self) -> bytes:
        if self._must_raise is not None:
            raise self._must_raise

        # if we got all of the data in the first shot, then self._complete is
        # set and self._has_data will not get set again, so skip the await
        # if we already have completed everything
        if not self._complete.is_set():
            await self._has_data.wait()

        if self._complete.is_set() and len(self._data) == 0:
            raise StopAsyncIteration()

        data = bytes(self._data)
        self._data.clear()
        self._has_data.clear()
        return data

    def __await__(self) -> Generator[Any, None, Any]:
        # Must check the _must_raise before and after waiting on the
        # completion event as it may change whilst waiting and the
        # event may not be set if there is already an issue.

        if self._must_raise is not None:
            raise self._must_raise

        yield from self._complete.wait().__await__()

        if self._must_raise is not None:
            raise self._must_raise
        return bytes(self._data)

    def append(self, data: bytes) -> None:
        if data == b'' or self._must_raise is not None:
            return
        self._data.extend(data)
        self._has_data.set()
        if self._max_content_length is not None and len(self._data) > self._max_content_length:
            from ..exceptions import RequestEntityTooLarge  # noqa Avoiding circular import
            self._must_raise = RequestEntityTooLarge()
            self.set_complete()

    def set_complete(self) -> None:
        self._complete.set()
        self._has_data.set()

    def set_result(self, data: bytes) -> None:
        """Convienience method, mainly for testing."""
        self.append(data)
        self.set_complete()


class Request(BaseRequestWebsocket, JSONMixin):
    """This class represents a request.

    It can be subclassed and the subclassed used in preference by
    replacing the :attr:`~quart.Quart.request_class` with your
    subclass.

    Attributes:
        body_class: The class to store the body data within.
    """
    body_class = Body

    def __init__(
            self,
            method: str,
            scheme: str,
            path: str,
            query_string: bytes,
            headers: CIMultiDict,
            *,
            max_content_length: Optional[int]=None,
            body_timeout: Optional[int]=None,
            send_push_promise: Callable[[str, Headers], Awaitable[None]],
    ) -> None:
        """Create a request object.

        Arguments:
            method: The HTTP verb.
            scheme: The scheme used for the request.
            path: The full unquoted path of the request.
            query_string: The raw bytes for the query string part.
            headers: The request headers.
            body: An awaitable future for the body data i.e.
                ``data = await body``
            max_content_length: The maximum length in bytes of the
                body (None implies no limit in Quart).
            body_timeout: The maximum time (seconds) to wait for the
                body before timing out.
            send_push_promise: An awaitable to send a push promise based
                off of this request (HTTP/2 feature).
        """
        super().__init__(method, scheme, path, query_string, headers)
        self.body_timeout = body_timeout
        self.body = self.body_class(self.content_length, max_content_length)
        self._form: Optional[MultiDict] = None
        self._files: Optional[MultiDict] = None
        self._send_push_promise = send_push_promise

    async def get_data(self, raw: bool=True) -> AnyStr:
        """The request body data."""
        try:
            body_future = asyncio.ensure_future(self.body)
            raw_data = await asyncio.wait_for(body_future, timeout=self.body_timeout)
        except asyncio.TimeoutError:
            body_future.cancel()
            from ..exceptions import RequestTimeout  # noqa Avoiding circular import
            raise RequestTimeout()

        if raw:
            return raw_data
        else:
            return raw_data.decode(self.charset)

    @property
    async def data(self) -> bytes:
        return await self.get_data()

    @property
    async def values(self) -> MultiDict:
        result = MultiDict()
        result.update(self.args)
        for key, value in (await self.form).items():
            result.add(key, value)
        return result

    @property
    async def form(self) -> MultiDict:
        """The parsed form encoded data.

        Note file data is present in the :attr:`files`.
        """
        if self._form is None:
            await self._load_form_data()
        return self._form

    @property
    async def files(self) -> MultiDict:
        """The parsed files.

        This will return an empty multidict unless the request
        mimetype was ``enctype="multipart/form-data"`` and the method
        POST, PUT, or PATCH.
        """
        if self._files is None:
            await self._load_form_data()
        return self._files

    async def _load_form_data(self) -> None:
        raw_data = await self.body
        self._form = MultiDict()
        self._files = MultiDict()
        content_header = self.content_type
        if content_header is None:
            return
        content_type, parameters = parse_header(content_header)
        if content_type == 'application/x-www-form-urlencoded':
            try:
                data = raw_data.decode(parameters.get("charset", "utf-8"))
            except UnicodeDecodeError:
                from ..exceptions import BadRequest  # noqa Avoiding circular import
                raise BadRequest()
            for key, values in parse_qs(data, keep_blank_values=True).items():
                for value in values:
                    self._form.add(key, value)
        elif content_type == 'multipart/form-data':
            field_storage = FieldStorage(
                io.BytesIO(raw_data), headers=self.headers,
                environ={'REQUEST_METHOD': 'POST'}, limit=len(raw_data),
            )
            for key in field_storage:  # type: ignore
                field_storage_key = field_storage[key]
                if isinstance(field_storage_key, list):
                    for item in field_storage_key:
                        self._load_field_storage(key, item)
                else:
                    self._load_field_storage(key, field_storage_key)

    def _load_field_storage(self, key: str, field_storage: FieldStorage) -> None:
        if isinstance(field_storage, FieldStorage) and field_storage.filename is not None:
            self._files.add(
                key, FileStorage(  # type: ignore
                    io.BytesIO(field_storage.file.read()), field_storage.filename,
                    field_storage.name, field_storage.type, field_storage.headers,  # type: ignore # noqa: E501
                ),
            )
        else:
            self._form.add(key, field_storage.value)

    @property
    def content_encoding(self) -> Optional[str]:
        return self.headers.get('Content-Encoding')

    @property
    def content_length(self) -> Optional[int]:
        if 'Content-Length' in self.headers:
            return int(self.headers['Content-Length'])
        else:
            return None

    @property
    def content_md5(self) -> Optional[str]:
        return self.headers.get('Content-md5')

    @property
    def content_type(self) -> Optional[str]:
        return self.headers.get('Content-Type')

    async def _load_json_data(self) -> str:
        """Return the data after decoding."""
        return await self.get_data(raw=False)

    async def send_push_promise(self, path: str) -> None:
        headers = Headers()
        for name in SERVER_PUSH_HEADERS_TO_COPY:
            for value in self.headers.getlist(name):
                headers.add(name, value)
        await self._send_push_promise(path, headers)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.method}, {self.path})"


class Websocket(BaseRequestWebsocket):

    def __init__(
            self,
            path: str,
            query_string: bytes,
            scheme: str,
            headers: CIMultiDict,
            subprotocols: List[str],
            receive: Callable,
            send: Callable,
            accept: Callable,
    ) -> None:
        """Create a request object.

        Arguments:
            path: The full unquoted path of the request.
            query_string: The raw bytes for the query string part.
            scheme: The scheme used for the request.
            headers: The request headers.
            subprotocols: The subprotocols requested.
            receive: Returns an awaitable of the current data

            accept: Idempotent callable to accept the websocket connection.
        """
        super().__init__('GET', scheme, path, query_string, headers)
        self._accept = accept
        self._receive = receive
        self._send = send
        self._subprotocols = subprotocols

    @property
    def requested_subprotocols(self) -> List[str]:
        return self._subprotocols

    async def receive(self) -> AnyStr:
        await self.accept()
        return await self._receive()

    async def send(self, data: AnyStr) -> None:
        # Must allow for the event loop to act if the user has say
        # setup a tight loop sending data over a websocket (as in the
        # example). So yield via the sleep.
        await asyncio.sleep(0)
        await self.accept()
        await self._send(data)

    async def accept(
            self,
            headers: Optional[Union[dict, CIMultiDict, Headers]] = None,
            subprotocol: Optional[str] = None,
    ) -> None:
        """Manually chose to accept the websocket connection.

        Arguments:
            headers: Additional headers to send with the acceptance
                response.
            subprotocol: The chosen subprotocol, optional.
        """
        if headers is None:
            headers_ = Headers()
        else:
            headers_ = Headers(headers)
        await self._accept(headers_, subprotocol)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.path})"
