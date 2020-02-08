from datetime import datetime
from email.utils import parsedate_to_datetime
from http.cookies import SimpleCookie
from typing import Any, AnyStr, Dict, List, Optional, TYPE_CHECKING, Union
from urllib.parse import ParseResult, urlunparse

from werkzeug.datastructures import (
    Accept,
    Authorization,
    CallbackDict,
    CharsetAccept,
    ETags,
    Headers,
    HeaderSet,
    IfRange,
    ImmutableList,
    ImmutableMultiDict,
    LanguageAccept,
    MIMEAccept,
    Range,
    RequestCacheControl,
)
from werkzeug.http import (
    dump_options_header,
    parse_accept_header,
    parse_authorization_header,
    parse_cache_control_header,
    parse_etags,
    parse_if_range_header,
    parse_list_header,
    parse_options_header,
    parse_range_header,
    parse_set_header,
)
from werkzeug.urls import url_decode
from werkzeug.utils import get_content_type

from ..json import loads

if TYPE_CHECKING:
    from ..routing import QuartRule  # noqa

sentinel = object()


class JSONMixin:
    """Mixin to provide get_json methods from objects.

    The class must support _load_data_json and have a mimetype
    attribute.
    """

    _cached_json = sentinel

    @property
    def mimetype(self) -> str:
        """Return the mimetype of the associated data."""
        raise NotImplementedError()

    async def _load_json_data(self) -> str:
        """Return the data after decoding."""
        raise NotImplementedError()

    @property
    def is_json(self) -> bool:
        """Returns True if the content_type is json like."""
        content_type = self.mimetype
        if content_type == "application/json" or (
            content_type.startswith("application/") and content_type.endswith("+json")
        ):
            return True
        else:
            return False

    @property
    async def json(self) -> Any:
        return await self.get_json()

    async def get_json(self, force: bool = False, silent: bool = False, cache: bool = True) -> Any:
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
        from ..exceptions import BadRequest  # noqa Avoiding circular import

        raise BadRequest()


class _BaseRequestResponse:
    """This is the base class for Request or Response.

    It implements a number of properties for header handling.

    Attributes:
        charset: The default charset for encoding/decoding.
    """

    charset = url_charset = "utf-8"

    def __init__(self, headers: Optional[Union[dict, Headers]]) -> None:
        self.headers: Headers
        if headers is None:
            self.headers = Headers()
        else:
            self.headers = Headers(headers)

    @property
    def mimetype(self) -> str:
        """Returns the mimetype parsed from the Content-Type header."""
        return parse_options_header(self.headers.get("Content-Type"))[0]

    @mimetype.setter
    def mimetype(self, value: str) -> None:
        """Set the mimetype to the value."""
        self.headers["Content-Type"] = get_content_type(value, self.charset)

    @property
    def mimetype_params(self) -> Dict[str, str]:
        """Returns the params parsed from the Content-Type header."""

        def _on_update(value: Dict[str, Any]) -> None:
            self.headers["Content-Type"] = dump_options_header(self.mimetype, value)

        value = parse_options_header(self.headers.get("Content-Type"))[1]
        return CallbackDict(value, _on_update)

    async def get_data(self, raw: bool = True) -> AnyStr:
        raise NotImplementedError()


class BaseRequestWebsocket(_BaseRequestResponse):
    """This class is the basis for Requests and websockets..

    Attributes:
        routing_exception: If an exception is raised during the route
            matching it will be stored here.
        url_rule: The rule that this request has been matched too.
        view_args: The keyword arguments for the view from the route
            matching.
    """

    encoding_errors = "replace"

    # Storage class for dict data, e.g.
    dict_storage_class = ImmutableMultiDict

    # Storage class for list data, e.g. access route
    list_storage_class = ImmutableList

    # Storage class for parameter data, e.g. args
    parameter_storage_class = ImmutableMultiDict

    routing_exception: Optional[Exception] = None
    url_rule: Optional["QuartRule"] = None
    view_args: Optional[Dict[str, Any]] = None

    def __init__(
        self,
        method: str,
        scheme: str,
        path: str,
        query_string: bytes,
        headers: Headers,
        root_path: str,
        http_version: str,
    ) -> None:
        """Create a request or websocket base object.

        Arguments:
            method: The HTTP verb.
            scheme: The scheme used for the request.
            path: The full unquoted path of the request.
            query_string: The raw bytes for the query string part.
            headers: The request headers.
            root_path: The root path that should be prepended to all
                routes.
            http_version: The HTTP version of the request.

        Attributes:
            args: The query string arguments.
            scheme: The URL scheme, http or https.
        """
        super().__init__(headers)
        self.args = url_decode(
            query_string,
            self.url_charset,
            errors=self.encoding_errors,
            cls=self.parameter_storage_class,
        )
        self.path = path
        self.query_string = query_string
        self.scheme = scheme
        self.method = method
        self.root_path = root_path
        self.http_version = http_version

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
        if self.endpoint is not None and "." in self.endpoint:
            return self.endpoint.rsplit(".", 1)[0]
        else:
            return None

    @property
    def accept_charsets(self) -> CharsetAccept:
        return parse_accept_header(self.headers.get("Accept-Charset"), CharsetAccept)

    @property
    def accept_encodings(self) -> Accept:
        return parse_accept_header(self.headers.get("Accept-Encoding"), Accept)

    @property
    def accept_languages(self) -> LanguageAccept:
        return parse_accept_header(self.headers.get("Accept-Language"), LanguageAccept)

    @property
    def accept_mimetypes(self) -> MIMEAccept:
        return parse_accept_header(self.headers.get("Accept"), MIMEAccept)

    @property
    def authorization(self) -> Optional[Authorization]:
        return parse_authorization_header(self.headers.get("Authorization"))

    @property
    def cache_control(self) -> RequestCacheControl:
        return parse_cache_control_header(
            self.headers.get("Cache-Control"), None, RequestCacheControl
        )

    @property
    def remote_addr(self) -> str:
        """Returns the remote address of the request, faked into the headers."""
        return self.headers["Remote-Addr"]

    @property
    def base_url(self) -> str:
        """Returns the base url without query string or fragments."""
        return urlunparse(ParseResult(self.scheme, self.host, self.path, "", "", ""))

    @property
    def full_path(self) -> str:
        if self.query_string:
            return f"{self.path}?{self.query_string.decode('ascii')}"
        else:
            return self.path

    @property
    def host(self) -> str:
        return self.headers.get("host") or self.headers.get(":authority")

    @property
    def host_url(self) -> str:
        return urlunparse(ParseResult(self.scheme, self.host, "", "", "", ""))

    @property
    def url(self) -> str:
        """Returns the full url requested."""
        return urlunparse(
            ParseResult(
                self.scheme, self.host, self.path, "", self.query_string.decode("ascii"), ""
            )
        )

    @property
    def url_root(self) -> str:
        return urlunparse(
            ParseResult(self.scheme, self.host, self.path.rsplit("/", 1)[0] + "/", "", "", "")
        )

    @property
    def is_secure(self) -> bool:
        return self.scheme in {"https", "wss"}

    @property
    def cookies(self) -> Dict[str, str]:
        """The parsed cookies attached to this request."""
        cookies: SimpleCookie = SimpleCookie()
        for cookie in self.headers.getlist("Cookie"):
            cookies.load(cookie)
        return self.dict_storage_class((key, cookie.value) for key, cookie in cookies.items())

    @property
    def access_route(self) -> List[str]:
        if "X-Forwarded-For" in self.headers:
            return self.list_storage_class(parse_list_header(self.headers["X-Forwarded-For"]))
        else:
            return self.list_storage_class([self.remote_addr])

    @property
    def date(self) -> Optional[datetime]:
        if "date" in self.headers:
            return parsedate_to_datetime(self.headers["date"])
        else:
            return None

    @property
    def if_match(self) -> ETags:
        return parse_etags(self.headers.get("If-Match"))

    @property
    def if_modified_since(self) -> Optional[datetime]:
        if "If-Modified-Since" in self.headers:
            return parsedate_to_datetime(self.headers["If-Modified-Since"])
        else:
            return None

    @property
    def if_none_match(self) -> ETags:
        return parse_etags(self.headers.get("If-None-Match"))

    @property
    def if_range(self) -> IfRange:
        return parse_if_range_header(self.headers.get("If-Range"))

    @property
    def max_forwards(self) -> Optional[str]:
        return self.headers.get("Max-Forwards")

    @property
    def pragma(self) -> HeaderSet:
        return parse_set_header(self.headers.get("Pragma"))

    @property
    def range(self) -> Optional[Range]:
        return parse_range_header(self.headers.get("Range"))

    @property
    def referrer(self) -> Optional[str]:
        return self.headers.get("Referer")

    @property
    def if_unmodified_since(self) -> Optional[datetime]:
        if "If-Unmodified-Since" in self.headers:
            return parsedate_to_datetime(self.headers["If-Unmodified-Since"])
        else:
            return None

    @property
    def origin(self) -> Optional[str]:
        return self.headers.get("Origin")

    @property
    def access_control_request_headers(self) -> Optional[HeaderSet]:
        if "Access-Control-Request-Headers" in self.headers:
            return parse_set_header(self.headers["Access-Control-Request-Headers"])
        return None

    @property
    def access_control_request_method(self) -> Optional[str]:
        return self.headers.get("Access-Control-Request-Method")
