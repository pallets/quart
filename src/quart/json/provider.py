from __future__ import annotations

import json
import weakref
from dataclasses import asdict, is_dataclass
from datetime import date
from decimal import Decimal
from typing import Any, AnyStr, Callable, Dict, IO, Tuple, TYPE_CHECKING
from uuid import UUID

from werkzeug.http import http_date

if TYPE_CHECKING:
    from ..app import Quart
    from ..wrappers import Response


class JSONProvider:
    """A standard set of JSON operations for an application. Subclasses
    of this can be used to customize JSON behavior or use different
    JSON libraries.

    To implement a provider for a specific library, subclass this base
    class and implement at least :meth:`dumps` and :meth:`loads`. All
    other methods have default implementations.

    To use a different provider, either subclass ``Quart`` and set
    :attr:`~quart.Quart.json_provider_class` to a provider class, or set
    :attr:`app.json <quart.Quart.json>` to an instance of the class.
    :param app: An application instance. This will be stored as a
        :class:`weakref.proxy` on the :attr:`_app` attribute.
    """

    def __init__(self, app: Quart) -> None:
        self._app = weakref.proxy(app)

    def dumps(self, object_: Any, **kwargs: Any) -> str:
        """Serialize data as JSON.

        Arguments:
            object_: The data to serialize.
            kwargs: May be passed to the underlying JSON library.
        """
        raise NotImplementedError

    def dump(self, object_: Any, fp: IO[str], **kwargs: Any) -> None:
        """Serialize data as JSON and write to a file.

        Arguments:
            object_: The data to serialize.
            fp: A file opened for writing text. Should use the UTF-8
                encoding to be valid JSON.
            kwargs: May be passed to the underlying JSON library.
        """
        fp.write(self.dumps(object_, **kwargs))

    def loads(self, object_: str | bytes, **kwargs: Any) -> Any:
        """Deserialize data as JSON.

        Arguments:
            s: Text or UTF-8 bytes.
            kwargs: May be passed to the underlying JSON library.
        """
        raise NotImplementedError

    def load(self, fp: IO[AnyStr], **kwargs: Any) -> Any:
        """Deserialize data as JSON read from a file.
        :param fp: A file opened for reading text or UTF-8 bytes.
        :param kwargs: May be passed to the underlying JSON library.
        """
        return self.loads(fp.read(), **kwargs)

    def _prepare_response_obj(self, args: Tuple[Any, ...], kwargs: Dict[str, Any]) -> Any:
        if args and kwargs:
            raise TypeError("app.json.response() takes either args or kwargs, not both")

        if not args and not kwargs:
            return None

        if len(args) == 1:
            return args[0]

        return args or kwargs

    def response(self, *args: Any, **kwargs: Any) -> Response:
        """Serialize the given arguments as JSON, and return a
        :class:`~quart.Response` object with the ``application/json``
        mimetype.

        The :func:`~quart.json.jsonify` function calls this method for
        the current application.
        Either positional or keyword arguments can be given, not both.
        If no arguments are given, ``None`` is serialized.

        Arguments:
            args: A single value to serialize, or multiple values to
                treat as a list to serialize.
            kwargs: Treat as a dict to serialize.
        """
        object_ = self._prepare_response_obj(args, kwargs)
        return self._app.response_class(self.dumps(object_), mimetype="application/json")


def _default(object_: Any) -> Any:
    if isinstance(object_, date):
        return http_date(object_)
    if isinstance(object_, (Decimal, UUID)):
        return str(object_)
    if is_dataclass(object_):
        return asdict(object_)
    if hasattr(object_, "__html__"):
        return str(object_.__html__())

    raise TypeError(f"Object of type {type(object_).__name__} is not JSON serializable")


class DefaultJSONProvider(JSONProvider):
    """Provide JSON operations using Python's built-in :mod:`json`
    library. Serializes the following additional data types:
    -   :class:`datetime.datetime` and :class:`datetime.date` are
        serialized to :rfc:`822` strings. This is the same as the HTTP
        date format.
    -   :class:`uuid.UUID` is serialized to a string.
    -   :class:`dataclasses.dataclass` is passed to
        :func:`dataclasses.asdict`.
    -   :class:`~markupsafe.Markup` (or any object with a ``__html__``
        method) will call the ``__html__`` method to get a string.
    """

    default: Callable[[Any], Any] = staticmethod(_default)
    """Apply this function to any object that :meth:`json.dumps` does
    not know how to serialize. It should return a valid JSON type or
    raise a ``TypeError``.
    """

    ensure_ascii = True
    """Replace non-ASCII characters with escape sequences. This may be
    more compatible with some clients, but can be disabled for better
    performance and size.
    """

    sort_keys = True
    """Sort the keys in any serialized dicts. This may be useful for
    some caching situations, but can be disabled for better performance.
    When enabled, keys must all be strings, they are not converted
    before sorting.
    """

    compact: bool | None = None
    """If ``True``, or ``None`` out of debug mode, the :meth:`response`
    output will not add indentation, newlines, or spaces. If ``False``,
    or ``None`` in debug mode, it will use a non-compact representation.
    """

    mimetype = "application/json"
    """The mimetype set in :meth:`response`."""

    def dumps(self, object_: Any, **kwargs: Any) -> str:
        """Serialize data as JSON to a string.
        Keyword arguments are passed to :func:`json.dumps`. Sets some
        parameter defaults from the :attr:`default`,
        :attr:`ensure_ascii`, and :attr:`sort_keys` attributes.

        Arguments:
            object_: The data to serialize.
            kwargs: Passed to :func:`json.dumps`.
        """
        kwargs.setdefault("default", self.default)
        kwargs.setdefault("ensure_ascii", self.ensure_ascii)
        kwargs.setdefault("sort_keys", self.sort_keys)
        return json.dumps(object_, **kwargs)

    def loads(self, object_: str | bytes, **kwargs: Any) -> Any:
        """Deserialize data as JSON from a string or bytes.

        Arguments:
            object_: Text or UTF-8 bytes.
            kwargs: Passed to :func:`json.loads`.
        """
        return json.loads(object_, **kwargs)

    def response(self, *args: Any, **kwargs: Any) -> Response:
        """Serialize the given arguments as JSON, and return a
        :class:`~quart.Response` object with it. The response mimetype
        will be "application/json" and can be changed with
        :attr:`mimetype`.
        If :attr:`compact` is ``False`` or debug mode is enabled, the
        output will be formatted to be easier to read.
        Either positional or keyword arguments can be given, not both.
        If no arguments are given, ``None`` is serialized.

        Arguments:
            args: A single value to serialize, or multiple values to
                treat as a list to serialize.
            kwargs: Treat as a dict to serialize.
        """
        object_ = self._prepare_response_obj(args, kwargs)
        dump_args: Dict[str, Any] = {}

        if (self.compact is None and self._app.debug) or self.compact is False:
            dump_args.setdefault("indent", 2)
        else:
            dump_args.setdefault("separators", (",", ":"))

        return self._app.response_class(self.dumps(object_, **dump_args), mimetype=self.mimetype)
