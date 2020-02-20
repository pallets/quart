from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from hashlib import md5
from inspect import isasyncgen, isgenerator
from io import BytesIO
from os import PathLike
from types import TracebackType
from typing import (
    AnyStr,
    AsyncGenerator,
    AsyncIterable,
    AsyncIterator,
    Iterable,
    Optional,
    Tuple,
    Union,
)
from wsgiref.handlers import format_date_time

from aiofiles import open as async_open
from aiofiles.base import AiofilesContextManager
from aiofiles.threadpool import AsyncFileIO
from werkzeug.datastructures import (  # type: ignore
    ContentRange,
    ContentSecurityPolicy,
    Headers,
    HeaderSet,
    Range,
    ResponseCacheControl,
)
from werkzeug.http import (  # type: ignore
    dump_cookie,
    dump_csp_header,
    dump_header,
    parse_cache_control_header,
    parse_content_range_header,
    parse_csp_header,
    parse_set_header,
)

from .base import _BaseRequestResponse, JSONMixin
from ..utils import file_path_to_path, run_sync_iterable

sentinel = object()


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
    async def __aexit__(self, exc_type: type, exc_value: BaseException, tb: TracebackType) -> None:
        pass

    @abstractmethod
    async def convert_to_sequence(self) -> bytes:
        pass


def _raise_if_invalid_range(begin: int, end: int, size: int) -> None:
    if begin >= end or abs(begin) > size or end > size:
        from ..exceptions import RequestRangeNotSatisfiable

        raise RequestRangeNotSatisfiable()


class DataBody(ResponseBody):
    def __init__(self, data: bytes) -> None:
        self.data = data
        self.begin = 0
        self.end = len(self.data)

    async def __aenter__(self) -> "DataBody":
        return self

    async def __aexit__(self, exc_type: type, exc_value: BaseException, tb: TracebackType) -> None:
        pass

    def __aiter__(self) -> AsyncIterator:
        async def _aiter() -> AsyncGenerator[bytes, None]:
            yield self.data[self.begin : self.end]

        return _aiter()

    async def convert_to_sequence(self) -> bytes:
        return self.data[self.begin : self.end]

    async def make_conditional(
        self, begin: int, end: Optional[int], max_partial_size: Optional[int] = None
    ) -> int:
        self.begin = begin
        self.end = len(self.data) if end is None else end
        if max_partial_size is not None:
            self.end = min(self.begin + max_partial_size, self.end)
        _raise_if_invalid_range(self.begin, self.end, len(self.data))
        return len(self.data)


class IterableBody(ResponseBody):
    def __init__(self, iterable: Union[AsyncGenerator[bytes, None], Iterable]) -> None:
        self.iter: AsyncGenerator[bytes, None]
        if isasyncgen(iterable):
            self.iter = iterable  # type: ignore
        elif isgenerator(iterable):
            self.iter = run_sync_iterable(iterable)  # type: ignore
        else:

            async def _aiter() -> AsyncGenerator[bytes, None]:
                for data in iterable:  # type: ignore
                    yield data

            self.iter = _aiter()

    async def __aenter__(self) -> "IterableBody":
        return self

    async def __aexit__(self, exc_type: type, exc_value: BaseException, tb: TracebackType) -> None:
        pass

    def __aiter__(self) -> AsyncIterator:
        return self.iter

    async def convert_to_sequence(self) -> bytes:
        result = bytearray()
        async for data in self.iter:
            result.extend(data)
        return bytes(result)


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
        self, file_path: Union[str, PathLike], *, buffer_size: Optional[int] = None
    ) -> None:
        self.file_path = file_path_to_path(file_path)
        self.size = self.file_path.stat().st_size
        self.begin = 0
        self.end = self.size
        if buffer_size is not None:
            self.buffer_size = buffer_size
        self.file: Optional[AsyncFileIO] = None
        self.file_manager: Optional[AiofilesContextManager] = None

    async def __aenter__(self) -> "FileBody":
        self.file_manager = async_open(self.file_path, mode="rb")
        self.file = await self.file_manager.__aenter__()
        await self.file.seek(self.begin)
        return self

    async def __aexit__(self, exc_type: type, exc_value: BaseException, tb: TracebackType) -> None:
        await self.file_manager.__aexit__(exc_type, exc_value, tb)

    def __aiter__(self) -> "FileBody":
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

    async def convert_to_sequence(self) -> bytes:
        result = bytearray()
        async with self as response:
            async for data in response:
                result.extend(data)
        return bytes(result)

    async def make_conditional(
        self, begin: int, end: Optional[int], max_partial_size: Optional[int] = None
    ) -> int:
        self.begin = begin
        self.end = self.size if end is None else end
        if max_partial_size is not None:
            self.end = min(self.begin + max_partial_size, self.end)
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

    def __init__(self, io_stream: BytesIO, *, buffer_size: Optional[int] = None) -> None:
        self.io_stream = io_stream
        self.size = io_stream.getbuffer().nbytes
        self.begin = 0
        self.end = self.size
        if buffer_size is not None:
            self.buffer_size = buffer_size

    async def __aenter__(self) -> "IOBody":
        self.io_stream.seek(self.begin)
        return self

    async def __aexit__(self, exc_type: type, exc_value: BaseException, tb: TracebackType) -> None:
        return None

    def __aiter__(self) -> "IOBody":
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

    async def convert_to_sequence(self) -> bytes:
        result = bytearray()
        async with self as response:
            async for data in response:
                result.extend(data)
        return bytes(result)

    async def make_conditional(
        self, begin: int, end: Optional[int], max_partial_size: Optional[int] = None
    ) -> int:
        self.begin = begin
        self.end = self.size if end is None else end
        if max_partial_size is not None:
            self.end = min(self.begin + max_partial_size, self.end)
        _raise_if_invalid_range(self.begin, self.end, self.size)
        return self.size


class Response(_BaseRequestResponse, JSONMixin):
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
    default_status = 200
    default_mimetype = "text/html"
    data_body_class = DataBody
    file_body_class = FileBody
    implicit_sequence_conversion = True
    io_body_class = IOBody
    iterable_body_class = IterableBody
    max_cookie_size = 4093

    def __init__(
        self,
        response: Union[ResponseBody, AnyStr, Iterable],
        status: Optional[int] = None,
        headers: Optional[Union[dict, Headers]] = None,
        mimetype: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> None:
        """Create a response object.

        The response itself can be a chunk of data or a
        iterable/generator of data chunks.

        The Content-Type can either be specified as a mimetype or
        content_type header or omitted to use the
        :attr:`default_mimetype`.

        Arguments:
            response: The response data or iterable over the data.
            status_code: Status code of the response.
            headers: Headers to attach to the response.
            mimetype: Mimetype of the response.
            content_type: Content-Type header value.

        Attributes:
            response: An iterable of the response bytes-data.
        """
        super().__init__(headers)
        self.timeout: Union[int, None, object] = sentinel

        if status is None:
            status = self.default_status
        try:
            self.status_code = int(status)
        except ValueError as error:
            raise ValueError("Quart  does not support non-integer status values") from error

        if content_type is None:
            if mimetype is None and "content-type" not in self.headers:
                mimetype = self.default_mimetype
            if mimetype is not None:
                self.mimetype = mimetype

        if content_type is not None:
            self.headers["Content-Type"] = content_type

        self.response: ResponseBody
        if isinstance(response, ResponseBody):
            self.response = response
        elif isinstance(response, (str, bytes)):
            self.set_data(response)  # type: ignore
        else:
            self.response = self.iterable_body_class(response)

    async def get_data(self, raw: bool = True) -> AnyStr:
        """Return the body data."""
        if self.implicit_sequence_conversion:
            self.response = self.data_body_class(await self.response.convert_to_sequence())
        result = b"" if raw else ""
        async with self.response as body:  # type: ignore
            async for data in body:
                if raw:
                    result += data
                else:
                    result += data.decode(self.charset)
        return result  # type: ignore

    def set_data(self, data: AnyStr) -> None:
        """Set the response data.

        This will encode using the :attr:`charset`.
        """
        if isinstance(data, str):
            bytes_data = data.encode(self.charset)
        else:
            bytes_data = data
        self.response = self.data_body_class(bytes_data)
        if self.automatically_set_content_length:
            self.content_length = len(bytes_data)

    async def make_conditional(
        self, request_range: Optional[Range], max_partial_size: Optional[int] = None
    ) -> None:
        """Make the response conditional to the

        Arguments:
            request_range: The range as requested by the request.
            max_partial_size: The maximum length the server is willing
                to serve in a single response. Defaults to unlimited.

        """
        self.accept_ranges = "bytes"  # Advertise this ability
        if request_range is None or len(request_range.ranges) == 0:  # Not a conditional request
            return

        if request_range.units != "bytes" or len(request_range.ranges) > 1:
            from ..exceptions import RequestRangeNotSatisfiable

            raise RequestRangeNotSatisfiable()

        begin, end = request_range.ranges[0]
        try:
            complete_length = await self.response.make_conditional(  # type: ignore
                begin, end, max_partial_size
            )
        except AttributeError:
            self.response = self.data_body_class(await self.response.convert_to_sequence())
            return await self.make_conditional(request_range, max_partial_size)
        else:
            self.content_length = self.response.end - self.response.begin  # type: ignore
            if self.content_length != complete_length:
                self.content_range = ContentRange(
                    request_range.units,
                    self.response.begin,  # type: ignore
                    self.response.end - 1,  # type: ignore
                    complete_length,
                )
                self.status_code = 206

    async def freeze(self) -> None:
        """Freeze this object ready for pickling."""
        self.set_data((await self.get_data()))

    def set_cookie(
        self,
        key: str,
        value: AnyStr = "",  # type: ignore
        max_age: Optional[Union[int, timedelta]] = None,
        expires: Optional[Union[int, float, datetime]] = None,
        path: str = "/",
        domain: Optional[str] = None,
        secure: bool = False,
        httponly: bool = False,
        samesite: str = None,
    ) -> None:
        """Set a cookie in the response headers.

        The arguments are the standard cookie morsels and this is a
        wrapper around the stdlib SimpleCookie code.
        """
        if isinstance(value, bytes):
            value = value.decode()  # type: ignore
        self.headers.add(
            "Set-Cookie",
            dump_cookie(  # type: ignore
                key,
                value=value,
                max_age=max_age,
                expires=expires,
                path=path,
                domain=domain,
                secure=secure,
                httponly=httponly,
                charset=self.charset,
                max_size=self.max_cookie_size,
                samesite=samesite,
            ),
        )

    def delete_cookie(self, key: str, path: str = "/", domain: Optional[str] = None) -> None:
        """Delete a cookie (set to expire immediately)."""
        self.set_cookie(key, expires=0, max_age=0, path=path, domain=domain)

    async def add_etag(self, overwrite: bool = False, weak: bool = False) -> None:
        if overwrite or "etag" not in self.headers:
            self.set_etag(md5((await self.get_data())).hexdigest(), weak)

    def get_etag(self) -> Tuple[Optional[str], Optional[bool]]:
        etag = self.headers.get("ETag")
        if etag is None:
            return None, None
        else:
            weak = False
            if etag.upper().startswith("W/"):
                etag = etag[2:]
            return etag.strip('"'), weak

    def set_etag(self, etag: str, weak: bool = False) -> None:
        if weak:
            self.headers["ETag"] = f'W/"{etag}"'
        else:
            self.headers["ETag"] = f'"{etag}"'

    @property
    def access_control_allow_credentials(self) -> bool:
        """Whether credentials can be shared by the browser to
        JavaScript code. As part of the preflight request it indicates
        whether credentials can be used on the cross origin request.
        """
        return "Access-Control-Allow-Credentials" in self.headers

    @access_control_allow_credentials.setter
    def access_control_allow_credentials(self, value: bool) -> None:
        if value is True:
            self.headers["Access-Control-Allow-Credentials"] = "true"
        else:
            self.headers.pop("Access-Control-Allow-Credentials", None)  # type: ignore

    @property
    def access_control_allow_headers(self) -> Optional[HeaderSet]:
        if "Access-Control-Allow-Headers" in self.headers:
            return parse_set_header(self.headers["Access-Control-Allow-Headers"])
        return None

    @access_control_allow_headers.setter
    def access_control_allow_headers(self, value: HeaderSet) -> None:
        self.headers["Access-Control-Allow-Headers"] = dump_header(value)

    @property
    def access_control_allow_methods(self) -> Optional[HeaderSet]:
        if "Access-Control-Allow-Methods" in self.headers:
            return parse_set_header(self.headers["Access-Control-Allow-Methods"])
        return None

    @access_control_allow_methods.setter
    def access_control_allow_methods(self, value: HeaderSet) -> None:
        self.headers["Access-Control-Allow-Methods"] = dump_header(value)

    @property
    def access_control_allow_origin(self) -> Optional[str]:
        return self.headers.get("Access-Control-Allow-Origin")

    @access_control_allow_origin.setter
    def access_control_allow_origin(self, value: str) -> None:
        self.headers["Access-Control-Allow-Origin"] = value

    @property
    def access_control_expose_headers(self) -> Optional[HeaderSet]:
        if "Access-Control-Expose-Headers" in self.headers:
            return parse_set_header(self.headers["Access-Control-Expose-Headers"])
        return None

    @access_control_expose_headers.setter
    def access_control_expose_headers(self, value: HeaderSet) -> None:
        self.headers["Access-Control-Expose-Headers"] = dump_header(value)

    @property
    def access_control_max_age(self) -> Optional[int]:
        if "Access-Control-Max-Age" in self.headers:
            return int(self.headers["Access-Control-Max-Age"])
        return None

    @access_control_max_age.setter
    def access_control_max_age(self, value: int) -> None:
        self.headers["Access-Control-Max-Age"] = str(value)

    @property
    def accept_ranges(self) -> Optional[str]:
        return self.headers.get("Accept-Ranges")

    @accept_ranges.setter
    def accept_ranges(self, value: str) -> None:
        self.headers["Accept-Ranges"] = value

    @property
    def age(self) -> Optional[int]:
        try:
            value = int(self.headers.get("Age", ""))
        except (TypeError, ValueError):
            return None
        return value if value > 0 else None

    @age.setter
    def age(self, value: Union[int, timedelta]) -> None:
        if isinstance(value, timedelta):
            self.headers["Age"] = str(value.total_seconds())
        else:
            self.headers["Age"] = str(value)

    @property
    def allow(self) -> HeaderSet:
        def on_update(header_set: HeaderSet) -> None:
            self.allow = header_set

        return parse_set_header(self.headers.get("Allow"), on_update=on_update)

    @allow.setter
    def allow(self, value: HeaderSet) -> None:
        self._set_or_pop_header("Allow", value.to_header())

    @property
    def cache_control(self) -> ResponseCacheControl:
        def on_update(cache_control: ResponseCacheControl) -> None:
            self.cache_control = cache_control

        return parse_cache_control_header(
            self.headers.get("Cache-Control"), on_update, ResponseCacheControl
        )

    @cache_control.setter
    def cache_control(self, value: ResponseCacheControl) -> None:
        self._set_or_pop_header("Cache-Control", value.to_header())

    @property
    def content_encoding(self) -> Optional[str]:
        return self.headers.get("Content-Encoding")

    @content_encoding.setter
    def content_encoding(self, value: str) -> None:
        self.headers["Content-Encoding"] = value

    @property
    def content_language(self) -> HeaderSet:
        def on_update(header_set: HeaderSet) -> None:
            self.content_language = header_set

        return parse_set_header(self.headers.get("Content-Language"), on_update=on_update)

    @content_language.setter
    def content_language(self, value: HeaderSet) -> None:
        self._set_or_pop_header("Content-Language", value.to_header())

    @property
    def content_length(self) -> Optional[int]:
        try:
            return int(self.headers.get("Content-Length"))
        except (ValueError, TypeError):
            return None

    @content_length.setter
    def content_length(self, value: int) -> None:
        self.headers["Content-Length"] = str(value)

    @property
    def content_location(self) -> Optional[str]:
        return self.headers.get("Content-Location")

    @content_location.setter
    def content_location(self, value: str) -> None:
        self.headers["Content-Location"] = value

    @property
    def content_md5(self) -> Optional[str]:
        return self.headers.get("Content-MD5")

    @content_md5.setter
    def content_md5(self, value: str) -> None:
        self.headers["Content-MD5"] = value

    @property
    def content_range(self) -> ContentRange:
        def on_update(cache_range: ContentRange) -> None:
            self.content_range = cache_range

        return parse_content_range_header(self.headers.get("Content-Range"), on_update)

    @content_range.setter
    def content_range(self, value: ContentRange) -> None:
        self._set_or_pop_header("Content-Range", value.to_header())

    @property
    def content_security_policy(self) -> ContentSecurityPolicy:
        def on_update(content_security_policy: ContentSecurityPolicy) -> None:
            self.content_security_policy = content_security_policy

        return parse_csp_header(self.headers.get("Content-Security-Policy"), on_update)

    @content_security_policy.setter
    def content_security_policy(self, value: ContentSecurityPolicy) -> None:
        self._set_or_pop_header("Content-Security-Policy", dump_csp_header(value))

    @property
    def content_security_policy_report_only(self) -> ContentSecurityPolicy:
        def on_update(content_security_policy: ContentSecurityPolicy) -> None:
            self.content_security_policy_report_only = content_security_policy

        return ContentSecurityPolicy.from_header(
            self.headers.get("Content-Security-Policy-Report-Only", ""), on_update
        )

    @content_security_policy_report_only.setter
    def content_security_policy_report_only(self, value: ContentSecurityPolicy) -> None:
        self._set_or_pop_header("Content-Security-Policy-Report-Only", value.to_header())

    @property
    def content_type(self) -> Optional[str]:
        return self.headers.get("Content-Type")

    @content_type.setter
    def content_type(self, value: str) -> None:
        self.headers["Content-Type"] = value

    @property
    def date(self) -> Optional[datetime]:
        try:
            return parsedate_to_datetime(self.headers.get("Date", ""))
        except TypeError:  # Not a date format
            return None

    @date.setter
    def date(self, value: datetime) -> None:
        self.headers["Date"] = format_date_time(value.timestamp())

    @property
    def expires(self) -> Optional[datetime]:
        try:
            return parsedate_to_datetime(self.headers.get("Expires", ""))
        except TypeError:  # Not a date format
            return None

    @expires.setter
    def expires(self, value: datetime) -> None:
        self.headers["Expires"] = format_date_time(value.timestamp())

    @property
    def last_modified(self) -> Optional[datetime]:
        try:
            return parsedate_to_datetime(self.headers.get("Last-Modified", ""))
        except TypeError:  # Not a date format
            return None

    @last_modified.setter
    def last_modified(self, value: datetime) -> None:
        self.headers["Last-Modified"] = format_date_time(value.timestamp())

    @property
    def location(self) -> Optional[str]:
        return self.headers.get("Location")

    @location.setter
    def location(self, value: str) -> None:
        self.headers["Location"] = value

    @property
    def referrer(self) -> Optional[str]:
        return self.headers.get("Referer")

    @referrer.setter
    def referrer(self, value: str) -> None:
        self.headers["Referer"] = value

    @property
    def retry_after(self) -> Optional[datetime]:
        value = self.headers.get("Retry-After", "")
        if value.isdigit():
            return datetime.utcnow() + timedelta(seconds=int(value))
        else:
            try:
                return parsedate_to_datetime(value)
            except TypeError:
                return None

    @retry_after.setter
    def retry_after(self, value: Union[datetime, int]) -> None:
        if isinstance(value, datetime):
            self.headers["Retry-After"] = format_date_time(value.timestamp())
        else:
            self.headers["Retry-After"] = str(value)

    @property
    def vary(self) -> HeaderSet:
        def on_update(header_set: HeaderSet) -> None:
            self.vary = header_set

        return parse_set_header(self.headers.get("Vary"), on_update=on_update)

    @vary.setter
    def vary(self, value: HeaderSet) -> None:
        self._set_or_pop_header("Vary", value.to_header())

    async def _load_json_data(self) -> str:
        """Return the data after decoding."""
        return await self.get_data(raw=False)

    def _set_or_pop_header(self, key: str, value: str) -> None:
        if value == "":
            self.headers.pop(key, None)  # type: ignore
        else:
            self.headers[key] = value

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.status_code})"
