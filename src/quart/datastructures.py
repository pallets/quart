import io
from cgi import parse_header
from functools import wraps
from shutil import copyfileobj
from typing import Any, BinaryIO, Callable, Dict, Iterable, Optional, Type
from urllib.request import parse_http_list


class FileStorage:
    """A thin wrapper over incoming files."""

    def __init__(
        self,
        stream: BinaryIO = None,
        filename: str = None,
        name: str = None,
        content_type: str = None,
        headers: Dict = None,
    ) -> None:
        self.name = name
        self.stream = stream or io.BytesIO()
        self.filename = filename
        if headers is None:
            headers = {}
        self.headers = headers
        if content_type is not None:
            headers["Content-Type"] = content_type

    @property
    def content_type(self) -> Optional[str]:
        """The content-type sent in the header."""
        return self.headers.get("Content-Type")

    @property
    def content_length(self) -> int:
        """The content-length sent in the header."""
        return int(self.headers.get("content-length", 0))

    @property
    def mimetype(self) -> str:
        """Returns the mimetype parsed from the Content-Type header."""
        return parse_header(self.headers.get("Content-Type"))[0]

    @property
    def mimetype_params(self) -> Dict[str, str]:
        """Returns the params parsed from the Content-Type header."""
        return parse_header(self.headers.get("Content-Type"))[1]

    def save(self, destination: BinaryIO, buffer_size: int = 16384) -> None:
        """Save the file to the destination.

        Arguments:
            destination: A filename (str) or file object to write to.
            buffer_size: Buffer size as used as length in
                :func:`shutil.copyfileobj`.
        """
        close_destination = False
        if isinstance(destination, str):
            destination = open(destination, "wb")
            close_destination = True
        try:
            copyfileobj(self.stream, destination, buffer_size)
        finally:
            if close_destination:
                destination.close()

    def close(self) -> None:
        try:
            self.stream.close()
        except Exception:
            pass

    def __bool__(self) -> bool:
        return bool(self.filename)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.stream, name)

    def __iter__(self) -> Iterable[bytes]:
        return iter(self.stream)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self.filename} ({self.content_type}))>"


def _on_update(method: Callable) -> Callable:
    @wraps(method)
    def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        result = method(self, *args, **kwargs)
        if self.on_update is not None:
            self.on_update(self)
        return result

    return wrapper


class HeaderSet(set):
    def __init__(self, *args: Any, on_update: Optional[Callable] = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.on_update = on_update

    def to_header(self) -> str:
        header = ", ".join(self)
        return header.strip(",")

    @classmethod
    def from_header(
        cls: Type["HeaderSet"], header: str, on_update: Optional[Callable] = None
    ) -> "HeaderSet":
        items = {item for item in parse_http_list(header)}
        return cls(items, on_update=on_update)

    add = _on_update(set.add)
    clear = _on_update(set.clear)
    pop = _on_update(set.pop)
    remove = _on_update(set.remove)
    update = _on_update(set.update)


class RequestAccessControl:
    def __init__(self, origin: str, request_headers: HeaderSet, request_method: str) -> None:
        self.origin = origin
        self.request_headers = request_headers
        self.request_method = request_method

    @classmethod
    def from_headers(
        cls: Type["RequestAccessControl"],
        origin_header: str,
        request_headers_header: str,
        request_method_header: str,
    ) -> "RequestAccessControl":
        request_headers = HeaderSet.from_header(request_headers_header)
        return cls(origin_header, request_headers, request_method_header)


class _AccessControlDescriptor:
    def __init__(self, name: str) -> None:
        self.name = name

    def __get__(self, instance: object, owner: type = None) -> Any:
        if instance is None:
            return self
        return instance._controls[self.name]  # type: ignore

    def __set__(self, instance: object, value: Any) -> None:
        header_set = HeaderSet(value, on_update=instance.on_update)  # type: ignore
        instance._controls[self.name] = header_set  # type: ignore
        if instance.on_update is not None:  # type: ignore
            instance.on_update()  # type: ignore


class ResponseAccessControl:
    allow_headers = _AccessControlDescriptor("allow_headers")
    allow_methods = _AccessControlDescriptor("allow_methods")
    allow_origin = _AccessControlDescriptor("allow_origin")
    expose_headers = _AccessControlDescriptor("expose_headers")

    def __init__(
        self,
        allow_credentials: Optional[bool],
        allow_headers: HeaderSet,
        allow_methods: HeaderSet,
        allow_origin: HeaderSet,
        expose_headers: HeaderSet,
        max_age: Optional[float],
        on_update: Optional[Callable] = None,
    ) -> None:
        self._on_update = None
        self._controls: Dict[str, Any] = {}
        self.allow_credentials = allow_credentials
        self.allow_headers = allow_headers
        self.allow_methods = allow_methods
        self.allow_origin = allow_origin
        self.expose_headers = expose_headers
        self.max_age = max_age
        self._on_update = on_update

    @property
    def allow_credentials(self) -> bool:
        return self._controls["allow_credentials"] is True

    @allow_credentials.setter
    def allow_credentials(self, value: Optional[bool] = None) -> None:
        self._controls["allow_credentials"] = value
        self.on_update()

    @property
    def max_age(self) -> Optional[float]:
        return self._controls["max_age"]

    @max_age.setter
    def max_age(self, value: Optional[float] = None) -> None:
        try:
            value = float(value)
        except (TypeError, ValueError):
            value = None
        self._controls["max_age"] = value
        self.on_update()

    @classmethod
    def from_headers(
        cls: Type["ResponseAccessControl"],
        allow_credentials_header: str,
        allow_headers_header: str,
        allow_methods_header: str,
        allow_origin_header: str,
        expose_headers_header: str,
        max_age_header: str,
        on_update: Optional[Callable] = None,
    ) -> "ResponseAccessControl":
        allow_credentials = allow_credentials_header == "true"
        allow_headers = HeaderSet.from_header(allow_headers_header)
        allow_methods = HeaderSet.from_header(allow_methods_header)
        allow_origin = HeaderSet.from_header(allow_origin_header)
        expose_headers = HeaderSet.from_header(expose_headers_header)
        try:
            max_age = float(max_age_header)
        except (ValueError, TypeError):
            max_age = None
        return cls(
            allow_credentials,
            allow_headers,
            allow_methods,
            allow_origin,
            expose_headers,
            max_age,
            on_update,
        )

    def on_update(self, _: Any = None) -> None:
        if self._on_update is not None:
            self._on_update(self)
