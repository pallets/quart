import os
from typing import AsyncGenerator, Generator, Tuple, TYPE_CHECKING, Union

if TYPE_CHECKING:
    from .wrappers.response import Response  # noqa: F401

FilePath = Union[bytes, str, os.PathLike]

# The possible types that are directly convertable or are a Response
# object.
ResponseValue = Union["Response", str, AsyncGenerator[bytes, None], Generator[bytes, None, None]]

# The possible types returned by a route function.
ResponseReturnValue = Union[
    ResponseValue,
    Tuple[ResponseValue, dict],
    Tuple[ResponseValue, int],
    Tuple[ResponseValue, int, dict],
]
