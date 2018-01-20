import asyncio
import io
from base64 import b64decode
from cgi import FieldStorage, parse_header
from datetime import datetime, timedelta
from http.cookies import SimpleCookie
from inspect import isasyncgen  # type: ignore
from typing import (
    Any, AnyStr, AsyncGenerator, Callable, Dict, Generator, Iterable, Optional, Set, TYPE_CHECKING,
    Union,
)
from urllib.parse import parse_qs, unquote, urlparse
from urllib.request import parse_http_list, parse_keqv_list

from .datastructures import (
    Accept, Authorization, CharsetAccept, CIMultiDict, FileStorage, LanguageAccept, MIMEAccept,
    MultiDict,
)
from .json import loads
from .utils import create_cookie

if TYPE_CHECKING:
    from .routing import Rule  # noqa

sentinel = object()


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
        self._body: asyncio.Future = asyncio.Future()
        self._stream: asyncio.Queue = asyncio.Queue()
        self._size = 0
        self._max_content_length = max_content_length

    def __aiter__(self) -> 'Body':
        return self

    async def __anext__(self) -> bytes:
        # The iterator should return whenever there is any data, but
        # quit if the body future is done i.e. there is no more data.
        done, _ = await asyncio.wait(  # type: ignore
            [self._body, self._stream.get()], return_when=asyncio.FIRST_COMPLETED,  # type: ignore
        )
        if self._body.done():
            raise StopAsyncIteration()
        else:
            result = bytearray()
            for future in done:
                data = future.result()
                result.extend(data)
                self._size -= len(data)
            return result

    def __await__(self) -> Generator[Any, None, Any]:
        return self._body.__await__()

    def append(self, data: bytes) -> None:
        self._stream.put_nowait(data)
        self._size += len(data)
        if self._max_content_length is not None and self._size > self._max_content_length:
            from .exceptions import RequestEntityTooLarge  # noqa Avoiding circular import
            raise RequestEntityTooLarge()

    def set_complete(self) -> None:
        buffer_ = bytearray()
        try:
            while True:
                buffer_.extend(self._stream.get_nowait())
        except asyncio.QueueEmpty:
            self._body.set_result(buffer_)

    def set_result(self, data: bytes) -> None:
        """Convienience method, mainly for testing."""
        self._body.set_result(data)


class JSONMixin:
    """Mixin to provide get_json methods from objects.

    The class must support _load_data_json and have a mimetype
    attribute.
    """
    _cached_json = sentinel

    @property
    def mimetype(self) -> str:
        """Return the mimetype of the associated data."""
        raise NotImplemented()

    async def _load_json_data(self) -> str:
        """Return the data after decoding."""
        raise NotImplemented()

    @property
    def is_json(self) -> bool:
        """Returns True if the content_type is json like."""
        content_type = self.mimetype
        if content_type == 'application/json' or (
                content_type.startswith('application/') and content_type.endswith('+json')
        ):
            return True
        else:
            return False

    @property
    async def json(self) -> Any:
        return await self.get_json()

    async def get_json(
        self, force: bool=False, silent: bool=False, cache: bool=True,
    ) -> Any:
        """Parses the body data as JSON and returns it.

        Arguments:
            force: Force JSON parsing even if the mimetype is not JSON.
            silent: Do not trigger error handling if parsing fails, without
                this the :meth:`on_json_loading_failed` will be called on
                error.
            cache: Cache the parsed JSON on this request object.
        """
        if cache and self._cached_json is not sentinel:
            return self._cached_json

        if not (force or self.is_json):
            return None

        data = await self._load_json_data()
        try:
            result = loads(data)
        except ValueError as error:
            if silent:
                result = None
            else:
                self.on_json_loading_failed(error)
        if cache:
            self._cached_json = result
        return result

    def on_json_loading_failed(self, error: Exception) -> None:
        """Handle a JSON parsing error.

        Arguments:
            error: The exception raised during parsing.
        """
        from .exceptions import BadRequest  # noqa Avoiding circular import
        raise BadRequest()


class _BaseRequestResponse:
    """This is the base class for Request or Response.

    It implements a number of properties for header handling.

    Attributes:
        charset: The default charset for encoding/decoding.
    """
    charset = 'utf-8'

    def __init__(self, headers: Optional[Union[dict, CIMultiDict]]) -> None:
        self.headers: CIMultiDict
        if headers is None:
            self.headers = CIMultiDict()
        elif isinstance(headers, CIMultiDict):
            self.headers = headers
        elif headers is not None:
            self.headers = CIMultiDict(headers)

    @property
    def mimetype(self) -> Optional[str]:
        """Returns the mimetype parsed from the Content-Type header."""
        if 'Content-Type' in self.headers:
            return parse_header(self.headers.get('Content-Type'))[0]
        else:
            return None

    @mimetype.setter
    def mimetype(self, value: str) -> None:
        """Set the mimetype to the value."""
        if (
                value.startswith('text/') or value == 'application/xml' or
                (value.startswith('application/') and value.endswith('+xml'))
        ):
            mimetype = f"{value}; charset={self.charset}"
        else:
            mimetype = value
        self.headers['Content-Type'] = mimetype

    @property
    def mimetype_params(self) -> Dict[str, str]:
        """Returns the params parsed from the Content-Type header."""
        return parse_header(self.headers.get('Content-Type'))[1]

    async def get_data(self, raw: bool=True) -> AnyStr:
        raise NotImplemented()


class BaseRequestWebsocket(_BaseRequestResponse):
    """This class is the basis for Requests and websockets..

    Attributes:
        routing_exception: If an exception is raised during the route
            matching it will be stored here.
        url_rule: The rule that this request has been matched too.
        view_args: The keyword arguments for the view from the route
            matching.
    """
    routing_exception: Optional[Exception] = None
    url_rule: Optional['Rule'] = None
    view_args: Optional[Dict[str, Any]] = None

    def __init__(self, method: str, path: str, headers: CIMultiDict) -> None:
        """Create a request or websocket base object.

        Arguments:
            method: The HTTP verb.
            path: The full URL of the request.
            headers: The request headers.
            body: An awaitable future for the body data i.e.
                ``data = await body``

        Attributes:
            args: The query string arguments.
            scheme: The URL scheme, http or https.
        """
        super().__init__(headers)
        self.full_path = path
        parsed_url = urlparse(path)
        self.args = MultiDict()
        for key, values in parse_qs(parsed_url.query).items():
            for value in values:
                self.args[key] = value
        self.path = unquote(parsed_url.path)
        self.scheme = parsed_url.scheme
        self.server_name = parsed_url.netloc
        self.method = method

    @property
    def endpoint(self) -> Optional[str]:
        """Returns the corresponding endpoint matched for this request.

        This can be None if the request has not been matched with a
        rule.
        """
        if self.url_rule is not None:
            return self.url_rule.endpoint
        else:
            return None

    @property
    def blueprint(self) -> Optional[str]:
        """Returns the blueprint the matched endpoint belongs to.

        This can be None if the request has not been matched or the
        endpoint is not in a blueprint.
        """
        if self.endpoint is not None and '.' in self.endpoint:
            return self.endpoint.rsplit('.', 1)[0]
        else:
            return None

    @property
    def accept_charsets(self) -> CharsetAccept:
        return CharsetAccept(self.headers.get('Accept-Charset', ''))

    @property
    def accept_encodings(self) -> Accept:
        return Accept(self.headers.get('Accept-Encoding', ''))

    @property
    def accept_languages(self) -> LanguageAccept:
        return LanguageAccept(self.headers.get('Accept-Language', ''))

    @property
    def accept_mimetypes(self) -> MIMEAccept:
        return MIMEAccept(self.headers.get('Accept', ''))

    @property
    def authorization(self) -> Optional[Authorization]:
        header = self.headers.get('Authorization', '')
        try:
            type_, value = header.split(None, 1)
            type_ = type_.lower()
        except ValueError:
            return None
        else:
            if type_ == 'basic':
                try:
                    username, password = b64decode(value.encode()).decode().split(':', 1)
                except ValueError:
                    return None
                else:
                    return Authorization(username=username, password=password)
            elif type_ == 'digest':
                items = parse_http_list(value)
                params = parse_keqv_list(items)
                for key in 'username', 'realm', 'nonce', 'uri', 'response':
                    if key not in params:
                        return None
                if ('cnonce' in params or 'nc' in params) and 'qop' not in params:
                    return None
                return Authorization(**params)
        return None

    @property
    def remote_addr(self) -> str:
        """Returns the remote address of the request, faked into the headers."""
        return self.headers['Remote-Addr']

    @property
    def cookies(self) -> Dict[str, str]:
        """The parsed cookies attached to this request."""
        cookies = SimpleCookie()  # type: ignore
        cookies.load(self.headers.get('Cookie', ''))
        return {key: cookie.value for key, cookie in cookies.items()}


class Request(BaseRequestWebsocket, JSONMixin):
    """This class represents a request.

    It can be subclassed and the subclassed used in preference by
    replacing the :attr:`~quart.Quart.request_class` with your
    subclass.
    """

    def __init__(
            self,
            method: str,
            path: str,
            headers: CIMultiDict,
            *,
            max_content_length: Optional[int]=None,
    ) -> None:
        """Create a request object.

        Arguments:
            method: The HTTP verb.
            path: The full URL of the request.
            headers: The request headers.
            body: An awaitable future for the body data i.e.
                ``data = await body``
            max_content_length: The maximum length in bytes of the
                body (None implies no limit in Quart).
        """
        super().__init__(method, path, headers)
        content_length = headers.get('Content-Length')
        self.max_content_length = max_content_length
        if (
                content_length is not None and self.max_content_length is not None and
                int(content_length) > self.max_content_length
        ):
            from .exceptions import RequestEntityTooLarge  # noqa Avoiding circular import
            raise RequestEntityTooLarge()
        self.body = Body(self.max_content_length)
        self._cached_json: Any = sentinel
        self._form: Optional[MultiDict] = None
        self._files: Optional[MultiDict] = None

    async def get_data(self, raw: bool=True) -> AnyStr:
        """The request body data."""
        if raw:
            return await self.body  # type: ignore
        else:
            return (await self.body).decode(self.charset)  # type: ignore

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
        content_header = self.headers.get('Content-Type')
        if content_header is None:
            return
        content_type, parameters = parse_header(content_header)
        if content_type == 'application/x-www-form-urlencoded':
            for key, values in parse_qs(data.decode()).items():
                for value in values:
                    self._form[key] = value
        elif content_type == 'multipart/form-data':
            field_storage = FieldStorage(
                io.BytesIO(data), headers=self.headers, environ={'REQUEST_METHOD': 'POST'},
            )
            for key in field_storage:  # type: ignore
                field_storage_key = field_storage[key]
                if field_storage_key.filename is None:
                    self._form[key] = field_storage_key.value
                else:
                    self._files[key] = FileStorage(
                        io.BytesIO(field_storage_key.file.read()), field_storage_key.filename,
                        field_storage_key.name, field_storage_key.type, field_storage_key.headers,
                    )

    async def _load_json_data(self) -> str:
        """Return the data after decoding."""
        return await self.get_data(raw=False)


class Websocket(BaseRequestWebsocket):

    def __init__(
            self,
            path: str,
            headers: CIMultiDict,
            queue: asyncio.Queue,
            send: Callable,
    ) -> None:
        """Create a request object.

        Arguments:
            method: The HTTP verb.
            path: The full URL of the request.
            headers: The request headers.
            websocket: The actual websocket with the data.
        """
        super().__init__('GET', path, headers)
        self._queue = queue
        self._send = send

    async def receive(self) -> bytes:
        return await self._queue.get()

    async def send(self, data: bytes) -> None:
        self._send(data)


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
    """

    automatically_set_content_length = True
    default_status = 200
    default_mimetype = 'text/html'

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

        self.response: AsyncGenerator[bytes, None]
        if isinstance(response, (str, bytes)):
            self.set_data(response)  # type: ignore
        else:
            self.response = _ensure_aiter(response)  # type: ignore
        self.push_promises: Set[str] = set()

    async def get_data(self, raw: bool=True) -> AnyStr:
        """Return the body data."""
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
        """Set a cookie in the response headers.

        The arguments are the standard cookie morsels and this is a
        wrapper around the stdlib SimpleCookie code.
        """
        cookie = create_cookie(key, value, max_age, expires, path, domain, secure, httponly)
        self.headers.add('Set-Cookie', cookie.output(header=''))

    def delete_cookie(self, key: str, path: str='/', domain: Optional[str]=None) -> None:
        """Delete a cookie (set to expire immediately)."""
        self.set_cookie(key, expires=datetime.utcnow(), max_age=0, path=path, domain=domain)

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
