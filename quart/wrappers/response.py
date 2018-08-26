from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from hashlib import md5
from inspect import isasyncgen  # type: ignore
from typing import (
    Any, AnyStr, AsyncGenerator, AsyncIterable, Iterable, Optional, Set, Tuple, TYPE_CHECKING,
    Union,
)
from wsgiref.handlers import format_date_time

from ._base import _BaseRequestResponse, JSONMixin
from ..datastructures import (
    CIMultiDict, ContentRange, Headers, HeaderSet, ResponseAccessControl, ResponseCacheControl,
)
from ..utils import create_cookie

if TYPE_CHECKING:
    from .routing import Rule  # noqa


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
    default_mimetype = 'text/html'
    implicit_sequence_conversion = True

    def __init__(
            self,
            response: Union[AnyStr, Iterable],
            status: Optional[int]=None,
            headers: Optional[Union[dict, CIMultiDict, Headers]]=None,
            mimetype: Optional[str]=None,
            content_type: Optional[str]=None,
            *,
            timeout: Optional[int]=None,
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
            timeout: Optional argument to specify timeout when sending
                response data.

        Attributes:
            response: An iterable of the response bytes-data.
            push_promises: A set of paths that should be pushed to the
                client if the protocol is HTTP/2.
        """
        super().__init__(headers)
        self.timeout = timeout

        if status is None:
            status = self.default_status
        try:
            self.status_code = int(status)
        except ValueError as error:
            raise ValueError('Quart  does not support non-integer status values') from error

        if content_type is None:
            if mimetype is None and 'content-type' not in self.headers:
                mimetype = self.default_mimetype
            if mimetype is not None:
                self.mimetype = mimetype

        if content_type is not None:
            self.headers['Content-Type'] = content_type

        self.response: AsyncIterable[bytes]
        if isinstance(response, (str, bytes)):
            self.set_data(response)  # type: ignore
        else:
            self.response = _ensure_aiter(response)  # type: ignore
        self.push_promises: Set[str] = set()

    async def get_data(self, raw: bool=True) -> AnyStr:
        """Return the body data."""
        if not isinstance(self.response, _AsyncList) and self.implicit_sequence_conversion:
            self.response = _AsyncList([data async for data in self.response])  # type: ignore
        result = b'' if raw else ''
        async for data in self.response:  # type: ignore
            if raw:
                result += data  # type: ignore
            else:
                result += data.decode(self.charset)  # type: ignore
        return result  # type: ignore

    def set_data(self, data: AnyStr) -> None:
        """Set the response data.

        This will encode using the :attr:`charset`.
        """
        if isinstance(data, str):
            bytes_data = data.encode(self.charset)
        else:
            bytes_data = data
        self.response = _ensure_aiter([bytes_data])
        if self.automatically_set_content_length:
            self.headers['Content-Length'] = str(len(bytes_data))

    async def freeze(self) -> None:
        """Freeze this object ready for pickling."""
        self.set_data((await self.get_data()))

    def set_cookie(  # type: ignore
            self,
            key: str,
            value: AnyStr='',
            max_age: Optional[Union[int, timedelta]]=None,
            expires: Optional[datetime]=None,
            path: str='/',
            domain: Optional[str]=None,
            secure: bool=False,
            httponly: bool=False,
    ) -> None:
        """Set a cookie in the response headers.

        The arguments are the standard cookie morsels and this is a
        wrapper around the stdlib SimpleCookie code.
        """
        if isinstance(value, bytes):
            value = value.decode()  # type: ignore
        cookie = create_cookie(key, value, max_age, expires, path, domain, secure, httponly)  # type: ignore  # noqa: E501
        self.headers.add('Set-Cookie', cookie.output(header=''))

    def delete_cookie(self, key: str, path: str='/', domain: Optional[str]=None) -> None:
        """Delete a cookie (set to expire immediately)."""
        self.set_cookie(key, expires=datetime.utcnow(), max_age=0, path=path, domain=domain)

    async def add_etag(self, overwrite: bool=False, weak: bool=False) -> None:
        if overwrite or 'etag' not in self.headers:
            self.set_etag(md5((await self.get_data())).hexdigest(), weak)  # type: ignore

    def get_etag(self) -> Tuple[Optional[str], Optional[bool]]:
        etag = self.headers.get('ETag')
        if etag is None:
            return None, None
        else:
            weak = False
            if etag.upper().startswith('W/'):
                etag = etag[2:]
            return etag.strip('"'), weak

    def set_etag(self, etag: str, weak: bool=False) -> None:
        if weak:
            self.headers['ETag'] = f"W/\"{etag}\""
        else:
            self.headers['ETag'] = f"\"{etag}\""

    @property
    def access_control(self) -> ResponseAccessControl:
        def on_update(value: ResponseAccessControl) -> None:
            self.access_control = value

        return ResponseAccessControl.from_headers(
            self.headers.get('Access-Control-Allow-Credentials', ''),
            self.headers.get('Access-Control-Allow-Headers', ''),
            self.headers.get('Access-Control-Allow-Methods', ''),
            self.headers.get('Access-Control-Allow-Origin', ''),
            self.headers.get('Access-Control-Expose-Headers', ''),
            self.headers.get('Access-Control-Max-Age', ''),
            on_update=on_update,
        )

    @access_control.setter
    def access_control(self, value: ResponseAccessControl) -> None:
        max_age = value.max_age
        if max_age is None:
            self.headers.pop('Access-Control-Max-Age', None)
        else:
            self.headers['Access-Control-Max-Age'] = max_age  # type: ignore
        if value.allow_credentials:
            self.headers['Access-Control-Allow-Credentials'] = 'true'
        else:
            self.headers.pop('Access-Control-Allow-Credentials', None)
        self._set_or_pop_header('Access-Control-Allow-Headers', value.allow_headers.to_header())
        self._set_or_pop_header('Access-Control-Allow-Methods', value.allow_methods.to_header())
        self._set_or_pop_header('Access-Control-Allow-Origin', value.allow_origin.to_header())
        self._set_or_pop_header('Access-Control-Expose-Headers', value.expose_headers.to_header())

    @property
    def accept_ranges(self) -> Optional[str]:
        return self.headers.get('Accept-Ranges')

    @accept_ranges.setter
    def accept_ranges(self, value: str) -> None:
        self.headers['Accept-Ranges'] = value

    @property
    def age(self) -> Optional[int]:
        try:
            value = self.headers.get('Age', '')
        except (TypeError, ValueError):
            return None
        return int(value) if value > 0 else None

    @age.setter
    def age(self, value: Union[int, timedelta]) -> None:
        if isinstance(value, timedelta):
            self.headers['Age'] = str(value.total_seconds())
        else:
            self.headers['Age'] = str(value)

    @property
    def allow(self) -> HeaderSet:
        def on_update(header_set: HeaderSet) -> None:
            self.allow = header_set

        return HeaderSet.from_header(self.headers.get('Allow', ''), on_update=on_update)

    @allow.setter
    def allow(self, value: HeaderSet) -> None:
        self._set_or_pop_header('Allow', value.to_header())

    @property
    def cache_control(self) -> ResponseCacheControl:
        def on_update(cache_control: ResponseCacheControl) -> None:
            self.cache_control = cache_control

        return ResponseCacheControl.from_header(self.headers.get('Cache-Control', ''), on_update)  # type: ignore  # noqa: E501

    @cache_control.setter
    def cache_control(self, value: ResponseCacheControl) -> None:
        self._set_or_pop_header('Cache-Control', value.to_header())

    @property
    def content_encoding(self) -> Optional[str]:
        return self.headers.get('Content-Encoding')

    @content_encoding.setter
    def content_encoding(self, value: str) -> None:
        self.headers['Content-Encoding'] = value

    @property
    def content_language(self) -> HeaderSet:
        def on_update(header_set: HeaderSet) -> None:
            self.content_language = header_set

        return HeaderSet.from_header(self.headers.get('Content-Language', ''), on_update=on_update)

    @content_language.setter
    def content_language(self, value: HeaderSet) -> None:
        self._set_or_pop_header('Content-Language', value.to_header())

    @property
    def content_length(self) -> Optional[int]:
        try:
            return int(self.headers.get('Content-Length'))
        except (ValueError, TypeError):
            return None

    @content_length.setter
    def content_length(self, value: int) -> None:
        self.headers['Content-Length'] = str(value)

    @property
    def content_location(self) -> Optional[str]:
        return self.headers.get('Content-Location')

    @content_location.setter
    def content_location(self, value: str) -> None:
        self.headers['Content-Location'] = value

    @property
    def content_md5(self) -> Optional[str]:
        return self.headers.get('Content-MD5')

    @content_md5.setter
    def content_md5(self, value: str) -> None:
        self.headers['Content-MD5'] = value

    @property
    def content_range(self) -> ContentRange:
        def on_update(cache_range: ContentRange) -> None:
            self.content_range = cache_range

        return ContentRange.from_header(self.headers.get('Content-Range', ''), on_update)  # type: ignore  # noqa: E501

    @content_range.setter
    def content_range(self, value: ContentRange) -> None:
        self._set_or_pop_header('Content-Range', value.to_header())

    @property
    def content_type(self) -> Optional[str]:
        return self.headers.get('Content-Type')

    @content_type.setter
    def content_type(self, value: str) -> None:
        self.headers['Content-Type'] = value

    @property
    def date(self) -> Optional[datetime]:
        try:
            return parsedate_to_datetime(self.headers.get('Date', ''))
        except TypeError:  # Not a date format
            return None

    @date.setter
    def date(self, value: datetime) -> None:
        self.headers['Date'] = format_date_time(value.timestamp())

    @property
    def expires(self) -> Optional[datetime]:
        try:
            return parsedate_to_datetime(self.headers.get('Expires', ''))
        except TypeError:  # Not a date format
            return None

    @expires.setter
    def expires(self, value: datetime) -> None:
        self.headers['Expires'] = format_date_time(value.timestamp())

    @property
    def last_modified(self) -> Optional[datetime]:
        try:
            return parsedate_to_datetime(self.headers.get('Last-Modified', ''))
        except TypeError:  # Not a date format
            return None

    @last_modified.setter
    def last_modified(self, value: datetime) -> None:
        self.headers['Last-Modified'] = format_date_time(value.timestamp())

    @property
    def location(self) -> Optional[str]:
        return self.headers.get('Location')

    @location.setter
    def location(self, value: str) -> None:
        self.headers['Location'] = value

    @property
    def referrer(self) -> Optional[str]:
        return self.headers.get('Referer')

    @referrer.setter
    def referrer(self, value: str) -> None:
        self.headers['Referer'] = value

    @property
    def retry_after(self) -> Optional[datetime]:
        value = self.headers.get('Retry-After', '')
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
            self.headers['Retry-After'] = format_date_time(value.timestamp())
        else:
            self.headers['Retry-After'] = str(value)

    @property
    def vary(self) -> HeaderSet:
        def on_update(header_set: HeaderSet) -> None:
            self.vary = header_set

        return HeaderSet.from_header(self.headers.get('Vary', ''), on_update=on_update)

    @vary.setter
    def vary(self, value: HeaderSet) -> None:
        self._set_or_pop_header('Vary', value.to_header())

    async def _load_json_data(self) -> str:
        """Return the data after decoding."""
        return await self.get_data(raw=False)

    def _set_or_pop_header(self, key: str, value: str) -> None:
        if value == '':
            self.headers.pop(key, None)
        else:
            self.headers[key] = value


def _ensure_aiter(
        iter_: Union[AsyncGenerator[bytes, None], Iterable],
) -> AsyncGenerator[bytes, None]:
    if isasyncgen(iter_):
        return iter_  # type: ignore
    else:
        async def aiter() -> AsyncGenerator[bytes, None]:
            for data in iter_:  # type: ignore
                yield data

        return aiter()


class _AsyncList(list):

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.iter_ = iter(self)

    def __aiter__(self) -> '_AsyncList':
        return _AsyncList(self)

    async def __anext__(self) -> Any:
        try:
            return next(self.iter_)
        except StopIteration as error:
            raise StopAsyncIteration() from error
