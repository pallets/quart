from __future__ import annotations

import os
from typing import Any, AnyStr, AsyncGenerator, Dict, Generator, Tuple, TYPE_CHECKING, Union

if TYPE_CHECKING:
    from werkzeug.datastructures import Headers  # noqa: F401
    from .wrappers.response import Response  # noqa: F401

FilePath = Union[bytes, str, os.PathLike]

# The possible types that are directly convertible or are a Response object.
ResponseValue = Union[
    "Response", AnyStr, Dict[str, Any], AsyncGenerator[bytes, None], Generator[bytes, None, None]
]
StatusCode = int
HeaderValue = Union["Headers", dict, list]

# The possible types returned by a route function.
ResponseReturnValue = Union[
    ResponseValue,
    Tuple[ResponseValue, HeaderValue],
    Tuple[ResponseValue, StatusCode],
    Tuple[ResponseValue, StatusCode, HeaderValue],
]
