from __future__ import annotations

import json
from typing import Any, IO, TYPE_CHECKING

from flask.json.provider import _default

from ..globals import current_app

if TYPE_CHECKING:
    from ..wrappers import Response  # noqa: F401


def dumps(object_: Any, **kwargs: Any) -> str:
    if current_app:
        return current_app.json.dumps(object_, **kwargs)
    else:
        kwargs.setdefault("default", _default)
        return json.dumps(object_, **kwargs)


def dump(object_: Any, fp: IO[str], **kwargs: Any) -> None:
    if current_app:
        current_app.json.dump(object_, fp, **kwargs)
    else:
        kwargs.setdefault("default", _default)
        json.dump(object_, fp, **kwargs)


def loads(object_: str | bytes, **kwargs: Any) -> Any:
    if current_app:
        return current_app.json.loads(object_, **kwargs)
    else:
        return json.loads(object_, **kwargs)


def load(fp: IO[str], **kwargs: Any) -> Any:
    if current_app:
        return current_app.json.load(fp, **kwargs)
    else:
        return json.load(fp, **kwargs)


def jsonify(*args: Any, **kwargs: Any) -> Response:
    return current_app.json.response(*args, **kwargs)  # type: ignore
