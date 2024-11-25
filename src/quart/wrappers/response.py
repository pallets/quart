from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from collections.abc import AsyncGenerator
from collections.abc import AsyncIterable
from collections.abc import AsyncIterator
from collections.abc import Iterable
from hashlib import md5
from io import BytesIO
from os import PathLike
from types import TracebackType
from typing import Any
from typing import Literal
from typing import overload
from typing import TYPE_CHECKING

from aiofiles import open as async_open
from aiofiles.base import AiofilesContextManager
from aiofiles.threadpool.binary import AsyncBufferedIOBase
from werkzeug.datastructures import ContentRange
from werkzeug.datastructures import Headers
from werkzeug.exceptions import RequestedRangeNotSatisfiable
from werkzeug.http import parse_etags
from werkzeug.sansio.http import is_resource_modified
from werkzeug.sansio.response import Response as SansIOResponse

from .. import json
from ..globals import current_app
from ..utils import file_path_to_path
from ..utils import run_sync_iterable

if TYPE_CHECKING:
    from .request import Request


class ResponseBody(ABC):
    """Base class wrapper for response body data.

    This ensures that the following is possible (as Quart assumes so
    when returning the body to the ASGI server

        async with wrapper as response:
            async for data in response:
                send(data)

    """

    @abstractmethod
    async def __aenter__(self) -> AsyncIterable:
        pass

    @abstractmethod
    async def __aexit__(
        self, exc_type: type, exc_value: BaseException, tb: TracebackType
    ) -> None:
        pass


def _raise_if_invalid_range(begin: int, end: int, size: int) -> None:
    if begin >= end or abs(begin) > size:
        raise RequestedRangeNotSatisfiable()


class DataBody(ResponseBody):
    def __init__(self, data: bytes) -> None:
        self.data = data
        self.begin = 0
        self.end = len(self.data)

    async def __aenter__(self) -> DataBody:
        return self

    async def __aexit__(
        self, exc_type: type, exc_value: BaseException, tb: TracebackType
    ) -> None:
        pass

    def __aiter__(self) -> AsyncIterator[bytes]:
        return _DataBodyGen(self)

    async def make_conditional(self, begin: int, end: int | None) -> int:
        self.begin = begin
        self.end = len(self.data) if end is None else end
        self.end = min(len(self.data), self.end)
        _raise_if_invalid_range(self.begin, self.end, len(self.data))
        return len(self.data)


class _DataBodyGen(AsyncIterator[bytes]):
    def __init__(self, data_body: DataBody):
        self._data_body = data_body
        self._iterated = False

    async def __anext__(self) -> bytes:
        if self._iterated:
            raise StopAsyncIteration

        self._iterated = True
        return self._data_body.data[self._data_body.begin : self._data_body.end]


class IterableBody(ResponseBody):
    def __init__(self, iterable: AsyncIterable[Any] | Iterable[Any]) -> None:
        self.iter: AsyncIterator[Any]
        if isinstance(iterable, Iterable):
            self.iter = run_sync_iterable(iter(iterable))
        else:
            self.iter = iterable.__aiter__()  # Can't use aiter() until 3.10

    async def __aenter__(self) -> IterableBody:
        return self

    async def __aexit__(
        self, exc_type: type, exc_value: BaseException, tb: TracebackType
    ) -> None:
        if hasattr(self.iter, "aclose"):
            await self.iter.aclose()

    def __aiter__(self) -> AsyncIterator[Any]:
        return self.iter


class FileBody(ResponseBody):
    """Provides an async file accessor with range setting.

    The :attr:`Response.response` attribute must be async-iterable and
    yield bytes, which this wrapper does for a file. In addition it
    allows a range to be set on the file, thereby supporting
    conditional requests.

    Attributes:
        buffer_size: Size in bytes to load per iteration.
    """

    buffer_size = 8192

    def __init__(
        self, file_path: str | PathLike, *, buffer_size: int | None = None
    ) -> None:
        self.file_path = file_path_to_path(file_path)
        self.size = self.file_path.stat().st_size
        self.begin = 0
        self.end = self.size
        if buffer_size is not None:
            self.buffer_size = buffer_size
        self.file: AsyncBufferedIOBase | None = None
        self.file_manager: AiofilesContextManager = None

    async def __aenter__(self) -> FileBody:
        self.file_manager = async_open(self.file_path, mode="rb")
        self.file = await self.file_manager.__aenter__()
        await self.file.seek(self.begin)
        return self

    async def __aexit__(
        self, exc_type: type, exc_value: BaseException, tb: TracebackType
    ) -> None:
        await self.file_manager.__aexit__(exc_type, exc_value, tb)

    def __aiter__(self) -> FileBody:
        return self

    async def __anext__(self) -> bytes:
        current = await self.file.tell()
        if current >= self.end:
            raise StopAsyncIteration()
        read_size = min(self.buffer_size, self.end - current)
        chunk = await self.file.read(read_size)

        if chunk:
            return chunk
        else:
            raise StopAsyncIteration()

    async def make_conditional(self, begin: int, end: int | None) -> int:
        self.begin = begin
        self.end = self.size if end is None else end
        self.end = min(self.size, self.end)
        _raise_if_invalid_range(self.begin, self.end, self.size)
        return self.size


class IOBody(ResponseBody):
    """Provides an async file accessor with range setting.

    The :attr:`Response.response` attribute must be async-iterable and
    yield bytes, which this wrapper does for a file. In addition it
    allows a range to be set on the file, thereby supporting
    conditional requests.

    Attributes:
        buffer_size: Size in bytes to load per iteration.
    """

    buffer_size = 8192

    def __init__(self, io_stream: BytesIO, *, buffer_size: int | None = None) -> None:
        self.io_stream = io_stream
        self.size = io_stream.getbuffer().nbytes
        self.begin = 0
        self.end = self.size
        if buffer_size is not None:
            self.buffer_size = buffer_size

    async def __aenter__(self) -> IOBody:
        self.io_stream.seek(self.begin)
        return self

    async def __aexit__(
        self, exc_type: type, exc_value: BaseException, tb: TracebackType
    ) -> None:
        return None

    def __aiter__(self) -> IOBody:
        return self

    async def __anext__(self) -> bytes:
        current = self.io_stream.tell()
        if current >= self.end:
            raise StopAsyncIteration()
        read_size = min(self.buffer_size, self.end - current)
        chunk = self.io_stream.read(read_size)

        if chunk:
            return chunk
        else:
            raise StopAsyncIteration()

    async def make_conditional(self, begin: int, end: int | None) -> int:
        self.begin = begin
        self.end = self.size if end is None else end
        self.end = min(self.size, self.end)
        _raise_if_invalid_range(self.begin, self.end, self.size)
        return self.size


class Response(SansIOResponse):
    """This class represents a response.

    It can be subclassed and the subclassed used in preference by
    replacing the :attr:`~quart.Quart.response_class` with your
    subclass.

    Attributes:
        automatically_set_content_length: If False the content length
            header must be provided.
        default_status: The status code to use if not provided.
        default_mimetype: The mimetype to use if not provided.
        implicit_sequence_conversion: Implicitly convert the response
            to a iterable in the get_data method, to allow multiple
            iterations.
    """

    automatically_set_content_length = True
    default_mimetype = "text/html"
    data_body_class = DataBody
    file_body_class = FileBody
    implicit_sequence_conversion = True
    io_body_class = IOBody
    iterable_body_class = IterableBody
    json_module = json

    def __init__(
        self,
        response: ResponseBody | str | bytes | Iterable | AsyncIterable | None = None,
        status: int | None = None,
        headers: dict | Headers | None = None,
        mimetype: str | None = None,
        content_type: str | None = None,
    ) -> None:
        """Create a response object.

        The response itself can be a chunk of data or a
        iterable/generator of data chunks.

        The Content-Type can either be specified as a mimetype or
        content_type header or omitted to use the
        :attr:`default_mimetype`.

        Arguments:
            response: The response data or iterable over the data.
            status: Status code of the response.
            headers: Headers to attach to the response.
            mimetype: Mimetype of the response.
            content_type: Content-Type header value.

        Attributes:
            response: An iterable of the response bytes-data.
        """
        super().__init__(status, headers, mimetype, content_type)
        self.timeout: Any = Ellipsis

        self.response: ResponseBody
        if response is None:
            self.response = self.iterable_body_class([])
        elif isinstance(response, ResponseBody):
            self.response = response
        elif isinstance(response, (str, bytes)):
            self.set_data(response)
        else:
            self.response = self.iterable_body_class(response)

    @property
    def max_cookie_size(self) -> int:  # type: ignore
        if current_app:
            return current_app.config["MAX_COOKIE_SIZE"]

        return super().max_cookie_size

    @overload
    async def get_data(self, as_text: Literal[True]) -> str: ...

    @overload
    async def get_data(self, as_text: Literal[False]) -> bytes: ...

    @overload
    async def get_data(self, as_text: bool = True) -> str | bytes: ...

    async def get_data(self, as_text: bool = False) -> str | bytes:
        """Return the body data."""
        if self.implicit_sequence_conversion:
            await self.make_sequence()
        result = "" if as_text else b""
        async with self.response as body:
            async for data in body:
                if as_text:
                    result += data.decode()
                else:
                    result += data
        return result

    def set_data(self, data: str | bytes) -> None:
        """Set the response data.

        This will encode using the :attr:`charset`.
        """
        if isinstance(data, str):
            bytes_data = data.encode()
        else:
            bytes_data = data
        self.response = self.data_body_class(bytes_data)
        if self.automatically_set_content_length:
            self.content_length = len(bytes_data)

    @property
    async def data(self) -> bytes:
        return await self.get_data(as_text=False)

    @data.setter
    def data(self, value: bytes) -> None:
        self.set_data(value)

    @property
    async def json(self) -> Any:
        return await self.get_json()

    async def get_json(self, force: bool = False, silent: bool = False) -> Any:
        """Parses the body data as JSON and returns it.

        Arguments:
            force: Force JSON parsing even if the mimetype is not JSON.
            silent: Do not trigger error handling if parsing fails, without
                this the :meth:`on_json_loading_failed` will be called on
                error.
        """
        if not (force or self.is_json):
            return None

        data = await self.get_data(as_text=True)
        try:
            return self.json_module.loads(data)
        except ValueError:
            if silent:
                raise
            return None

    def _is_range_request_processable(self, request: Request) -> bool:
        return (
            "If-Range" not in request.headers
            or not is_resource_modified(
                http_range=request.headers.get("Range"),
                http_if_range=request.headers.get("If-Range"),
                http_if_modified_since=request.headers.get("If-Modified-Since"),
                http_if_none_match=request.headers.get("If-None-Match"),
                http_if_match=request.headers.get("If-Match"),
                etag=self.headers.get("etag"),
                data=None,
                last_modified=self.headers.get("last-modified"),
                ignore_if_range=False,
            )
        ) and "Range" in request.headers

    async def _process_range_request(
        self,
        request: Request,
        complete_length: int | None = None,
        accept_ranges: str | None = None,
    ) -> bool:
        if (
            accept_ranges is None
            or complete_length is None
            or complete_length == 0
            or not self._is_range_request_processable(request)
        ):
            return False

        request_range = request.range

        if request_range is None:
            raise RequestedRangeNotSatisfiable(complete_length)

        if request_range.units != "bytes" or len(request_range.ranges) > 1:
            raise RequestedRangeNotSatisfiable()

        begin, end = request_range.ranges[0]
        try:
            complete_length = await self.response.make_conditional(begin, end)  # type: ignore
        except AttributeError:
            await self.make_sequence()
            complete_length = await self.response.make_conditional(begin, end)  # type: ignore

        self.content_length = self.response.end - self.response.begin  # type: ignore
        self.headers["Accept-Ranges"] = accept_ranges
        self.content_range = ContentRange(
            request_range.units,
            self.response.begin,  # type: ignore
            self.response.end,  # type: ignore
            complete_length,
        )
        self.status_code = 206

        return True

    async def make_conditional(
        self,
        request: Request,
        accept_ranges: bool | str = False,
        complete_length: int | None = None,
    ) -> Response:
        if request.method in {"GET", "HEAD"}:
            accept_ranges = _clean_accept_ranges(accept_ranges)
            is206 = await self._process_range_request(
                request, complete_length, accept_ranges
            )
            if not is206 and not is_resource_modified(
                http_range=request.headers.get("Range"),
                http_if_range=request.headers.get("If-Range"),
                http_if_modified_since=request.headers.get("If-Modified-Since"),
                http_if_none_match=request.headers.get("If-None-Match"),
                http_if_match=request.headers.get("If-Match"),
                etag=self.headers.get("etag"),
                data=None,
                last_modified=self.headers.get("last-modified"),
                ignore_if_range=True,
            ):
                if parse_etags(request.headers.get("If-Match")):
                    self.status_code = 412
                else:
                    self.status_code = 304
                    self.set_data(b"")
                    del self.content_length

        return self

    async def make_sequence(self) -> None:
        data = b"".join([value async for value in self.iter_encode()])
        self.response = self.data_body_class(data)

    async def iter_encode(self) -> AsyncGenerator[bytes, None]:
        async with self.response as response_body:
            async for item in response_body:
                if isinstance(item, str):
                    yield item.encode()
                else:
                    yield item

    async def freeze(self) -> None:
        """Freeze this object ready for pickling."""
        self.set_data(await self.get_data())

    async def add_etag(self, overwrite: bool = False, weak: bool = False) -> None:
        if overwrite or "etag" not in self.headers:
            self.set_etag(md5(await self.get_data(as_text=False)).hexdigest(), weak)

    def _set_or_pop_header(self, key: str, value: str) -> None:
        if value == "":
            self.headers.pop(key, None)
        else:
            self.headers[key] = value


def _clean_accept_ranges(accept_ranges: bool | str) -> str:
    if accept_ranges is True:
        return "bytes"
    elif accept_ranges is False:
        return "none"
    elif isinstance(accept_ranges, str):
        return accept_ranges
    raise ValueError("Invalid accept_ranges value")
