from __future__ import annotations

import os
from typing import Any, AnyStr, AsyncGenerator, Dict, Generator, List, Tuple, TYPE_CHECKING, Union

if TYPE_CHECKING:
    from werkzeug.datastructures import Headers  # noqa: F401

    from .wrappers.response import Response  # noqa: F401

FilePath = Union[bytes, str, os.PathLike]

# The possible types that are directly convertible or are a Response object.
ResponseValue = Union[
    "Response",
    AnyStr,
    Dict[str, Any],  # any jsonify-able dict
    AsyncGenerator[bytes, None],
    Generator[bytes, None, None],
]
StatusCode = int

# the possible types for an individual HTTP header
HeaderName = str
HeaderValue = Union[str, List[str], Tuple[str, ...]]

# the possible types for HTTP headers
HeadersValue = Union["Headers", Dict[HeaderName, HeaderValue], List[Tuple[HeaderName, HeaderValue]]]

# The possible types returned by a route function.
ResponseReturnValue = Union[
    ResponseValue,
    Tuple[ResponseValue, HeadersValue],
    Tuple[ResponseValue, StatusCode],
    Tuple[ResponseValue, StatusCode, HeadersValue],
]
