import asyncio
import io
from cgi import FieldStorage, parse_header
from typing import Any, AnyStr, Callable, Generator, Optional, TYPE_CHECKING
from urllib.parse import parse_qs

from ._base import BaseRequestWebsocket, JSONMixin
from ..datastructures import CIMultiDict, FileStorage, MultiDict

if TYPE_CHECKING:
    from .routing import Rule  # noqa


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

    def __init__(self, max_content_length: Optional[int]) -> None:
        self._data = bytearray()
        self._complete: asyncio.Event = asyncio.Event()
        self._has_data: asyncio.Event = asyncio.Event()
        self._max_content_length = max_content_length

    def __aiter__(self) -> 'Body':
        return self

    async def __anext__(self) -> bytes:
        await self._has_data.wait()
        if self._complete.is_set() and len(self._data) == 0:
            raise StopAsyncIteration()

        data = bytes(self._data)
        self._data.clear()
        self._has_data.clear()
        return data

    def __await__(self) -> Generator[Any, None, Any]:
        try:
            yield from self._complete.wait().__await__()
        except AttributeError:  # Python 3.7 moved to async/await throughout, 3.6 breaks here
            yield from self._complete.wait()
        return bytes(self._data)

    def append(self, data: bytes) -> None:
        if data == b'':
            return
        self._data.extend(data)
        self._has_data.set()
        if self._max_content_length is not None and len(self._data) > self._max_content_length:
            from ..exceptions import RequestEntityTooLarge  # noqa Avoiding circular import
            raise RequestEntityTooLarge()

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
    """

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
        """
        super().__init__(method, scheme, path, query_string, headers)
        self.max_content_length = max_content_length
        self.body_timeout = body_timeout
        if (
                self.content_length is not None and self.max_content_length is not None and
                self.content_length > self.max_content_length
        ):
            from ..exceptions import RequestEntityTooLarge  # noqa Avoiding circular import
            raise RequestEntityTooLarge()
        self.body = Body(self.max_content_length)
        self._form: Optional[MultiDict] = None
        self._files: Optional[MultiDict] = None

    async def get_data(self, raw: bool=True) -> AnyStr:
        """The request body data."""
        try:
            body_future = asyncio.ensure_future(self.body)
            raw_data = await asyncio.wait_for(body_future, timeout=self.body_timeout)
        except asyncio.TimeoutError:
            body_future.cancel()
            from ..exceptions import RequestTimeout
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
        data = await self.body  # type: ignore
        self._form = MultiDict()
        self._files = MultiDict()
        content_header = self.content_type
        if content_header is None:
            return
        content_type, parameters = parse_header(content_header)
        if content_type == 'application/x-www-form-urlencoded':
            for key, values in parse_qs(data.decode(), keep_blank_values=True).items():
                for value in values:
                    self._form.add(key, value)
        elif content_type == 'multipart/form-data':
            field_storage = FieldStorage(
                io.BytesIO(data), headers=self.headers, environ={'REQUEST_METHOD': 'POST'},
            )
            for key in field_storage:  # type: ignore
                field_storage_key = field_storage[key]
                if isinstance(field_storage_key, list):
                    for item in field_storage_key:
                        self._form.add(key, item.value)
                elif (
                        isinstance(field_storage_key, FieldStorage) and
                        field_storage_key.filename is not None
                ):
                    self._files[key] = FileStorage(  # type: ignore
                        io.BytesIO(field_storage_key.file.read()), field_storage_key.filename,
                        field_storage_key.name, field_storage_key.type, field_storage_key.headers,  # type: ignore # noqa: E501
                    )
                else:
                    self._form.add(key, field_storage_key.value)

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


class Websocket(BaseRequestWebsocket):

    def __init__(
            self,
            path: str,
            query_string: bytes,
            scheme: str,
            headers: CIMultiDict,
            queue: asyncio.Queue,
            send: Callable,
            accept: Callable,
    ) -> None:
        """Create a request object.

        Arguments:
            path: The full unquoted path of the request.
            query_string: The raw bytes for the query string part.
            scheme: The scheme used for the request.
            headers: The request headers.
            websocket: The actual websocket with the data.
            accept: Idempotent callable to accept the websocket connection.
        """
        super().__init__('GET', scheme, path, query_string, headers)
        self._queue = queue
        self._send = send
        self._accept = accept

    async def receive(self) -> AnyStr:
        await self.accept()
        return await self._queue.get()

    async def send(self, data: AnyStr) -> None:
        # Must allow for the event loop to act if the user has say
        # setup a tight loop sending data over a websocket (as in the
        # example). So yield via the sleep.
        await asyncio.sleep(0)
        await self.accept()
        await self._send(data)

    async def accept(self) -> None:
        """Manually chose to accept the websocket connection."""
        await self._accept()
