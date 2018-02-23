from datetime import datetime, timedelta
from inspect import isasyncgen  # type: ignore
from typing import (
    Any, AnyStr, AsyncGenerator, AsyncIterable, Iterable, Optional, Set, TYPE_CHECKING, Union,
)

from ._base import _BaseRequestResponse, JSONMixin
from ..datastructures import CIMultiDict, ResponseCacheControl
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
            headers: Optional[Union[dict, CIMultiDict]]=None,
            mimetype: Optional[str]=None,
            content_type: Optional[str]=None,
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
            push_promises: A set of paths that should be pushed to the
                client if the protocol is HTTP/2.
        """
        super().__init__(headers)
        if status is not None and not isinstance(status, int):
            raise ValueError('Quart does not support non-integer status values')
        self.status_code: int = status or self.default_status

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

    @property
    def cache_control(self) -> ResponseCacheControl:
        def on_update(cache_control: ResponseCacheControl) -> None:
            self.headers['Cache-Control'] = cache_control.to_header()

        return ResponseCacheControl.from_header(self.headers.get('Cache-Control', ''), on_update)  # type: ignore  # noqa: E501

    async def _load_json_data(self) -> str:
        """Return the data after decoding."""
        return await self.get_data(raw=False)


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

    async def __aiter__(self) -> '_AsyncList':
        return _AsyncList(self)

    async def __anext__(self) -> Any:
        try:
            return next(self.iter_)
        except StopIteration as error:
            raise StopAsyncIteration() from error
