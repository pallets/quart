from __future__ import annotations

from typing import Any, AnyStr, Optional, Tuple, TYPE_CHECKING, Union
from urllib.parse import unquote, urlencode

from werkzeug.datastructures import Headers

from ..json import dumps

if TYPE_CHECKING:
    from ..app import Quart  # noqa

sentinel = object()


def make_test_headers_path_and_query_string(
    app: "Quart",
    path: str,
    headers: Optional[Union[dict, Headers]] = None,
    query_string: Optional[dict] = None,
) -> Tuple[Headers, str, bytes]:
    """Make the headers and path with defaults for testing.

    Arguments:
        app: The application to test against.
        path: The path to request. If the query_string argument is not
            defined this argument will be partitioned on a '?' with
            the following part being considered the query_string.
        headers: Initial headers to send.
        query_string: To send as a dictionary, alternatively the
            query_string can be determined from the path.
    """
    if headers is None:
        headers = Headers()
    elif isinstance(headers, Headers):
        headers = headers
    elif headers is not None:
        headers = Headers(headers)
    headers.setdefault("Remote-Addr", "127.0.0.1")
    headers.setdefault("User-Agent", "Quart")
    headers.setdefault("host", app.config["SERVER_NAME"] or "localhost")
    if "?" in path and query_string is not None:
        raise ValueError("Query string is defined in the path and as an argument")
    if query_string is None:
        path, _, query_string_raw = path.partition("?")
    else:
        query_string_raw = urlencode(query_string, doseq=True)
    query_string_bytes = query_string_raw.encode("ascii")
    return headers, unquote(path), query_string_bytes


def make_test_body_with_headers(
    data: Optional[AnyStr] = None,
    form: Optional[dict] = None,
    json: Any = sentinel,
    app: Optional["Quart"] = None,
) -> Tuple[bytes, Headers]:
    """Make the body bytes with associated headers.

    Arguments:
        data: Raw data to send in the request body.
        form: Data to send form encoded in the request body.
        json: Data to send json encoded in the request body.
    """
    if [json is not sentinel, form is not None, data is not None].count(True) > 1:
        raise ValueError("Quart test args 'json', 'form', and 'data' are mutually exclusive")

    request_data = b""

    headers = Headers()

    if isinstance(data, str):
        request_data = data.encode("utf-8")
    elif isinstance(data, bytes):
        request_data = data

    if json is not sentinel:
        request_data = dumps(json, app=app).encode("utf-8")
        headers["Content-Type"] = "application/json"

    if form is not None:
        request_data = urlencode(form).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"

    return request_data, headers


async def no_op_push(path: str, headers: Headers) -> None:
    """A push promise sender that does nothing.

    This is best used when creating Request instances for testing
    outside of the QuartClient. The Request instance must know what to
    do with push promises, and this gives it the option of doing
    nothing.
    """
    pass
