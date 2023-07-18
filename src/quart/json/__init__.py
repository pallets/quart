from __future__ import annotations

import json
from typing import Any, IO, TYPE_CHECKING

from .provider import _default
from ..globals import current_app

if TYPE_CHECKING:
    from ..wrappers import Response  # noqa: F401


def dumps(object_: Any, **kwargs: Any) -> str:
    kwargs.setdefault("default", _default)
    return json.dumps(object_, **kwargs)


def dump(object_: Any, fp: IO[str], **kwargs: Any) -> None:
    kwargs.setdefault("default", _default)
    json.dump(object_, fp, **kwargs)


def loads(object_: str | bytes, **kwargs: Any) -> Any:
    return json.loads(object_, **kwargs)


def load(fp: IO[str], **kwargs: Any) -> Any:
    return json.load(fp, **kwargs)


def jsonify(*args: Any, **kwargs: Any) -> Response:
    return current_app.json.response(*args, **kwargs)
