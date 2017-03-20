from typing import Tuple, Union

from .wrappers import Response


# The possible types that are directly convertable or are a Response
# object.
ResponseValue = Union[Response, str]

# The possible types returned by a route function.
ResponseReturnValue = Union[
    ResponseValue,
    Tuple[ResponseValue, dict],
    Tuple[ResponseValue, int],
    Tuple[ResponseValue, int, dict],
]
